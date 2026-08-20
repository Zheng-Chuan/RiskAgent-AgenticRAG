from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient


@dataclass(frozen=True)
class MilvusStoreConfig:
    collection_name: str
    metric_type: str
    index_type: str
    nlist: int
    nprobe: int


def _default_lite_uri(*, persist_dir: Path) -> str:
    persist_dir.mkdir(parents=True, exist_ok=True)
    return str((persist_dir / "milvus.db").absolute())


def build_milvus_client(*, persist_dir: Path) -> MilvusClient:
    uri = os.getenv("MILVUS_URI")
    if uri:
        return MilvusClient(uri=uri)
    host = os.getenv("MILVUS_HOST")
    port = os.getenv("MILVUS_PORT")
    if host and port:
        return MilvusClient(uri=f"http://{host}:{int(port)}")
    return MilvusClient(uri=_default_lite_uri(persist_dir=persist_dir))


def ensure_collection(*, client: MilvusClient, config: MilvusStoreConfig, dim: int) -> None:
    name = str(config.collection_name)
    if client.has_collection(name):
        return

    fields = [
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=256),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=int(dim)),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="file_type", dtype=DataType.VARCHAR, max_length=16),
        FieldSchema(name="parent_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="section_path", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="context_brief", dtype=DataType.VARCHAR, max_length=2048),
        FieldSchema(name="start_index", dtype=DataType.INT64),
        FieldSchema(name="page", dtype=DataType.INT64),
        FieldSchema(name="start_line", dtype=DataType.INT64),
        FieldSchema(name="end_line", dtype=DataType.INT64),
    ]
    schema = CollectionSchema(fields=fields, description="RiskAgent chunks")
    client.create_collection(collection_name=name, schema=schema)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type=str(config.index_type),
        metric_type=str(config.metric_type),
        params={"nlist": int(config.nlist)},
    )
    client.create_index(collection_name=name, index_params=index_params)


def delete_by_source(*, client: MilvusClient, config: MilvusStoreConfig, source: str) -> None:
    src = str(source or "").replace("\\", "\\\\").replace('"', '\\"')
    expr = f'source == "{src}"'
    try:
        client.load_collection(collection_name=str(config.collection_name))
    except Exception:
        pass
    try:
        client.delete(collection_name=str(config.collection_name), filter=expr)
    except TypeError:
        client.delete(collection_name=str(config.collection_name), expr=expr)
    except Exception as e:
        msg = str(e).lower()
        if "collection not loaded" not in msg:
            raise
        try:
            client.load_collection(collection_name=str(config.collection_name))
        except Exception:
            pass
        try:
            client.delete(collection_name=str(config.collection_name), filter=expr)
        except TypeError:
            client.delete(collection_name=str(config.collection_name), expr=expr)


def insert_chunks(*, client: MilvusClient, config: MilvusStoreConfig, rows: list[dict[str, Any]]) -> None:
    """分批插入向量数据, 避免 gRPC 消息超限 (默认 64MB).

    2560 维向量约 10KB + text 字段约 60KB => 每条 row 约 70KB.
    取 200 条/批 => 约 14MB, 远低于 64MB 限制.
    """
    if not rows:
        return
    batch_size = 200
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        client.insert(collection_name=str(config.collection_name), data=batch)


def drop_collection(*, client: MilvusClient, config: MilvusStoreConfig) -> bool:
    """删除Milvus集合（清空所有数据）。

    Args:
        client: Milvus客户端
        config: Milvus存储配置

    Returns:
        是否成功删除
    """
    name = str(config.collection_name)
    if not client.has_collection(name):
        return True

    try:
        client.drop_collection(collection_name=name)
        return True
    except Exception:
        return False


def search(*, client: MilvusClient, config: MilvusStoreConfig, vector: list[float], limit: int) -> list[dict[str, Any]]:
    out = client.search(
        collection_name=str(config.collection_name),
        data=[vector],
        limit=int(limit),
        output_fields=[
            "chunk_id",
            "text",
            "source",
            "file_type",
            "parent_id",
            "section_path",
            "context_brief",
            "start_index",
            "page",
            "start_line",
            "end_line",
        ],
        search_params={"params": {"nprobe": int(config.nprobe)}},
    )
    if not out:
        return []
    hits = out[0] or []
    rows: list[dict[str, Any]] = []
    for h in hits:
        entity = getattr(h, "entity", None) or {}
        score = getattr(h, "distance", None)
        if isinstance(entity, dict):
            # pymilvus MilvusClient.search() 返回的 Hit.entity 是嵌套结构:
            # {id, distance, entity: {chunk_id, source, text, ...}}
            # 真正的字段数据在 entity['entity'] 中
            inner = entity.get("entity")
            if isinstance(inner, dict):
                row = dict(inner)
            else:
                row = dict(entity)
        else:
            row = {}
            for k in (
                "chunk_id",
                "text",
                "source",
                "file_type",
                "parent_id",
                "section_path",
                "context_brief",
                "start_index",
                "page",
                "start_line",
                "end_line",
            ):
                try:
                    row[k] = getattr(entity, k)
                except Exception:
                    pass
        if isinstance(score, (int, float)):
            row["score"] = float(score)
        rows.append(row)
    return rows

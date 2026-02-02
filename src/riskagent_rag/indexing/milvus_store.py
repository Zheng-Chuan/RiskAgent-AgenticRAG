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
        client.delete(collection_name=str(config.collection_name), filter=expr)
    except TypeError:
        client.delete(collection_name=str(config.collection_name), expr=expr)


def insert_chunks(*, client: MilvusClient, config: MilvusStoreConfig, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    client.insert(collection_name=str(config.collection_name), data=rows)


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

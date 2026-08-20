"""Milvus 存储模块单元测试.

覆盖 indexing/milvus_store.py 的全部函数 (mock MilvusClient):
build_milvus_client / ensure_collection / delete_by_source / insert_chunks /
drop_collection / search (含嵌套 entity 结构).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from riskagent_agenticrag.indexing.milvus_store import (
    MilvusStoreConfig,
    _default_lite_uri,
    build_milvus_client,
    delete_by_source,
    drop_collection,
    ensure_collection,
    insert_chunks,
    search,
)


# ---------------------------------------------------------------------------
# _default_lite_uri
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDefaultLiteUri:
    """默认 lite URI 生成测试."""

    def test_creates_dir_and_returns_uri(self, tmp_path: Path):
        """应创建目录并返回 milvus.db 路径."""
        persist = tmp_path / "milvus_data"
        uri = _default_lite_uri(persist_dir=persist)
        assert persist.exists()
        assert "milvus.db" in uri

    def test_existing_dir_not_error(self, tmp_path: Path):
        """已存在的目录不应报错."""
        persist = tmp_path / "existing"
        persist.mkdir()
        uri = _default_lite_uri(persist_dir=persist)
        assert "milvus.db" in uri


# ---------------------------------------------------------------------------
# build_milvus_client
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildMilvusClient:
    """Milvus 客户端构建测试."""

    def test_uses_milvus_uri_when_set(self, tmp_path: Path):
        """有 MILVUS_URI 环境变量时应直接使用."""
        with patch.dict(os.environ, {"MILVUS_URI": "http://milvus:19530"}), \
             patch("riskagent_agenticrag.indexing.milvus_store.MilvusClient") as mock_cls:
            build_milvus_client(persist_dir=tmp_path)
            _, kwargs = mock_cls.call_args
            assert kwargs["uri"] == "http://milvus:19530"

    def test_uses_host_port_when_set(self, tmp_path: Path):
        """有 MILVUS_HOST + MILVUS_PORT 时应组合 URL."""
        with patch.dict(os.environ, {"MILVUS_HOST": "localhost", "MILVUS_PORT": "19530"}, clear=False), \
             patch.dict(os.environ, {"MILVUS_URI": ""}), \
             patch("riskagent_agenticrag.indexing.milvus_store.MilvusClient") as mock_cls:
            build_milvus_client(persist_dir=tmp_path)
            _, kwargs = mock_cls.call_args
            assert "localhost" in kwargs["uri"]
            assert "19530" in kwargs["uri"]

    def test_falls_back_to_lite_uri(self, tmp_path: Path):
        """无环境变量时应回退到 lite URI."""
        env = {k: v for k, v in os.environ.items() if k not in ("MILVUS_URI", "MILVUS_HOST", "MILVUS_PORT")}
        with patch.dict(os.environ, env, clear=True), \
             patch("riskagent_agenticrag.indexing.milvus_store.MilvusClient") as mock_cls:
            build_milvus_client(persist_dir=tmp_path)
            _, kwargs = mock_cls.call_args
            assert "milvus.db" in kwargs["uri"]


# ---------------------------------------------------------------------------
# ensure_collection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnsureCollection:
    """集合创建测试."""

    def test_skips_when_collection_exists(self):
        """集合已存在时应直接返回."""
        client = MagicMock()
        client.has_collection.return_value = True
        cfg = MilvusStoreConfig(collection_name="test", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        ensure_collection(client=client, config=cfg, dim=64)
        client.create_collection.assert_not_called()

    def test_creates_collection_when_missing(self):
        """集合不存在时应创建."""
        client = MagicMock()
        client.has_collection.return_value = False
        cfg = MilvusStoreConfig(collection_name="test", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        ensure_collection(client=client, config=cfg, dim=64)
        client.create_collection.assert_called_once()
        client.create_index.assert_called_once()

    def test_uses_correct_dimension(self):
        """应使用传入的维度."""
        client = MagicMock()
        client.has_collection.return_value = False
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        ensure_collection(client=client, config=cfg, dim=2560)
        # 验证 schema 中 vector 字段的 dim
        call_args = client.create_collection.call_args
        schema = call_args.kwargs.get("schema") or (call_args.args[1] if len(call_args.args) > 1 else None)
        if schema:
            vector_field = [f for f in schema.fields if f.name == "vector"][0]
            assert vector_field.dim == 2560


# ---------------------------------------------------------------------------
# insert_chunks
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInsertChunks:
    """批量插入测试."""

    def test_empty_rows_returns_without_call(self):
        """空 rows 不应调用 insert."""
        client = MagicMock()
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        insert_chunks(client=client, config=cfg, rows=[])
        client.insert.assert_not_called()

    def test_inserts_in_batches(self):
        """应分批插入 (batch_size=200)."""
        client = MagicMock()
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        rows = [{"chunk_id": f"c{i}"} for i in range(250)]
        insert_chunks(client=client, config=cfg, rows=rows)
        assert client.insert.call_count == 2  # 200 + 50

    def test_small_batch_single_insert(self):
        """小于 200 条应单次插入."""
        client = MagicMock()
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        rows = [{"chunk_id": "c1"}]
        insert_chunks(client=client, config=cfg, rows=rows)
        assert client.insert.call_count == 1


# ---------------------------------------------------------------------------
# drop_collection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDropCollection:
    """集合删除测试."""

    def test_returns_true_when_not_exists(self):
        """集合不存在时返回 True."""
        client = MagicMock()
        client.has_collection.return_value = False
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        assert drop_collection(client=client, config=cfg) is True

    def test_drops_and_returns_true(self):
        """集合存在且删除成功时返回 True."""
        client = MagicMock()
        client.has_collection.return_value = True
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        assert drop_collection(client=client, config=cfg) is True
        client.drop_collection.assert_called_once()

    def test_returns_false_on_exception(self):
        """删除异常时返回 False."""
        client = MagicMock()
        client.has_collection.return_value = True
        client.drop_collection.side_effect = RuntimeError("boom")
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        assert drop_collection(client=client, config=cfg) is False


# ---------------------------------------------------------------------------
# delete_by_source
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeleteBySource:
    """按 source 删除测试."""

    def test_deletes_with_filter(self):
        """应使用 source 过滤器删除."""
        client = MagicMock()
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        delete_by_source(client=client, config=cfg, source="doc.md")
        client.delete.assert_called_once()

    def test_falls_back_to_expr_on_type_error(self):
        """TypeError 时应回退到 expr 参数."""
        client = MagicMock()
        client.load_collection = MagicMock()
        client.delete.side_effect = [TypeError("no filter"), None]
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        delete_by_source(client=client, config=cfg, source="doc.md")
        assert client.delete.call_count == 2

    def test_retries_on_collection_not_loaded(self):
        """collection not loaded 错误时应重试."""
        client = MagicMock()
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        client.delete.side_effect = [RuntimeError("collection not loaded"), None]
        delete_by_source(client=client, config=cfg, source="doc.md")
        assert client.delete.call_count >= 2

    def test_escapes_quotes_in_source(self):
        """source 中的引号应被转义."""
        client = MagicMock()
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        delete_by_source(client=client, config=cfg, source='path"with"quotes.md')
        call_args = client.delete.call_args
        filter_arg = call_args.kwargs.get("filter") or ""
        assert '\\"' in filter_arg


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSearch:
    """向量搜索测试 (含嵌套 entity 结构)."""

    def test_empty_result_returns_empty_list(self):
        """空结果应返回空列表."""
        client = MagicMock()
        client.search.return_value = []
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        result = search(client=client, config=cfg, vector=[0.1] * 64, limit=5)
        assert result == []

    def test_nested_entity_structure_extracted(self):
        """应从嵌套 entity['entity'] 中提取字段数据."""
        hit = MagicMock()
        hit.distance = 0.95
        hit.entity = {"entity": {"chunk_id": "c1", "source": "doc.md", "text": "content"}}
        client = MagicMock()
        client.search.return_value = [[hit]]
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        result = search(client=client, config=cfg, vector=[0.1] * 64, limit=5)
        assert len(result) == 1
        assert result[0]["chunk_id"] == "c1"
        assert result[0]["source"] == "doc.md"
        assert result[0]["score"] == 0.95

    def test_flat_entity_dict_fallback(self):
        """entity 为平铺 dict (无嵌套 entity 键) 时应直接使用."""
        hit = MagicMock()
        hit.distance = 0.8
        hit.entity = {"chunk_id": "c2", "source": "doc2.md", "text": "text2"}
        client = MagicMock()
        client.search.return_value = [[hit]]
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        result = search(client=client, config=cfg, vector=[0.1] * 64, limit=5)
        assert result[0]["chunk_id"] == "c2"

    def test_attribute_fallback_for_non_dict_entity(self):
        """entity 非 dict 时应回退到 getattr 逐字段提取."""
        class FakeEntity:
            chunk_id = "c3"
            source = "doc3.md"
            text = "text3"

        hit = MagicMock()
        hit.distance = 0.7
        hit.entity = FakeEntity()
        client = MagicMock()
        client.search.return_value = [[hit]]
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        result = search(client=client, config=cfg, vector=[0.1] * 64, limit=5)
        assert len(result) == 1
        assert result[0]["chunk_id"] == "c3"
        assert result[0]["score"] == 0.7

    def test_no_score_when_distance_none(self):
        """distance 为 None 时不应添加 score."""
        hit = MagicMock()
        hit.distance = None
        hit.entity = {"chunk_id": "c4"}
        client = MagicMock()
        client.search.return_value = [[hit]]
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        result = search(client=client, config=cfg, vector=[0.1] * 64, limit=5)
        assert "score" not in result[0]

    def test_multiple_hits(self):
        """多 hit 应返回多行."""
        hits = []
        for i in range(3):
            h = MagicMock()
            h.distance = 0.9 - i * 0.1
            h.entity = {"entity": {"chunk_id": f"c{i}", "text": f"text{i}"}}
            hits.append(h)
        client = MagicMock()
        client.search.return_value = [hits]
        cfg = MilvusStoreConfig(collection_name="t", metric_type="COSINE", index_type="IVF_FLAT", nlist=128, nprobe=8)
        result = search(client=client, config=cfg, vector=[0.1] * 64, limit=5)
        assert len(result) == 3

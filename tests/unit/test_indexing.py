"""Unit tests for indexing/indexer.py and indexing/milvus_store.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from riskagent_agenticrag.indexing.milvus_store import (
    MilvusStoreConfig,
    delete_by_source,
    drop_collection,
    ensure_collection,
    insert_chunks,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def milvus_config():
    return MilvusStoreConfig(
        collection_name="test_collection",
        metric_type="IP",
        index_type="IVF_FLAT",
        nlist=128,
        nprobe=16,
    )


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.has_collection.return_value = False
    client.create_collection.return_value = None
    client.prepare_index_params.return_value = MagicMock()
    client.create_index.return_value = None
    client.insert.return_value = None
    client.delete.return_value = None
    client.load_collection.return_value = None
    client.drop_collection.return_value = None
    return client


# ---------------------------------------------------------------------------
# ensure_collection
# ---------------------------------------------------------------------------

class TestEnsureCollection:

    @pytest.mark.unit
    def test_creates_collection_when_not_exists(self, mock_client, milvus_config):
        mock_client.has_collection.return_value = False
        ensure_collection(client=mock_client, config=milvus_config, dim=768)
        mock_client.create_collection.assert_called_once()
        mock_client.create_index.assert_called_once()

    @pytest.mark.unit
    def test_skips_creation_when_exists(self, mock_client, milvus_config):
        mock_client.has_collection.return_value = True
        ensure_collection(client=mock_client, config=milvus_config, dim=768)
        mock_client.create_collection.assert_not_called()


# ---------------------------------------------------------------------------
# insert_chunks / delete_by_source / drop_collection
# ---------------------------------------------------------------------------

class TestMilvusOperations:

    @pytest.mark.unit
    def test_insert_chunks_calls_client(self, mock_client, milvus_config):
        rows = [{"chunk_id": "c1", "vector": [0.1] * 768, "text": "hello"}]
        insert_chunks(client=mock_client, config=milvus_config, rows=rows)
        mock_client.insert.assert_called_once_with(
            collection_name="test_collection", data=rows
        )

    @pytest.mark.unit
    def test_insert_chunks_empty_rows_noop(self, mock_client, milvus_config):
        insert_chunks(client=mock_client, config=milvus_config, rows=[])
        mock_client.insert.assert_not_called()

    @pytest.mark.unit
    def test_delete_by_source_calls_client(self, mock_client, milvus_config):
        delete_by_source(client=mock_client, config=milvus_config, source="/path/to/doc.pdf")
        mock_client.delete.assert_called_once()

    @pytest.mark.unit
    def test_drop_collection_success(self, mock_client, milvus_config):
        mock_client.has_collection.return_value = True
        result = drop_collection(client=mock_client, config=milvus_config)
        assert result is True
        mock_client.drop_collection.assert_called_once()

    @pytest.mark.unit
    def test_drop_collection_not_exists(self, mock_client, milvus_config):
        mock_client.has_collection.return_value = False
        result = drop_collection(client=mock_client, config=milvus_config)
        assert result is True
        mock_client.drop_collection.assert_not_called()

    @pytest.mark.unit
    def test_drop_collection_exception_returns_false(self, mock_client, milvus_config):
        mock_client.has_collection.return_value = True
        mock_client.drop_collection.side_effect = RuntimeError("connection lost")
        result = drop_collection(client=mock_client, config=milvus_config)
        assert result is False


# ---------------------------------------------------------------------------
# Manifest generation and consistency
# ---------------------------------------------------------------------------

class TestManifest:

    @pytest.mark.unit
    def test_load_manifest_missing_file(self, tmp_path):
        from riskagent_agenticrag.indexing.indexer import _load_manifest
        result = _load_manifest(persist_dir=tmp_path)
        assert result["version"] == 2
        assert result["sources"] == {}
        assert result["schema"] == {}
        assert result["schema_fingerprint"] == ""

    @pytest.mark.unit
    def test_write_and_load_manifest(self, tmp_path):
        from riskagent_agenticrag.indexing.indexer import _load_manifest, _write_manifest
        data = {
            "version": 2,
            "schema": {"name": "v2"},
            "schema_fingerprint": "fp1",
            "sources": {"doc.pdf": {"sha1": "abc123", "chunks": 10}},
        }
        _write_manifest(persist_dir=tmp_path, data=data)
        loaded = _load_manifest(persist_dir=tmp_path)
        assert loaded["sources"]["doc.pdf"]["sha1"] == "abc123"
        assert loaded["sources"]["doc.pdf"]["chunks"] == 10
        assert loaded["schema_fingerprint"] == "fp1"

    @pytest.mark.unit
    def test_write_manifest_creates_dir(self, tmp_path):
        from riskagent_agenticrag.indexing.indexer import _write_manifest
        nested = tmp_path / "a" / "b" / "c"
        _write_manifest(
            persist_dir=nested,
            data={"version": 2, "schema": {}, "schema_fingerprint": "", "sources": {}},
        )
        assert (nested / "index_manifest.json").exists()

    @pytest.mark.unit
    def test_load_manifest_corrupted_file(self, tmp_path):
        from riskagent_agenticrag.indexing.indexer import _load_manifest
        manifest_path = tmp_path / "index_manifest.json"
        manifest_path.write_text("not valid json {{{{", encoding="utf-8")
        result = _load_manifest(persist_dir=tmp_path)
        assert result["version"] == 2
        assert result["sources"] == {}
        assert result["schema"] == {}

    @pytest.mark.unit
    def test_incremental_index_rebuilds_when_manifest_schema_changes(self, tmp_path, monkeypatch):
        from riskagent_agenticrag.indexing.indexer import incremental_index

        corpus_dir = tmp_path / "corpus"
        persist_dir = tmp_path / "persist"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        source_path = corpus_dir / "doc.md"
        source_path.write_text("# Title\nBody\n", encoding="utf-8")
        persist_dir.mkdir(parents=True, exist_ok=True)
        (persist_dir / "index_manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "sources": {str(source_path): {"sha1": "legacy-sha1", "chunks": 1}},
                }
            ),
            encoding="utf-8",
        )

        raw_doc = Document(page_content="# Title\nBody\n", metadata={"source": str(source_path), "file_type": "md"})
        chunk_doc = Document(page_content="Body", metadata={"source": str(source_path), "chunk_id": "c1"})
        parent_doc = Document(page_content="Body", metadata={"source": str(source_path), "parent_id": "p1"})

        class FakeEmbeddings:
            def embed_query(self, _: str):
                return [0.1, 0.2]

            def embed_documents(self, texts):
                return [[0.1, 0.2] for _ in texts]

        mock_client = MagicMock()

        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.load_sources", lambda _: [raw_doc])
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.build_embeddings", lambda: FakeEmbeddings())
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.build_parent_documents", lambda _: [parent_doc])
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.split_documents", lambda _: [chunk_doc])
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.build_summary_docs", lambda _: [])
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.build_hyde_docs", lambda _: [])
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.build_milvus_client", lambda persist_dir: mock_client)
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.ensure_collection", lambda **_: None)
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.delete_by_source", lambda **_: None)
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.insert_chunks", lambda **_: None)

        drop_calls = []

        def _fake_drop_collection(*, client, config):
            drop_calls.append((client, config.collection_name))
            return True

        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.drop_collection", _fake_drop_collection)

        result = incremental_index(corpus_dir=corpus_dir, persist_dir=persist_dir, include_paths=None)

        assert result.indexed_sources == [str(source_path)]
        assert drop_calls, "schema change should trigger full persisted index reset"

        manifest = json.loads((persist_dir / "index_manifest.json").read_text(encoding="utf-8"))
        assert manifest["version"] == 2
        assert manifest["schema_fingerprint"]
        assert manifest["sources"][str(source_path)]["chunks"] == 1

    @pytest.mark.unit
    def test_incremental_index_rejects_partial_include_on_schema_change(self, tmp_path, monkeypatch):
        from riskagent_agenticrag.indexing.indexer import incremental_index

        corpus_dir = tmp_path / "corpus"
        persist_dir = tmp_path / "persist"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        source_path = corpus_dir / "doc.md"
        source_path.write_text("# Title\nBody\n", encoding="utf-8")
        persist_dir.mkdir(parents=True, exist_ok=True)
        (persist_dir / "index_manifest.json").write_text(
            json.dumps({"version": 1, "sources": {str(source_path): {"sha1": "legacy-sha1"}}}),
            encoding="utf-8",
        )

        raw_doc = Document(page_content="# Title\nBody\n", metadata={"source": str(source_path), "file_type": "md"})

        class FakeEmbeddings:
            def embed_query(self, _: str):
                return [0.1, 0.2]

        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.load_sources", lambda _: [raw_doc])
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.build_embeddings", lambda: FakeEmbeddings())
        monkeypatch.setattr("riskagent_agenticrag.indexing.indexer.build_milvus_client", lambda persist_dir: MagicMock())

        with pytest.raises(ValueError, match="full rebuild"):
            incremental_index(corpus_dir=corpus_dir, persist_dir=persist_dir, include_paths=[source_path])


# ---------------------------------------------------------------------------
# Error handling when Milvus is unavailable
# ---------------------------------------------------------------------------

class TestMilvusUnavailable:

    @pytest.mark.unit
    def test_delete_by_source_handles_type_error(self, mock_client, milvus_config):
        """When client.delete raises TypeError, should retry with expr kwarg."""
        mock_client.delete.side_effect = [TypeError("unexpected kwarg"), None]
        # Should not raise
        delete_by_source(client=mock_client, config=milvus_config, source="test.pdf")
        assert mock_client.delete.call_count == 2

    @pytest.mark.unit
    def test_ensure_collection_propagates_error(self, mock_client, milvus_config):
        mock_client.has_collection.return_value = False
        mock_client.create_collection.side_effect = RuntimeError("Milvus unreachable")
        with pytest.raises(RuntimeError, match="Milvus unreachable"):
            ensure_collection(client=mock_client, config=milvus_config, dim=768)

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from langchain_core.documents import Document  # type: ignore[import-not-found]

from riskagent_agenticrag.config.settings import settings
from riskagent_agenticrag.indexing.milvus_store import (
    MilvusStoreConfig,
    build_milvus_client,
    delete_by_source,
    drop_collection,
    ensure_collection,
    insert_chunks,
)
from riskagent_agenticrag.rag.advanced_index import (
    HYDE_CORPUS_FILENAME,
    PARENT_CORPUS_FILENAME,
    SUMMARY_CORPUS_FILENAME,
    build_hyde_docs,
    build_summary_docs,
)
from riskagent_agenticrag.rag.embeddings import build_embeddings
from riskagent_agenticrag.rag.ingestion import build_parent_documents, split_documents
from riskagent_agenticrag.rag.source_loader import load_sources
from riskagent_agenticrag.rag.sparse_index import SPARSE_CORPUS_FILENAME


MANIFEST_FILENAME = "index_manifest.json"
MANIFEST_VERSION = 2
DEFAULT_CHUNKING_CONFIG = {
    "use_llm_chunking": True,
    "max_chunk_size": 800,
    "overlap": 100,
    "policy_version": "split_documents_v1",
}
DEFAULT_ADVANCED_INDEX_CONFIG = {
    "summary_strategy": "extractive_head_or_sentence_v1",
    "summary_max_chars": 900,
    "hyde_strategy": "section_path_plus_summary_v1",
    "parent_expand_source": "parent_corpus_v1",
}


@dataclass(frozen=True)
class IncrementalIndexResult:
    indexed_sources: list[str]
    skipped_sources: list[str]
    chunk_indexed: int
    persist_dir: str


def _file_sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _load_manifest(*, persist_dir: Path) -> dict[str, Any]:
    skeleton = {
        "version": MANIFEST_VERSION,
        "schema": {},
        "schema_fingerprint": "",
        "sources": {},
        "embeddings": {},
    }
    path = persist_dir / MANIFEST_FILENAME
    if not path.exists():
        return skeleton
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return skeleton
        merged = dict(skeleton)
        merged.update(loaded)
        if not isinstance(merged.get("sources"), dict):
            merged["sources"] = {}
        if not isinstance(merged.get("schema"), dict):
            merged["schema"] = {}
        if not isinstance(merged.get("embeddings"), dict):
            merged["embeddings"] = {}
        return merged
    except Exception:
        return skeleton


def _write_manifest(*, persist_dir: Path, data: dict[str, Any]) -> None:
    persist_dir.mkdir(parents=True, exist_ok=True)
    path = persist_dir / MANIFEST_FILENAME
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _schema_fingerprint(schema: dict[str, Any]) -> str:
    return hashlib.sha1(_stable_json_dumps(schema).encode("utf-8")).hexdigest()


def _current_index_schema(*, dim: int, milvus_config: MilvusStoreConfig) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_VERSION,
        "embeddings": {
            "provider": str(settings.embeddings.provider),
            "model": str(settings.embeddings.model_name),
            "dim": int(dim),
        },
        "milvus": {
            "collection_name": str(milvus_config.collection_name),
            "metric_type": str(milvus_config.metric_type),
            "index_type": str(milvus_config.index_type),
            "nlist": int(milvus_config.nlist),
            "nprobe": int(milvus_config.nprobe),
        },
        "chunking": dict(DEFAULT_CHUNKING_CONFIG),
        "advanced_index": dict(DEFAULT_ADVANCED_INDEX_CONFIG),
        "features": {
            "retrieval_pipeline": str(settings.features.retrieval_pipeline),
            "prompt_version": str(settings.features.prompt_version),
            "query_intel_enabled": bool(settings.features.query_intel_enabled),
            "self_rag_enabled": bool(settings.features.self_rag_enabled),
        },
        "source_loader": {
            "loader_version": "load_sources_v1",
            "parent_builder_version": "build_parent_documents_v1",
        },
    }


def _manifest_has_schema_mismatch(*, manifest: dict[str, Any], schema: dict[str, Any]) -> bool:
    current_fingerprint = _schema_fingerprint(schema)
    previous_fingerprint = str(manifest.get("schema_fingerprint", "") or "").strip()
    previous_version = int(manifest.get("version", 0) or 0)
    if previous_version != MANIFEST_VERSION:
        return True
    if not previous_fingerprint:
        return True
    return previous_fingerprint != current_fingerprint


def _reset_persisted_index_artifacts(*, persist_dir: Path, client: Any, milvus_config: MilvusStoreConfig) -> None:
    dropped = drop_collection(client=client, config=milvus_config)
    if not dropped:
        raise RuntimeError("Failed to drop stale Milvus collection during schema migration")
    for filename in (
        SPARSE_CORPUS_FILENAME,
        PARENT_CORPUS_FILENAME,
        SUMMARY_CORPUS_FILENAME,
        HYDE_CORPUS_FILENAME,
    ):
        path = persist_dir / filename
        if path.exists():
            path.unlink()


def _upsert_jsonl(*, path: Path, source: str, docs: Iterable[Document]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    src = str(source)
    kept: list[str] = []
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                row = json.loads(ln)
            except Exception:
                continue
            meta = row.get("metadata") or {}
            if isinstance(meta, dict) and str(meta.get("source", "")) == src:
                continue
            kept.append(json.dumps(row, ensure_ascii=False))

    added: list[str] = []
    for d in docs:
        row = {"page_content": d.page_content or "", "metadata": d.metadata or {}}
        added.append(json.dumps(row, ensure_ascii=False))

    out = kept + added
    path.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")


def incremental_index(
    *,
    corpus_dir: Path,
    persist_dir: Path,
    include_paths: list[Path] | None = None,
) -> IncrementalIndexResult:
    corpus_dir = Path(corpus_dir)
    persist_dir = Path(persist_dir)
    sources = load_sources(corpus_dir)

    selected: list[str] = []
    if include_paths:
        wanted = {str(Path(p).absolute()) for p in include_paths}
        for d in sources:
            src = str((d.metadata or {}).get("source", ""))
            if src and str(Path(src).absolute()) in wanted:
                selected.append(src)
        sources = [d for d in sources if str((d.metadata or {}).get("source", "")) in selected]

    embeddings = build_embeddings()
    dim = len(embeddings.embed_query("dim_probe"))

    cfg = MilvusStoreConfig(
        collection_name=settings.milvus.collection_name,
        metric_type=settings.milvus.metric_type,
        index_type=settings.milvus.index_type,
        nlist=settings.milvus.nlist,
        nprobe=settings.milvus.nprobe,
    )
    manifest = _load_manifest(persist_dir=persist_dir)
    current_schema = _current_index_schema(dim=int(dim), milvus_config=cfg)
    schema_changed = _manifest_has_schema_mismatch(manifest=manifest, schema=current_schema)
    src_map = manifest.get("sources")
    if not isinstance(src_map, dict):
        src_map = {}
    manifest["sources"] = src_map

    client = build_milvus_client(persist_dir=persist_dir)
    if schema_changed:
        if include_paths:
            raise ValueError("Index schema changed; rerun incremental_index without include_paths for a full rebuild")
        _reset_persisted_index_artifacts(persist_dir=persist_dir, client=client, milvus_config=cfg)
        src_map = {}
        manifest["sources"] = src_map
    ensure_collection(client=client, config=cfg, dim=int(dim))

    indexed_sources: list[str] = []
    skipped_sources: list[str] = []
    chunk_indexed = 0

    per_source_docs: dict[str, list[Document]] = {}
    for d in sources:
        src = str((d.metadata or {}).get("source", "")).strip()
        if not src:
            continue
        per_source_docs.setdefault(src, [])
        per_source_docs[src].append(d)

    for src, docs in per_source_docs.items():
        p = Path(src)
        digest = _file_sha1(p) if p.exists() else ""
        prev = src_map.get(src) if isinstance(src_map, dict) else None
        if (not schema_changed) and isinstance(prev, dict) and str(prev.get("sha1", "")) == digest and digest:
            skipped_sources.append(src)
            continue

        parents = build_parent_documents(docs)
        chunks = split_documents(docs)

        delete_by_source(client=client, config=cfg, source=src)

        texts = [c.page_content or "" for c in chunks]
        vecs = embeddings.embed_documents(texts) if texts else []
        rows: list[dict[str, Any]] = []
        for c, v in zip(chunks, vecs):
            meta = c.metadata or {}
            rows.append(
                {
                    "chunk_id": str(meta.get("chunk_id", "")),
                    "vector": list(v),
                    "text": str(c.page_content or ""),
                    "source": str(meta.get("source", "")),
                    "file_type": str(meta.get("file_type", "")),
                    "parent_id": str(meta.get("parent_id", "")),
                    "section_path": str(meta.get("section_path", "")),
                    "start_index": int(meta.get("start_index", 0) or 0),
                    "page": int(meta.get("page", 0) or 0),
                    "start_line": int(meta.get("start_line", 0) or 0),
                    "end_line": int(meta.get("end_line", 0) or 0),
                }
            )

        insert_chunks(client=client, config=cfg, rows=rows)
        chunk_indexed += len(rows)

        sparse_path = persist_dir / SPARSE_CORPUS_FILENAME
        _upsert_jsonl(path=sparse_path, source=src, docs=chunks)

        parent_path = persist_dir / PARENT_CORPUS_FILENAME
        _upsert_jsonl(path=parent_path, source=src, docs=parents)

        summary_docs = build_summary_docs(parents)
        summary_path = persist_dir / SUMMARY_CORPUS_FILENAME
        _upsert_jsonl(path=summary_path, source=src, docs=summary_docs)

        hyde_docs = build_hyde_docs(parents)
        hyde_path = persist_dir / HYDE_CORPUS_FILENAME
        _upsert_jsonl(path=hyde_path, source=src, docs=hyde_docs)

        src_map[src] = {
            "sha1": digest,
            "chunks": int(len(rows)),
            "parents": int(len(parents)),
            "summaries": int(len(summary_docs)),
            "hydes": int(len(hyde_docs)),
        }
        indexed_sources.append(src)

    manifest["version"] = MANIFEST_VERSION
    manifest["schema"] = current_schema
    manifest["schema_fingerprint"] = _schema_fingerprint(current_schema)
    manifest["embeddings"] = dict(current_schema.get("embeddings") or {})
    _write_manifest(persist_dir=persist_dir, data=manifest)

    return IncrementalIndexResult(
        indexed_sources=indexed_sources,
        skipped_sources=skipped_sources,
        chunk_indexed=int(chunk_indexed),
        persist_dir=str(persist_dir),
    )

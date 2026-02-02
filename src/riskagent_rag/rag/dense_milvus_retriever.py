from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.documents import Document  # type: ignore[import-not-found]

from riskagent_rag.config.settings import settings
from riskagent_rag.indexing.milvus_store import MilvusStoreConfig, build_milvus_client, ensure_collection, search
from riskagent_rag.rag.embeddings import build_embeddings


@dataclass(frozen=True)
class DenseMilvusRetrieverConfig:
    k: int = 30


class DenseMilvusRetriever:
    def __init__(self, *, persist_dir: Path, config: DenseMilvusRetrieverConfig) -> None:
        self._persist_dir = Path(persist_dir)
        self._config = config
        self._embeddings = build_embeddings()
        dim = len(self._embeddings.embed_query("dim_probe"))
        self._milvus_cfg = MilvusStoreConfig(
            collection_name=settings.milvus.collection_name,
            metric_type=settings.milvus.metric_type,
            index_type=settings.milvus.index_type,
            nlist=settings.milvus.nlist,
            nprobe=settings.milvus.nprobe,
        )
        self._client = build_milvus_client(persist_dir=self._persist_dir)
        ensure_collection(client=self._client, config=self._milvus_cfg, dim=int(dim))

    def invoke(self, query: str) -> list[Document]:
        q = str(query or "").strip()
        if not q:
            return []
        vec = self._embeddings.embed_query(q)
        rows = search(client=self._client, config=self._milvus_cfg, vector=list(vec), limit=int(self._config.k))
        docs: list[Document] = []
        for rank, r in enumerate(rows, start=1):
            meta: dict[str, Any] = {
                "chunk_id": str(r.get("chunk_id", "")),
                "source": str(r.get("source", "")),
                "file_type": str(r.get("file_type", "")),
                "parent_id": str(r.get("parent_id", "")),
                "section_path": str(r.get("section_path", "")),
                "start_index": int(r.get("start_index", 0) or 0),
                "page": int(r.get("page", 0) or 0),
                "start_line": int(r.get("start_line", 0) or 0),
                "end_line": int(r.get("end_line", 0) or 0),
                "dense_rank": int(rank),
            }
            if isinstance(r.get("score"), (int, float)):
                meta["dense_score"] = float(r["score"])
            docs.append(Document(page_content=str(r.get("text", "") or ""), metadata=meta))
        return docs


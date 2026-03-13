"""RAG 共享工具函数 -- tokenize / doc_key / rrf / JSONL 读写."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

# ---- 分词 ----

_TOKEN_RE = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    """将文本分词为小写 token 列表 (英文/数字/中文)."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]


def token_set(text: str) -> set[str]:
    """将文本分词为小写 token 集合 (去重)."""
    return set(tokenize(text))


# ---- Document 去重键 ----

def doc_key(d: Document) -> str:
    """为 Document 生成唯一键, 优先用 source::chunk_id, 回退到 page_content hash."""
    meta = d.metadata or {}
    chunk_id = str(meta.get("chunk_id", "")).strip()
    source = str(meta.get("source", "")).strip()
    if chunk_id and source:
        return f"{source}::{chunk_id}"
    return str(hash(d.page_content or ""))


# ---- RRF 融合 ----

def rrf_scores(*, ranked_lists: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal Rank Fusion: 将多路排序列表融合为统一分数."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, key in enumerate(ranked):
            scores[key] = scores.get(key, 0.0) + 1.0 / float(k + rank + 1)
    return scores


# ---- JSONL 持久化 ----

def persist_docs_jsonl(docs: list[Document], path: Path) -> str:
    """将 Document 列表写入 JSONL 文件."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for d in docs:
            row = {"page_content": d.page_content or "", "metadata": d.metadata or {}}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return str(path)


def load_docs_jsonl(path: Path) -> list[Document]:
    """从 JSONL 文件加载 Document 列表."""
    if not path.exists():
        return []
    docs: list[Document] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        page_content = str(data.get("page_content", "") or "")
        metadata = data.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        docs.append(Document(page_content=page_content, metadata=metadata))
    return docs

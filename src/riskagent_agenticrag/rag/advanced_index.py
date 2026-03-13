"""高级索引 -- Parent / Summary / HyDE 语料构建与持久化."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from riskagent_agenticrag.rag.utils import load_docs_jsonl, persist_docs_jsonl

PARENT_CORPUS_FILENAME = "parent_corpus.jsonl"
SUMMARY_CORPUS_FILENAME = "summary_corpus.jsonl"
HYDE_CORPUS_FILENAME = "hyde_corpus.jsonl"

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


# ---------------------------------------------------------------------------
# Parent 语料
# ---------------------------------------------------------------------------

def persist_parent_corpus(*, parents: list[Document], persist_dir: Path) -> str:
    return persist_docs_jsonl(parents, persist_dir / PARENT_CORPUS_FILENAME)


def load_parent_corpus(*, persist_dir: Path) -> list[Document]:
    return load_docs_jsonl(persist_dir / PARENT_CORPUS_FILENAME)


def parent_corpus_by_id(*, persist_dir: Path) -> dict[str, Document]:
    out: dict[str, Document] = {}
    for d in load_parent_corpus(persist_dir=persist_dir):
        pid = str((d.metadata or {}).get("parent_id") or "").strip()
        if pid:
            out[pid] = d
    return out


# ---------------------------------------------------------------------------
# Summary 语料
# ---------------------------------------------------------------------------

def _extractive_summary(text: str, *, max_chars: int = 900) -> str:
    """从文本中提取摘要: 优先取前 12 行, 不够则按句子拼接."""
    raw = str(text or "").strip()
    if not raw:
        return ""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    head = "\n".join(lines[:12]).strip()
    if len(head) >= min(max_chars, 240):
        return head[:max_chars]
    sentences = _SENTENCE_SPLIT_RE.split(raw)
    keep: list[str] = []
    total = 0
    for s in sentences:
        s1 = str(s or "").strip()
        if not s1 or len(s1) < 30:
            continue
        keep.append(s1)
        total += len(s1) + 1
        if total >= max_chars:
            break
    out = " ".join(keep).strip()
    return (out or head)[:max_chars]


def build_summary_docs(parents: list[Document]) -> list[Document]:
    out: list[Document] = []
    for d in parents:
        meta = dict(d.metadata or {})
        pid = str(meta.get("parent_id") or "").strip()
        if not pid:
            continue
        summary = _extractive_summary(d.page_content or "")
        if not summary:
            continue
        row_meta = {k: v for k, v in meta.items() if k != "text"}
        row_meta["doc_type"] = "summary"
        row_meta["parent_id"] = pid
        out.append(Document(page_content=summary, metadata=row_meta))
    return out


def persist_summary_corpus(*, parents: list[Document], persist_dir: Path) -> str:
    return persist_docs_jsonl(build_summary_docs(parents), persist_dir / SUMMARY_CORPUS_FILENAME)


def load_summary_corpus(*, persist_dir: Path) -> list[Document]:
    return load_docs_jsonl(persist_dir / SUMMARY_CORPUS_FILENAME)


# ---------------------------------------------------------------------------
# HyDE 语料
# ---------------------------------------------------------------------------

def _hyde_question(text: str, *, section_path: str) -> str:
    """根据文本和 section_path 生成假设性问题 (HyDE)."""
    base = str(section_path or "").strip()
    last = ""
    if base:
        last = re.sub(r"\s+", " ", base.split("/")[-1].strip())
    summary = _extractive_summary(text, max_chars=240)
    kw = " ".join(re.findall(r"[A-Za-z0-9]+", summary)[:12])
    if last:
        return f"What is {last} and why does it matter {kw}".strip()
    if kw:
        return f"What is {kw} and how is it used in risk systems".strip()
    return "What is the definition and background"


def build_hyde_docs(parents: list[Document]) -> list[Document]:
    out: list[Document] = []
    for d in parents:
        meta = dict(d.metadata or {})
        pid = str(meta.get("parent_id") or "").strip()
        if not pid:
            continue
        q = _hyde_question(d.page_content or "", section_path=str(meta.get("section_path") or ""))
        if not q:
            continue
        row_meta = {k: v for k, v in meta.items() if k != "text"}
        row_meta["doc_type"] = "hyde"
        row_meta["parent_id"] = pid
        out.append(Document(page_content=q, metadata=row_meta))
    return out


def persist_hyde_corpus(*, parents: list[Document], persist_dir: Path) -> str:
    return persist_docs_jsonl(build_hyde_docs(parents), persist_dir / HYDE_CORPUS_FILENAME)


def load_hyde_corpus(*, persist_dir: Path) -> list[Document]:
    return load_docs_jsonl(persist_dir / HYDE_CORPUS_FILENAME)


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AdvancedIndexStats:
    parents: int
    summaries: int
    hydes: int


def advanced_index_stats(*, persist_dir: Path) -> dict[str, Any]:
    return {
        "parents": len(load_parent_corpus(persist_dir=persist_dir)),
        "summaries": len(load_summary_corpus(persist_dir=persist_dir)),
        "hydes": len(load_hyde_corpus(persist_dir=persist_dir)),
        "parent_path": str(persist_dir / PARENT_CORPUS_FILENAME),
        "summary_path": str(persist_dir / SUMMARY_CORPUS_FILENAME),
        "hyde_path": str(persist_dir / HYDE_CORPUS_FILENAME),
    }

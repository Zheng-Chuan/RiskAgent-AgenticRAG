from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.documents import Document  # type: ignore[import-not-found]


PARENT_CORPUS_FILENAME = "parent_corpus.jsonl"
SUMMARY_CORPUS_FILENAME = "summary_corpus.jsonl"
HYDE_CORPUS_FILENAME = "hyde_corpus.jsonl"


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def persist_parent_corpus(*, parents: list[Document], persist_dir: Path) -> str:
    persist_dir.mkdir(parents=True, exist_ok=True)
    path = persist_dir / PARENT_CORPUS_FILENAME
    with path.open("w", encoding="utf-8") as f:
        for d in parents:
            meta = d.metadata or {}
            row = {"page_content": d.page_content or "", "metadata": meta}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return str(path)


def load_parent_corpus(*, persist_dir: Path) -> list[Document]:
    path = persist_dir / PARENT_CORPUS_FILENAME
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


def parent_corpus_by_id(*, persist_dir: Path) -> dict[str, Document]:
    out: dict[str, Document] = {}
    for d in load_parent_corpus(persist_dir=persist_dir):
        pid = str((d.metadata or {}).get("parent_id") or "").strip()
        if not pid:
            continue
        out[pid] = d
    return out


def _extractive_summary(text: str, *, max_chars: int = 900) -> str:
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
        if not s1:
            continue
        if len(s1) < 30:
            continue
        keep.append(s1)
        total += len(s1) + 1
        if total >= max_chars:
            break
    out = " ".join(keep).strip()
    if out:
        return out[:max_chars]
    return head[:max_chars]


def _hyde_question(text: str, *, section_path: str) -> str:
    base = str(section_path or "").strip()
    if base:
        last = base.split("/")[-1].strip()
        last = re.sub(r"\s+", " ", last)
    else:
        last = ""
    summary = _extractive_summary(text, max_chars=240)
    toks = re.findall(r"[A-Za-z0-9]+", summary)[:12]
    kw = " ".join(toks)
    if last:
        return f"What is {last} and why does it matter {kw}".strip()
    if kw:
        return f"What is {kw} and how is it used in risk systems".strip()
    return "What is the definition and background".strip()


def build_summary_docs(parents: list[Document]) -> list[Document]:
    out: list[Document] = []
    for d in parents:
        meta = dict(d.metadata or {})
        pid = str(meta.get("parent_id") or "").strip()
        if not pid:
            continue
        text = str(d.page_content or "")
        summary = _extractive_summary(text)
        if not summary:
            continue
        row_meta = {k: v for k, v in meta.items() if k != "text"}
        row_meta["doc_type"] = "summary"
        row_meta["parent_id"] = pid
        out.append(Document(page_content=summary, metadata=row_meta))
    return out


def build_hyde_docs(parents: list[Document]) -> list[Document]:
    out: list[Document] = []
    for d in parents:
        meta = dict(d.metadata or {})
        pid = str(meta.get("parent_id") or "").strip()
        if not pid:
            continue
        section_path = str(meta.get("section_path") or "")
        text = str(d.page_content or "")
        q = _hyde_question(text, section_path=section_path)
        if not q:
            continue
        row_meta = {k: v for k, v in meta.items() if k != "text"}
        row_meta["doc_type"] = "hyde"
        row_meta["parent_id"] = pid
        out.append(Document(page_content=q, metadata=row_meta))
    return out


def persist_summary_corpus(*, parents: list[Document], persist_dir: Path) -> str:
    persist_dir.mkdir(parents=True, exist_ok=True)
    path = persist_dir / SUMMARY_CORPUS_FILENAME
    with path.open("w", encoding="utf-8") as f:
        for d in build_summary_docs(parents):
            row = {"page_content": d.page_content or "", "metadata": d.metadata or {}}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return str(path)


def persist_hyde_corpus(*, parents: list[Document], persist_dir: Path) -> str:
    persist_dir.mkdir(parents=True, exist_ok=True)
    path = persist_dir / HYDE_CORPUS_FILENAME
    with path.open("w", encoding="utf-8") as f:
        for d in build_hyde_docs(parents):
            row = {"page_content": d.page_content or "", "metadata": d.metadata or {}}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return str(path)


def _load_jsonl_docs(path: Path) -> list[Document]:
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


def load_summary_corpus(*, persist_dir: Path) -> list[Document]:
    return _load_jsonl_docs(persist_dir / SUMMARY_CORPUS_FILENAME)


def load_hyde_corpus(*, persist_dir: Path) -> list[Document]:
    return _load_jsonl_docs(persist_dir / HYDE_CORPUS_FILENAME)


@dataclass(frozen=True)
class AdvancedIndexStats:
    parents: int
    summaries: int
    hydes: int


def advanced_index_stats(*, persist_dir: Path) -> dict[str, Any]:
    parents = len(load_parent_corpus(persist_dir=persist_dir))
    summaries = len(load_summary_corpus(persist_dir=persist_dir))
    hydes = len(load_hyde_corpus(persist_dir=persist_dir))
    return {
        "parents": int(parents),
        "summaries": int(summaries),
        "hydes": int(hydes),
        "parent_path": str(persist_dir / PARENT_CORPUS_FILENAME),
        "summary_path": str(persist_dir / SUMMARY_CORPUS_FILENAME),
        "hyde_path": str(persist_dir / HYDE_CORPUS_FILENAME),
    }

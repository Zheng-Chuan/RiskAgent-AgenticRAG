"""Ingestion 入口 -- 文档加载, Markdown 解析, 切分与元数据丰富."""

from __future__ import annotations

import hashlib
import pathlib
import re
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from riskagent_agenticrag.rag.chunking import llm_semantic_split_document


# ---------------------------------------------------------------------------
# Markdown 解析工具
# ---------------------------------------------------------------------------

_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _compute_line_range(*, full_text: str, start_index: int, chunk_text: str) -> tuple[int, int]:
    prefix = full_text[: max(0, start_index)]
    start_line = prefix.count("\n") + 1
    end_index = max(0, start_index) + len(chunk_text)
    end_line = full_text[:end_index].count("\n") + 1
    return start_line, end_line


def _markdown_sections(text: str) -> list[tuple[str, str, int, int, int]]:
    """解析 Markdown 文本, 按标题拆分为 (section_path, text, start_line, end_line, start_char)."""
    lines = (text or "").splitlines()
    if not lines:
        return []

    offsets: list[int] = []
    pos = 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1

    sections: list[tuple[str, str, int, int, int]] = []
    stack: list[tuple[int, str]] = []

    current_start = 0
    current_path = ""

    def _path_from_stack() -> str:
        return " / ".join([t for _, t in stack])

    for idx, ln in enumerate(lines):
        m = _MD_HEADING_RE.match(ln)
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()

        if idx > current_start:
            sections.append(
                (
                    current_path,
                    "\n".join(lines[current_start:idx]),
                    current_start,
                    idx,
                    offsets[current_start],
                )
            )

        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        current_path = _path_from_stack()
        current_start = idx

    sections.append(
        (
            current_path,
            "\n".join(lines[current_start:]),
            current_start,
            len(lines),
            offsets[current_start] if current_start < len(offsets) else 0,
        )
    )
    return sections


def _stable_parent_id(*, source: str, section_path: str, start_char: int, page: int) -> str:
    material = f"{source}:{section_path}:{int(start_char)}:{int(page)}".encode("utf-8")
    return hashlib.sha1(material).hexdigest()[:12]


# ---------------------------------------------------------------------------
# build_parent_documents
# ---------------------------------------------------------------------------

def build_parent_documents(docs: list[Document]) -> list[Document]:
    """从原始文档构建 parent documents (MD section / PDF page / 整文档)."""
    parents: list[Document] = []
    for d in docs:
        meta = dict(d.metadata or {})
        source = str(meta.get("source", ""))
        file_type = str(meta.get("file_type", "")).lower().strip()
        page = int(meta.get("page") or 0)
        content = d.page_content or ""

        if source.lower().endswith(".md") or file_type == "md":
            sections = _markdown_sections(content)
            if sections:
                for section_path, section_text, start_line0, end_line0, start_char in sections:
                    text = str(section_text or "").strip()
                    if not text:
                        continue
                    parent_id = _stable_parent_id(
                        source=source,
                        section_path=str(section_path or ""),
                        start_char=int(start_char),
                        page=0,
                    )
                    parents.append(
                        Document(
                            page_content=text,
                            metadata={
                                **meta,
                                "parent_id": parent_id,
                                "parent_type": "md_section",
                                "section_path": str(section_path or ""),
                                "start_index": int(start_char),
                                "start_line": int(start_line0 + 1),
                                "end_line": int(end_line0),
                                "page": 0,
                            },
                        )
                    )
                continue

            parent_id = _stable_parent_id(source=source, section_path="", start_char=0, page=0)
            parents.append(
                Document(
                    page_content=content,
                    metadata={
                        **meta,
                        "parent_id": parent_id,
                        "parent_type": "md_file",
                        "section_path": "",
                        "start_index": 0,
                        "start_line": 1,
                        "end_line": max(1, (content or "").count("\n") + 1),
                        "page": 0,
                    },
                )
            )
            continue

        parent_id = _stable_parent_id(source=source, section_path="", start_char=0, page=page)
        parents.append(
            Document(
                page_content=content,
                metadata={
                    **meta,
                    "parent_id": parent_id,
                    "parent_type": "pdf_page" if page else "doc",
                    "section_path": "",
                    "start_index": 0,
                    "start_line": 0,
                    "end_line": 0,
                    "page": int(page),
                },
            )
        )

    return parents


# ---------------------------------------------------------------------------
# split_documents (主入口)
# ---------------------------------------------------------------------------

def split_documents(
    docs: list[Document],
    *,
    use_llm_chunking: bool = True,
    max_chunk_size: int = 800,
    overlap: int = 100,
) -> list[Document]:
    """将原始文档切分为 chunks.

    支持基于 LLM 的智能语义切割和传统字符切割两种模式.

    Args:
        docs: 原始文档列表.
        use_llm_chunking: 是否使用 LLM 语义切割 (默认 True)
        max_chunk_size: 每个 chunk 的最大字符数
        overlap: chunk 之间的重叠字符数

    Returns:
        切分后的 chunks 列表.
    """
    # 1) Markdown section 丰富
    enriched_docs: list[Document] = []
    for d in docs:
        meta = dict(d.metadata or {})
        source = str(meta.get("source", ""))
        file_type = str(meta.get("file_type", "")).lower().strip()
        content = d.page_content or ""

        if source.lower().endswith(".md") or file_type == "md":
            sections = _markdown_sections(content)
            if sections:
                for section_path, section_text, start_line0, end_line0, start_char in sections:
                    if not section_text.strip():
                        continue
                    parent_id = _stable_parent_id(
                        source=source,
                        section_path=str(section_path or ""),
                        start_char=int(start_char),
                        page=0,
                    )
                    enriched_docs.append(
                        Document(
                            page_content=section_text,
                            metadata={
                                **meta,
                                "section_path": section_path,
                                "section_start_line": int(start_line0 + 1),
                                "section_end_line": int(end_line0),
                                "section_start_char": int(start_char),
                                "parent_id": parent_id,
                            },
                        )
                    )
                continue

        enriched_docs.append(d)

    # 2) 切割
    if use_llm_chunking:
        chunks: list[Document] = []
        for doc in enriched_docs:
            chunks.extend(
                llm_semantic_split_document(doc, max_chunk_size=max_chunk_size, overlap=overlap)
            )
    else:
        base_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=overlap,
            add_start_index=True,
        )
        chunks = base_splitter.split_documents(enriched_docs)

    # 3) 元数据丰富
    _enrich_chunk_metadata(chunks)

    return chunks


# ---------------------------------------------------------------------------
# chunk 元数据丰富 (内部)
# ---------------------------------------------------------------------------

def _enrich_chunk_metadata(chunks: list[Document]) -> None:
    """为每个 chunk 补全 chunk_id / parent_id / line range 等元数据."""
    for i, c in enumerate(chunks):
        c.metadata = dict(c.metadata or {})

        source = str(c.metadata.get("source", ""))
        c.metadata.setdefault("file_type", "")
        c.metadata.setdefault("parent_id", "")

        start_index_raw = c.metadata.get("start_index", 0)
        try:
            start_index = int(start_index_raw)
        except Exception:
            start_index = 0

        section_start_char_raw = c.metadata.get("section_start_char")
        if section_start_char_raw is not None:
            try:
                section_start_char = int(section_start_char_raw)
                start_index = section_start_char + start_index
                c.metadata["start_index"] = int(start_index)
            except Exception:
                pass

        parent_id = str(c.metadata.get("parent_id") or "").strip()
        if not parent_id and source:
            page = int(c.metadata.get("page") or 0)
            parent_id = _stable_parent_id(
                source=source,
                section_path=str(c.metadata.get("section_path") or ""),
                start_char=0,
                page=page,
            )
            c.metadata["parent_id"] = parent_id

        material = f"{source}:{start_index}:{c.page_content}".encode("utf-8")
        digest = hashlib.sha1(material).hexdigest()[:12]

        c.metadata["chunk_index"] = i
        if source:
            c.metadata["chunk_id"] = f"{pathlib.Path(source).name}:{digest}"
        else:
            c.metadata["chunk_id"] = digest

        file_type = str(c.metadata.get("file_type", "")).lower().strip()
        if source.lower().endswith(".md") or file_type == "md":
            full_text = c.metadata.get("_source_text")
            if not isinstance(full_text, str):
                full_text = ""
            if full_text:
                start_line, end_line = _compute_line_range(
                    full_text=full_text,
                    start_index=start_index,
                    chunk_text=c.page_content or "",
                )
                c.metadata["start_line"] = int(start_line)
                c.metadata["end_line"] = int(end_line)

        c.metadata.setdefault("section_path", "")
        c.metadata.setdefault("start_line", 0)
        c.metadata.setdefault("end_line", 0)
        c.metadata.setdefault("page", 0)

        c.metadata.pop("_source_text", None)
        c.metadata.pop("section_start_char", None)
        c.metadata.pop("section_start_line", None)
        c.metadata.pop("section_end_line", None)

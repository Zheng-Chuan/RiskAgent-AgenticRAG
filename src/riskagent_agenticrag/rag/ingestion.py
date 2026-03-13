"""Ingestion module.

负责文档加载与切分。支持基于LLM的智能语义切割。
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from riskagent_agenticrag.config.settings import settings
from riskagent_agenticrag.llm.generate import call_llm_json_with_model

# LLM chunking configuration
LLM_CHUNKING_MODEL = "gpt-4o-mini"  # Model for document semantic chunking


def _compute_line_range(*, full_text: str, start_index: int, chunk_text: str) -> tuple[int, int]:
    prefix = full_text[: max(0, start_index)]
    start_line = prefix.count("\n") + 1
    end_index = max(0, start_index) + len(chunk_text)
    end_line = full_text[:end_index].count("\n") + 1
    return start_line, end_line


_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _markdown_sections(text: str) -> list[tuple[str, str, int, int, int]]:
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


def _llm_semantic_chunking(text: str, *, max_chunk_size: int = 800, overlap: int = 100) -> list[dict[str, Any]]:
    """使用LLM进行智能语义切割。

    使用 gpt-4o-mini 模型进行语义分析，成本低廉且效果良好。

    Args:
        text: 待切割的文本
        max_chunk_size: 每个chunk的最大字符数
        overlap: chunk之间的重叠字符数

    Returns:
        切割后的chunk列表，每个chunk包含text和metadata
    """
    if not text or len(text) <= max_chunk_size:
        return [{"text": text, "start": 0, "end": len(text), "reason": "short_text"}]

    prompt = f"""你是一个文档语义分析专家。请分析以下文本，找出最合适的语义切割点。

要求：
1. 每个chunk应该在{max_chunk_size}字符左右
2. 切割点必须选在语义边界处（如段落结束、主题转换、逻辑断点）
3. 避免在句子中间切割
4. 保留chunk之间的重叠约{overlap}字符以保证上下文连续性

请返回JSON格式：
{{
    "chunks": [
        {{
            "start": 0,
            "end": 500,
            "reason": "段落边界",
            "summary": "这段内容的主要主题"
        }}
    ],
    "total_chunks": 3
}}

其中start和end是字符位置（从0开始），reason说明为什么在这里切割。

待分析文本：
---
{text[:4000]}
---

如果文本超过4000字符，请优先分析前半部分并给出切割建议。"""

    try:
        response = call_llm_json_with_model(
            prompt,
            model=LLM_CHUNKING_MODEL,
            temperature=0.0,
            max_tokens=4096,
        )
        chunks_data = response.get("chunks", [])

        if not chunks_data:
            # Fallback to traditional splitting
            return _fallback_chunking(text, max_chunk_size=max_chunk_size, overlap=overlap)

        chunks: list[dict[str, Any]] = []
        for chunk_info in chunks_data:
            start = max(0, int(chunk_info.get("start", 0)))
            end = min(len(text), int(chunk_info.get("end", len(text))))
            chunk_text = text[start:end]

            if chunk_text.strip():
                chunks.append({
                    "text": chunk_text,
                    "start": start,
                    "end": end,
                    "reason": chunk_info.get("reason", "semantic_boundary"),
                    "summary": chunk_info.get("summary", ""),
                })

        return chunks if chunks else _fallback_chunking(text, max_chunk_size=max_chunk_size, overlap=overlap)

    except Exception:
        # Fallback to traditional splitting on any error
        return _fallback_chunking(text, max_chunk_size=max_chunk_size, overlap=overlap)


def _fallback_chunking(text: str, *, max_chunk_size: int = 800, overlap: int = 100) -> list[dict[str, Any]]:
    """传统字符切割作为fallback。"""
    chunks: list[dict[str, Any]] = []
    start = 0

    while start < len(text):
        end = min(start + max_chunk_size, len(text))

        # Try to find a better boundary
        if end < len(text):
            # Look for paragraph boundary
            next_para = text.find("\n\n", end - overlap, end + overlap)
            if next_para != -1:
                end = next_para + 2
            else:
                # Look for sentence boundary
                for sep in [". ", "。", "\n"]:
                    pos = text.rfind(sep, end - overlap, end + overlap)
                    if pos != -1:
                        end = pos + len(sep)
                        break

        chunk_text = text[start:end]
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "start": start,
                "end": end,
                "reason": "fallback_boundary",
                "summary": "",
            })

        start = max(start + 1, end - overlap)

    return chunks


def _llm_semantic_split_document(doc: Document, *, max_chunk_size: int = 800, overlap: int = 100) -> list[Document]:
    """对单个文档进行LLM语义切割。

    Args:
        doc: 输入文档
        max_chunk_size: 每个chunk的最大字符数
        overlap: chunk之间的重叠字符数

    Returns:
        切割后的Document列表
    """
    content = doc.page_content or ""
    if not content:
        return []

    meta = dict(doc.metadata or {})
    source = str(meta.get("source", ""))
    file_type = str(meta.get("file_type", "")).lower().strip()
    parent_id = str(meta.get("parent_id", "")).strip()
    section_path = str(meta.get("section_path", ""))

    # For very long texts, use a hybrid approach:
    # 1. First do coarse splitting into large blocks (to avoid too many LLM calls)
    # 2. Then use LLM for semantic refinement within each block

    if len(content) > 8000:
        # Coarse splitting first
        coarse_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            add_start_index=True,
        )
        coarse_chunks = coarse_splitter.split_documents([doc])

        result_docs: list[Document] = []
        for coarse_doc in coarse_chunks:
            coarse_text = coarse_doc.page_content or ""
            if not coarse_text:
                continue

            # Apply LLM semantic chunking to each coarse chunk
            semantic_chunks = _llm_semantic_chunking(
                coarse_text,
                max_chunk_size=max_chunk_size,
                overlap=overlap
            )

            for i, chunk_data in enumerate(semantic_chunks):
                chunk_text = chunk_data.get("text", "")
                if not chunk_text.strip():
                    continue

                # Calculate line numbers if we have full text
                start_index = chunk_data.get("start", 0)

                chunk_meta = {
                    **meta,
                    "chunking_method": "llm_semantic",
                    "parent_id": parent_id,
                    "section_path": section_path,
                    "chunk_reason": chunk_data.get("reason", ""),
                    "chunk_summary": chunk_data.get("summary", ""),
                    "start_index": start_index,
                }

                result_docs.append(Document(page_content=chunk_text, metadata=chunk_meta))

        return result_docs
    else:
        # For shorter texts, apply LLM chunking directly
        semantic_chunks = _llm_semantic_chunking(
            content,
            max_chunk_size=max_chunk_size,
            overlap=overlap
        )

        result_docs: list[Document] = []
        for chunk_data in semantic_chunks:
            chunk_text = chunk_data.get("text", "")
            if not chunk_text.strip():
                continue

            start_index = chunk_data.get("start", 0)

            chunk_meta = {
                **meta,
                "chunking_method": "llm_semantic",
                "parent_id": parent_id,
                "section_path": section_path,
                "chunk_reason": chunk_data.get("reason", ""),
                "chunk_summary": chunk_data.get("summary", ""),
                "start_index": start_index,
            }

            result_docs.append(Document(page_content=chunk_text, metadata=chunk_meta))

        return result_docs


def build_parent_documents(docs: list[Document]) -> list[Document]:
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


def split_documents(
    docs: list[Document],
    *,
    use_llm_chunking: bool = True,
    max_chunk_size: int = 800,
    overlap: int = 100,
) -> list[Document]:
    """将原始文档切分为chunks。

    支持基于LLM的智能语义切割和传统字符切割两种模式。

    Args:
        docs: 原始文档列表。
        use_llm_chunking: 是否使用LLM语义切割（默认True）
        max_chunk_size: 每个chunk的最大字符数
        overlap: chunk之间的重叠字符数

    Returns:
        切分后的 chunks 列表。
    """
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

    # Apply chunking
    if use_llm_chunking:
        # Use LLM semantic chunking
        chunks: list[Document] = []
        for doc in enriched_docs:
            semantic_chunks = _llm_semantic_split_document(
                doc,
                max_chunk_size=max_chunk_size,
                overlap=overlap
            )
            chunks.extend(semantic_chunks)
    else:
        # Use traditional character-based splitting
        base_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=overlap,
            add_start_index=True,
        )
        chunks = base_splitter.split_documents(enriched_docs)

    # Enrich chunk metadata
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
                page=page
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
                    chunk_text=c.page_content or ""
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

    return chunks

"""文档切割 -- LLM 语义切割 + 传统字符切割 fallback."""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from riskagent_agenticrag.llm.generate import call_llm_json_with_model

# LLM chunking 使用的模型
LLM_CHUNKING_MODEL = "gpt-4o-mini"


# ---------------------------------------------------------------------------
# LLM 语义切割
# ---------------------------------------------------------------------------

def _llm_semantic_chunking(text: str, *, max_chunk_size: int = 800, overlap: int = 100) -> list[dict[str, Any]]:
    """使用 LLM 进行智能语义切割.

    Args:
        text: 待切割的文本
        max_chunk_size: 每个 chunk 的最大字符数
        overlap: chunk 之间的重叠字符数

    Returns:
        切割后的 chunk 列表, 每个 chunk 包含 text / start / end / reason / summary
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
        return _fallback_chunking(text, max_chunk_size=max_chunk_size, overlap=overlap)


# ---------------------------------------------------------------------------
# 传统字符切割 (fallback)
# ---------------------------------------------------------------------------

def _fallback_chunking(text: str, *, max_chunk_size: int = 800, overlap: int = 100) -> list[dict[str, Any]]:
    """传统字符切割作为 fallback."""
    chunks: list[dict[str, Any]] = []
    start = 0

    while start < len(text):
        end = min(start + max_chunk_size, len(text))

        if end < len(text):
            next_para = text.find("\n\n", end - overlap, end + overlap)
            if next_para != -1:
                end = next_para + 2
            else:
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


# ---------------------------------------------------------------------------
# 对单个 Document 进行 LLM 语义切割
# ---------------------------------------------------------------------------

def _build_chunk_doc(
    chunk_data: dict[str, Any],
    meta: dict[str, Any],
    parent_id: str,
    section_path: str,
) -> Document | None:
    """从 chunk_data 构建 Document, 返回 None 表示跳过空 chunk."""
    chunk_text = chunk_data.get("text", "")
    if not chunk_text.strip():
        return None
    chunk_meta = {
        **meta,
        "chunking_method": "llm_semantic",
        "parent_id": parent_id,
        "section_path": section_path,
        "chunk_reason": chunk_data.get("reason", ""),
        "chunk_summary": chunk_data.get("summary", ""),
        "start_index": chunk_data.get("start", 0),
    }
    return Document(page_content=chunk_text, metadata=chunk_meta)


def llm_semantic_split_document(
    doc: Document,
    *,
    max_chunk_size: int = 800,
    overlap: int = 100,
) -> list[Document]:
    """对单个文档进行 LLM 语义切割.

    Args:
        doc: 输入文档
        max_chunk_size: 每个 chunk 的最大字符数
        overlap: chunk 之间的重叠字符数

    Returns:
        切割后的 Document 列表
    """
    content = doc.page_content or ""
    if not content:
        return []

    meta = dict(doc.metadata or {})
    parent_id = str(meta.get("parent_id", "")).strip()
    section_path = str(meta.get("section_path", ""))

    # 长文本: 先粗切再 LLM 精切
    if len(content) > 8000:
        coarse_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            add_start_index=True,
        )
        coarse_chunks = coarse_splitter.split_documents([doc])

        result_docs: list[Document] = []
        for coarse_doc in coarse_chunks:
            if not (coarse_doc.page_content or ""):
                continue
            for cd in _llm_semantic_chunking(coarse_doc.page_content, max_chunk_size=max_chunk_size, overlap=overlap):
                d = _build_chunk_doc(cd, meta, parent_id, section_path)
                if d:
                    result_docs.append(d)
        return result_docs

    # 短文本: 直接 LLM 切割
    result_docs = []
    for cd in _llm_semantic_chunking(content, max_chunk_size=max_chunk_size, overlap=overlap):
        d = _build_chunk_doc(cd, meta, parent_id, section_path)
        if d:
            result_docs.append(d)
    return result_docs

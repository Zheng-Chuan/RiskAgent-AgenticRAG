"""RAG pipeline.

这个模块提供对外稳定的数据结构化输出
目前保留 citations 提取作为对外 contract
"""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document

def extract_citations(docs: list[Document]) -> list[dict[str, Any]]:
    # citations 是一个最小可展示结构.
    # UI 会将其渲染为 markdown 列表.
    # 技术难点: citations 字段一旦对外展示, 就会变成对外 contract.
    # 业务不清晰点: 什么算有效 citations.
    # - 只要能定位 source + chunk_id 就算, 还是要包含 section path, page, score.
    # - 未来还需要定义引用覆盖率, 作为 Week 2 的核心指标.
    citations: list[dict[str, Any]] = []
    for d in docs:
        meta = d.metadata or {}
        item: dict[str, Any] = {
            "source": str(meta.get("source", "")),
            "chunk_id": str(meta.get("chunk_id", "")),
        }
        if "start_index" in meta:
            try:
                item["start_index"] = int(meta.get("start_index"))
            except Exception:
                pass
        if meta.get("section_path"):
            item["section_path"] = str(meta.get("section_path"))
        if meta.get("page"):
            try:
                item["page"] = int(meta.get("page"))
            except Exception:
                pass
        if meta.get("start_line") is not None:
            try:
                item["start_line"] = int(meta.get("start_line"))
            except Exception:
                pass
        if meta.get("end_line") is not None:
            try:
                item["end_line"] = int(meta.get("end_line"))
            except Exception:
                pass
        expanded = str(meta.get("expanded_text") or "").strip()
        raw_text = expanded or str(getattr(d, "page_content", "") or "").strip()
        if raw_text:
            item["snippet"] = raw_text[:300]
        citations.append(item)
    return citations

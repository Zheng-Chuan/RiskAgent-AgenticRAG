"""RAG pipeline.

这个模块把 ingest 和 retrieval 相关步骤串起来, 给 UI 或 CLI 调用.

最小链路.
- build_index: 读取 docs/sources 下的 markdown, 切分 chunks, 写入 Chroma 持久化目录.
- load_index: 从 Chroma 持久化目录恢复向量库.
- extract_citations: 将检索到的 Document 元数据转成可展示的 citations 结构.

注意.
- citations 目前只包含 source 和 chunk_id, 后续可以扩展为 page, section, score 等.
"""

from __future__ import annotations

import pathlib

from langchain_core.documents import Document

from riskagent_rag.rag.chroma_index import (
    build_chroma_vectorstore,
    load_chroma_vectorstore,
    split_documents,
)
from riskagent_rag.rag.source_loader import load_markdown_sources


class IndexBuildResult:
    def __init__(self, source_count: int, chunk_count: int, persist_dir: pathlib.Path):
        # build_index 的结果对象, 方便在 UI 里展示统计信息.
        self.source_count = source_count
        self.chunk_count = chunk_count
        self.persist_dir = persist_dir


def build_index(sources_dir: pathlib.Path, persist_dir: pathlib.Path) -> IndexBuildResult:
    # 从 sources_dir 加载 markdown, 切分为 chunks, 并写入 Chroma.
    # 返回 source_count 和 chunk_count 便于可观测.
    sources = load_markdown_sources(sources_dir)
    chunks = split_documents(sources)
    build_chroma_vectorstore(chunks, persist_dir)
    return IndexBuildResult(source_count=len(sources), chunk_count=len(chunks), persist_dir=persist_dir)


def load_index(persist_dir: pathlib.Path):
    # 加载已有 Chroma 向量库.
    return load_chroma_vectorstore(persist_dir)


def extract_citations(docs: list[Document]) -> list[dict[str, str]]:
    # citations 是一个最小可展示结构.
    # UI 会将其渲染为 markdown 列表.
    citations: list[dict[str, str]] = []
    for d in docs:
        meta = d.metadata or {}
        citations.append(
            {
                "source": str(meta.get("source", "")),
                "chunk_id": str(meta.get("chunk_id", "")),
            }
        )
    return citations

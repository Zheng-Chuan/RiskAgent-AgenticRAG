"""Ingestion module.

负责文档加载与切分。
"""
from __future__ import annotations

import hashlib
import pathlib

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(docs: list[Document]) -> list[Document]:
    """将原始文档切分为固定大小 chunks。

    Args:
        docs: 原始文档列表。

    Returns:
        切分后的 chunks 列表。
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=120,
        add_start_index=True,
    )
    chunks = splitter.split_documents(docs)

    for i, c in enumerate(chunks):
        # 为每个 chunk 写入 chunk_id, 便于 citations 展示.
        c.metadata = dict(c.metadata or {})

        source = str(c.metadata.get("source", ""))
        start = str(c.metadata.get("start_index", ""))
        material = f"{source}:{start}:{c.page_content}".encode("utf-8")
        digest = hashlib.sha1(material).hexdigest()[:12]

        c.metadata["chunk_index"] = i
        if source:
            c.metadata["chunk_id"] = f"{pathlib.Path(source).name}:{digest}"
        else:
            c.metadata["chunk_id"] = digest

    return chunks

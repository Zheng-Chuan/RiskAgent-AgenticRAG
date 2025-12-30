"""Chroma 索引相关.

该模块负责两件事.
1. 将 Document 列表切分为 chunk 级别的 Document.
2. 使用 embeddings + Chroma 构建或加载本地持久化向量库.

MVP 设计选择.
- embeddings 默认用 FakeEmbeddings, 目的是离线可运行, 不依赖外部模型或 API key.
- 这会影响检索质量, 但能保证链路可跑通.
- 后续可替换为真实 embeddings, 例如 OpenAI embeddings 或本地模型 embeddings.
"""

from __future__ import annotations

import pathlib

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(docs: list[Document]) -> list[Document]:
    # 将原始文档切分为固定大小 chunks.
    # chunk_size 和 chunk_overlap 是经验值, MVP 阶段先保证稳定.
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    chunks = splitter.split_documents(docs)

    for i, c in enumerate(chunks):
        # 为每个 chunk 写入 chunk_id, 便于 citations 展示.
        c.metadata = dict(c.metadata or {})
        c.metadata["chunk_id"] = i

    return chunks


def build_chroma_vectorstore(chunks: list[Document], persist_dir: pathlib.Path):
    # 构建 Chroma 向量库并落地到 persist_dir.
    # 这里使用 LangChain 的 community 版本 Chroma wrapper.
    from langchain_community.embeddings import FakeEmbeddings
    from langchain_community.vectorstores import Chroma

    # 确保目录存在, Chroma 会在该目录写入 sqlite 和索引文件.
    persist_dir.mkdir(parents=True, exist_ok=True)

    # FakeEmbeddings 是一个可离线运行的 embeddings 实现.
    # 仅用于 MVP 跑通链路. 真实环境请替换.
    embeddings = FakeEmbeddings(size=384)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(persist_dir),
    )

    return vectorstore


def load_chroma_vectorstore(persist_dir: pathlib.Path):
    # 从 persist_dir 加载已有向量库.
    # 注意: 必须使用和 build 时相同维度的 embeddings, 否则检索会报错或结果异常.
    from langchain_community.embeddings import FakeEmbeddings
    from langchain_community.vectorstores import Chroma

    embeddings = FakeEmbeddings(size=384)

    return Chroma(
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

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

import hashlib
import pathlib
import os
import importlib

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(docs: list[Document]) -> list[Document]:
    # 将原始文档切分为固定大小 chunks.
    # chunk_size 和 chunk_overlap 是经验值, MVP 阶段先保证稳定.
    # 技术难点: chunk 粒度会直接影响.
    # - 检索命中率(recall)
    # - 引用可读性(citations 是否能定位到合适片段)
    # Week 2 会基于真实语料调整切分策略, 例如按标题层级优先.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=120,
        add_start_index=True,
    )
    chunks = splitter.split_documents(docs)

    for i, c in enumerate(chunks):
        # 为每个 chunk 写入 chunk_id, 便于 citations 展示.
        # 技术难点: metadata schema 一旦对外展示, 后续变更要考虑兼容.
        # 业务不清晰点: 未来 citations 可能需要 section_path, page, score 等字段.
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


def _build_embeddings():
    # Week 2 选择真实 embeddings 的原因
    # 1. citations coverage 的硬指标依赖 retrieval 质量
    # 2. embeddings 模型与维度必须锁定, 否则 rebuild index 会出现 silent wrong results
    # 3. 先用本地 sentence-transformers, 保证可控与可复现
    model_name = os.getenv(
        "EMBEDDINGS_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )
    provider = os.getenv("EMBEDDINGS_PROVIDER", "hf")
    provider = provider.lower().strip()
    if provider in {"fake", "offline"}:
        from langchain_community.embeddings import FakeEmbeddings

        # FakeEmbeddings 仅用于离线调试, 不建议用于 Week 2 评测
        return FakeEmbeddings(size=384)

    try:
        mod = importlib.import_module("langchain_huggingface")
        HuggingFaceEmbeddings = getattr(mod, "HuggingFaceEmbeddings")
    except Exception:
        from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=model_name)


def build_chroma_vectorstore(
    chunks: list[Document],
    persist_dir: pathlib.Path,
):
    # 构建 Chroma 向量库并落地到 persist_dir.
    # 这里使用 LangChain 的 community 版本 Chroma wrapper.
    from langchain_community.vectorstores import Chroma

    # 确保目录存在, Chroma 会在该目录写入 sqlite 和索引文件.
    persist_dir.mkdir(parents=True, exist_ok=True)

    # FakeEmbeddings 是一个可离线运行的 embeddings 实现.
    # 技术难点: 它只保证链路可跑, 不保证检索质量.
    # Week 2 需要切换到真实 embeddings.
    # 例如 OpenAI compatible embeddings 或本地 embeddings.
    embeddings = _build_embeddings()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(persist_dir),
    )

    return vectorstore


def load_chroma_vectorstore(persist_dir: pathlib.Path):
    # 从 persist_dir 加载已有向量库.
    # 注意: 必须使用和 build 时相同维度的 embeddings, 否则检索会报错或结果异常.
    # 技术难点: 这类问题通常表现为.
    # - 线上报错
    # - 或者 silent wrong results(检索结果异常但不报错)
    from langchain_community.vectorstores import Chroma

    embeddings = _build_embeddings()

    return Chroma(
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

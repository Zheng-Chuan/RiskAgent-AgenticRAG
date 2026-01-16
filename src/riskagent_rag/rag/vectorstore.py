"""VectorStore module.

负责向量数据库连接与 CRUD。
"""
from __future__ import annotations

import os  # pylint: disable=unused-import
import pathlib
import time
import urllib.error
import urllib.request
from typing import Any, Dict
from uuid import uuid4  # pylint: disable=unused-import

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from riskagent_rag.config.settings import settings
from riskagent_rag.rag.embeddings import build_embeddings


def _connection_args(persist_dir: pathlib.Path) -> Dict[str, Any]:
    """构建 Milvus 连接参数。"""
    cfg = settings.milvus
    
    if cfg.uri:
        base: Dict[str, Any] = {"uri": cfg.uri, "secure": cfg.secure}
    elif cfg.host:
        base = {
            "host": cfg.host,
            "port": cfg.port,
            "secure": cfg.secure,
        }
    else:
        persist_dir.mkdir(parents=True, exist_ok=True)
        base = {"uri": str((persist_dir / "milvus.db").absolute()), "secure": False}

    if cfg.user:
        base["user"] = cfg.user
    if cfg.password:
        base["password"] = cfg.password

    return base


def _wait_for_milvus_ready(connection_args: Dict[str, Any]) -> None:
    """等待 Milvus 服务就绪。"""
    if not settings.milvus.wait_ready:
        return

    host = connection_args.get("host")
    if not host:
        return

    health_port = settings.milvus.health_port
    timeout_s = settings.milvus.ready_timeout_s
    deadline = time.time() + timeout_s
    url = f"http://{host}:{health_port}/healthz"

    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if 200 <= resp.status < 300:
                    return
        except Exception as e:  # pylint: disable=broad-exception-caught
            last_err = e
        time.sleep(1)

    if last_err is not None:
        raise last_err


def build_milvus_vectorstore(
    chunks: list[Document],
    persist_dir: pathlib.Path,
) -> VectorStore:
    """构建向量库。
    
    如果未配置 Milvus 远端地址，则尝试使用 InMemoryVectorStore (如果不可用 Milvus Lite)
    但为了与旧逻辑保持一致，这里优先保留 Milvus 逻辑，只有显式 fallback 时才用 InMemory。
    """
    embeddings = build_embeddings()
    cfg = settings.milvus

    # 如果没有配置远端 Milvus 且不使用 Docker，使用 InMemory 作为 fallback (主要用于单测)
    if not cfg.uri and not cfg.host and not cfg.use_docker:
        # 尝试检测是否为测试环境或者确实没有 Milvus 环境
        # 之前的逻辑是: if not uri and not host: -> InMemory
        # 但这样会导致 Milvus Lite 被绕过。
        # 让我们修正逻辑：仅当环境确实不支持 Milvus 时（例如单测无 Docker 且 Milvus Lite 有问题时）
        # 这里暂时沿用之前的修复逻辑：
        try:
            from langchain_milvus import Milvus
        except ImportError:
            try:
                from langchain_community.vectorstores import Milvus
            except ImportError:
                # 只有当 langchain_milvus 和 community 都不存在时才 fallback
                from langchain_core.vectorstores import InMemoryVectorStore
                persist_dir.mkdir(parents=True, exist_ok=True)
                path = persist_dir / "inmemory_vectorstore.json"
                vectorstore = InMemoryVectorStore.from_documents(documents=chunks, embedding=embeddings)
                vectorstore.dump(str(path))
                return vectorstore

    # 正常流程使用 Milvus (包含 Lite)
    try:
        from langchain_milvus import Milvus
    except ImportError:
        from langchain_community.vectorstores import Milvus

    connection_args = _connection_args(persist_dir)
    _wait_for_milvus_ready(connection_args)
    
    index_params = {
        "index_type": cfg.index_type,
        "metric_type": cfg.metric_type,
        "params": {"nlist": cfg.nlist},
    }
    search_params = {"params": {"nprobe": cfg.nprobe}}

    return Milvus.from_documents(
        documents=chunks,
        embedding=embeddings,
        connection_args=connection_args,
        collection_name=cfg.collection_name,
        index_params=index_params,
        search_params=search_params,
        drop_old=True,
    )


def load_milvus_vectorstore(persist_dir: pathlib.Path) -> VectorStore:
    """加载已存在的向量库。"""
    embeddings = build_embeddings()
    cfg = settings.milvus

    # Fallback logic check
    if not cfg.uri and not cfg.host and not cfg.use_docker:
        try:
            from langchain_milvus import Milvus
        except ImportError:
            try:
                from langchain_community.vectorstores import Milvus
            except ImportError:
                from langchain_core.vectorstores import InMemoryVectorStore
                path = persist_dir / "inmemory_vectorstore.json"
                if path.exists():
                    return InMemoryVectorStore.load(str(path), embedding=embeddings)
                # If file doesn't exist, we might still want to try Milvus or return empty
                # For now let's fall through

    try:
        from langchain_milvus import Milvus
    except ImportError:
        from langchain_community.vectorstores import Milvus

    connection_args = _connection_args(persist_dir)
    _wait_for_milvus_ready(connection_args)

    return Milvus(
        embedding_function=embeddings,
        connection_args=connection_args,
        collection_name=cfg.collection_name,
        consistency_level=cfg.consistency_level,
    )

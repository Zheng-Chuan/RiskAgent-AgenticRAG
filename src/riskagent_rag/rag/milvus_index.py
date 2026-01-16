"""Milvus 索引相关.

职责:
1. 文档切分为 chunk 级 Document.
2. 使用 embeddings + Milvus 构建或加载向量库.

设计取舍:
- 默认支持 Milvus Lite(本地文件 uri) 便于离线可复现, 同时可通过环境变量切换到远端 Milvus/Qdrant 兼容部署.
- embeddings 默认使用真实 HuggingFace 模型, 通过环境变量调整模型名称.
"""

from __future__ import annotations

import hashlib
import importlib
import os
import pathlib
import time
import urllib.error
import urllib.request
from typing import Any, Dict

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(docs: list[Document]) -> list[Document]:
    # 将原始文档切分为固定大小 chunks.
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


def _ensure_project_hf_cache_env() -> None:
    # 中文注释: 将 HuggingFace 缓存固定到项目目录, 便于预下载与可复现.
    project_root = pathlib.Path(__file__).resolve().parents[3]
    base = project_root / "models" / "hf"
    base.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(base))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(base / "hub"))
    os.environ.setdefault("HF_HUB_CACHE", str(base / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(base / "transformers"))
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(base / "sentence_transformers"))


def _local_embeddings_dir_for_model(model_name: str) -> pathlib.Path:
    # 中文注释: 将模型名映射为稳定目录名 便于提交到仓库
    project_root = pathlib.Path(__file__).resolve().parents[3]
    safe = model_name.replace("/", "__")
    return project_root / "models" / "embeddings" / safe


def _build_embeddings():
    model_name = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    _ensure_project_hf_cache_env()

    local_dir = _local_embeddings_dir_for_model(model_name)
    resolved_model = str(local_dir) if local_dir.exists() else model_name
    try:
        mod = importlib.import_module("langchain_huggingface")
        HuggingFaceEmbeddings = getattr(mod, "HuggingFaceEmbeddings")
    except Exception:
        from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=resolved_model)


def preload_embeddings_model() -> dict[str, str]:
    # 中文注释: 预下载 embeddings 模型到项目目录
    # 返回值用于在 CLI 打印路径与模型信息
    model_name = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    _ensure_project_hf_cache_env()

    embeddings = _build_embeddings()
    try:
        embeddings.embed_query("warmup")
    except Exception:
        # 中文注释: 某些 embeddings 实现可能不支持 embed_query
        pass

    project_root = pathlib.Path(__file__).resolve().parents[3]
    cache_dir = project_root / "models" / "hf"
    return {
        "model": model_name,
        "hf_home": str(cache_dir),
    }


def export_embeddings_model_to_repo_dir() -> dict[str, str]:
    # 中文注释: 将 HF 模型导出为稳定目录结构 用于提交到仓库
    # 依赖 sentence_transformers
    model_name = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    _ensure_project_hf_cache_env()

    target_dir = _local_embeddings_dir_for_model(model_name)
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise e

    model = SentenceTransformer(model_name)
    model.save(str(target_dir))

    return {
        "model": model_name,
        "export_dir": str(target_dir),
    }


def _connection_args(persist_dir: pathlib.Path) -> Dict[str, Any]:
    # 连接参数优先读取环境变量, 无则回退 Milvus Lite 单文件模式.
    uri = os.getenv("MILVUS_URI")
    host = os.getenv("MILVUS_HOST")
    port = int(os.getenv("MILVUS_PORT", "19530"))

    secure = os.getenv("MILVUS_SECURE", "").lower().strip() in {"true", "1", "yes"}

    if uri:
        base: Dict[str, Any] = {"uri": uri, "secure": secure}
    elif host:
        base = {
            "host": host,
            "port": port,
            "secure": secure,
        }
    else:
        persist_dir.mkdir(parents=True, exist_ok=True)
        base = {"uri": str((persist_dir / "milvus.db").absolute()), "secure": False}

    user = os.getenv("MILVUS_USER")
    password = os.getenv("MILVUS_PASSWORD")
    if user:
        base["user"] = user
    if password:
        base["password"] = password

    return base


def _wait_for_milvus_ready(connection_args: Dict[str, Any]) -> None:
    wait_enabled = os.getenv("MILVUS_WAIT_READY", "true").lower().strip() in {
        "true",
        "1",
        "yes",
    }
    if not wait_enabled:
        return

    host = connection_args.get("host")
    if not host:
        return

    health_port = int(os.getenv("MILVUS_HEALTH_PORT", "9091"))
    timeout_s = float(os.getenv("MILVUS_READY_TIMEOUT_S", "120"))
    deadline = time.time() + timeout_s
    url = f"http://{host}:{health_port}/healthz"

    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if 200 <= resp.status < 300:
                    return
        except Exception as e:
            last_err = e
        time.sleep(1)

    if last_err is not None:
        raise last_err


def build_milvus_vectorstore(
    chunks: list[Document],
    persist_dir: pathlib.Path,
):
    embeddings = _build_embeddings()

    uri = os.getenv("MILVUS_URI")
    host = os.getenv("MILVUS_HOST")

    if not uri and not host:
        from langchain_core.vectorstores import InMemoryVectorStore

        persist_dir.mkdir(parents=True, exist_ok=True)
        path = persist_dir / "inmemory_vectorstore.json"
        vectorstore = InMemoryVectorStore.from_documents(documents=chunks, embedding=embeddings)
        vectorstore.dump(str(path))
        return vectorstore

    try:
        from langchain_milvus import Milvus
    except Exception:
        from langchain_community.vectorstores import Milvus

    connection_args = _connection_args(persist_dir)
    _wait_for_milvus_ready(connection_args)
    collection_name = os.getenv("MILVUS_COLLECTION", "riskagent_rag")
    index_params = {
        "index_type": os.getenv("MILVUS_INDEX_TYPE", "IVF_FLAT"),
        "metric_type": os.getenv("MILVUS_METRIC", "L2"),
        "params": {"nlist": int(os.getenv("MILVUS_NLIST", "128"))},
    }
    search_params = {"params": {"nprobe": int(os.getenv("MILVUS_NPROBE", "16"))}}

    return Milvus.from_documents(
        documents=chunks,
        embedding=embeddings,
        connection_args=connection_args,
        collection_name=collection_name,
        index_params=index_params,
        search_params=search_params,
        drop_old=True,
    )


def load_milvus_vectorstore(persist_dir: pathlib.Path):
    # 加载已存在的 Milvus 向量库.
    embeddings = _build_embeddings()

    uri = os.getenv("MILVUS_URI")
    host = os.getenv("MILVUS_HOST")

    if not uri and not host:
        from langchain_core.vectorstores import InMemoryVectorStore

        path = persist_dir / "inmemory_vectorstore.json"
        return InMemoryVectorStore.load(str(path), embedding=embeddings)

    try:
        from langchain_milvus import Milvus
    except Exception:
        from langchain_community.vectorstores import Milvus

    connection_args = _connection_args(persist_dir)
    _wait_for_milvus_ready(connection_args)
    collection_name = os.getenv("MILVUS_COLLECTION", "riskagent_rag")

    return Milvus(
        embedding_function=embeddings,
        connection_args=connection_args,
        collection_name=collection_name,
        consistency_level=os.getenv("MILVUS_CONSISTENCY", "Session"),
    )

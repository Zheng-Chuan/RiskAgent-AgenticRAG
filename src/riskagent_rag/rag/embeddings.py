"""Embeddings module.

负责 Embedding 模型的加载与缓存。
"""
from __future__ import annotations

import importlib
import os
import pathlib
from typing import Any  # pylint: disable=unused-import

from langchain_core.embeddings import Embeddings

from riskagent_rag.config.settings import settings


def _ensure_project_hf_cache_env() -> None:
    """将 HuggingFace 缓存固定到项目目录, 便于预下载与可复现。"""
    base = settings.paths.hf_cache_dir
    base.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(base))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(base / "hub"))
    os.environ.setdefault("HF_HUB_CACHE", str(base / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(base / "transformers"))
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(base / "sentence_transformers"))


def _local_embeddings_dir_for_model(model_name: str) -> pathlib.Path:
    """将模型名映射为稳定目录名 便于提交到仓库"""
    safe = model_name.replace("/", "__")
    return settings.paths.models_dir / "embeddings" / safe


def build_embeddings() -> Embeddings:
    """构建 Embeddings 实例。"""
    model_name = settings.embeddings.model_name
    _ensure_project_hf_cache_env()

    local_dir = _local_embeddings_dir_for_model(model_name)
    resolved_model = str(local_dir) if local_dir.exists() else model_name

    try:
        mod = importlib.import_module("langchain_huggingface")
        HuggingFaceEmbeddings = getattr(mod, "HuggingFaceEmbeddings")
    except Exception:  # pylint: disable=broad-exception-caught
        from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=resolved_model)


def preload_embeddings_model() -> dict[str, str]:
    """预下载 embeddings 模型到项目目录。
    
    Returns:
        包含模型名和缓存路径的字典。
    """
    model_name = settings.embeddings.model_name
    _ensure_project_hf_cache_env()

    embeddings = build_embeddings()
    try:
        embeddings.embed_query("warmup")
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    return {
        "model": model_name,
        "hf_home": str(settings.paths.hf_cache_dir),
    }


def export_embeddings_model_to_repo_dir() -> dict[str, str]:
    """将 HF 模型导出为稳定目录结构 用于提交到仓库。
    
    Returns:
        包含模型名和导出路径的字典。
    """
    model_name = settings.embeddings.model_name
    _ensure_project_hf_cache_env()

    target_dir = _local_embeddings_dir_for_model(model_name)
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError("Export requires sentence_transformers installed") from e

    model = SentenceTransformer(model_name)
    model.save(str(target_dir))

    return {
        "model": model_name,
        "export_dir": str(target_dir),
    }

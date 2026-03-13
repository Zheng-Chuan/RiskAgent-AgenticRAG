"""Embeddings -- Embedding 模型加载与缓存."""

from __future__ import annotations

import importlib
import os
import pathlib
import warnings

from langchain_core.embeddings import Embeddings

from riskagent_agenticrag.config.settings import settings

# 强制离线模式, 避免 HuggingFace 网络请求
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""


def _ensure_project_hf_cache_env() -> None:
    """将 HuggingFace 缓存固定到项目目录, 便于预下载与可复现."""
    base = settings.paths.hf_cache_dir
    base.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(base))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(base / "hub"))
    os.environ.setdefault("HF_HUB_CACHE", str(base / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(base / "transformers"))
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(base / "sentence_transformers"))


def _local_embeddings_dir(model_name: str) -> pathlib.Path:
    """将模型名映射为稳定目录名, 便于提交到仓库."""
    safe = model_name.replace("/", "__")
    return settings.paths.models_dir / "embeddings" / safe


def build_embeddings() -> Embeddings:
    """构建 HuggingFace Embeddings 实例.

    优先使用 langchain_huggingface, 回退到 langchain_community.
    导入时抑制 langchain_core.pydantic_v1 弃用警告.
    """
    model_name = settings.embeddings.model_name
    _ensure_project_hf_cache_env()

    provider = str(settings.embeddings.provider or "hf").lower().strip()
    if provider != "hf":
        raise RuntimeError(f"Unsupported embeddings provider: {provider}")

    local_dir = _local_embeddings_dir(model_name)
    resolved_model = str(local_dir) if local_dir.exists() else model_name

    # langchain_huggingface 内部会触发 pydantic_v1 弃用警告, 这里统一抑制
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*pydantic_v1.*")
        warnings.filterwarnings("ignore", message=".*class-validator.*")
        warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*")
        try:
            mod = importlib.import_module("langchain_huggingface")
            HFEmbeddings = getattr(mod, "HuggingFaceEmbeddings")
        except Exception:
            from langchain_community.embeddings import HuggingFaceEmbeddings as HFEmbeddings

        return HFEmbeddings(
            model_name=resolved_model,
            model_kwargs={"local_files_only": True, "trust_remote_code": True},
        )


def preload_embeddings_model() -> dict[str, str]:
    """预下载 embeddings 模型到项目目录, 返回模型名与缓存路径."""
    model_name = settings.embeddings.model_name
    _ensure_project_hf_cache_env()
    try:
        build_embeddings().embed_query("warmup")
    except Exception:
        pass
    return {"model": model_name, "hf_home": str(settings.paths.hf_cache_dir)}


def export_embeddings_model_to_repo_dir() -> dict[str, str]:
    """将 HF 模型导出为稳定目录结构, 用于提交到仓库."""
    model_name = settings.embeddings.model_name
    _ensure_project_hf_cache_env()
    target_dir = _local_embeddings_dir(model_name)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError("Export requires sentence_transformers installed") from e
    SentenceTransformer(model_name).save(str(target_dir))
    return {"model": model_name, "export_dir": str(target_dir)}


from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass, field


@dataclass
class MilvusConfig:
    """Milvus 向量数据库配置"""
    uri: str | None = None
    host: str | None = None
    port: int = 19530
    user: str | None = None
    password: str | None = None
    secure: bool = False
    collection_name: str = "riskagent_agenticrag"
    index_type: str = "IVF_FLAT"
    metric_type: str = "L2"
    nlist: int = 128
    nprobe: int = 16
    wait_ready: bool = True
    health_port: int = 9091
    ready_timeout_s: float = 120.0
    consistency_level: str = "Session"
    use_docker: bool = False  # 如果为 True，强制使用 Docker 模式而不是 Lite

    @classmethod
    def from_env(cls) -> MilvusConfig:
        return cls(
            uri=os.getenv("MILVUS_URI"),
            host=os.getenv("MILVUS_HOST"),
            port=int(os.getenv("MILVUS_PORT", "19530")),
            user=os.getenv("MILVUS_USER"),
            password=os.getenv("MILVUS_PASSWORD"),
            secure=os.getenv("MILVUS_SECURE", "").lower().strip() in {"true", "1", "yes"},
            collection_name=os.getenv("MILVUS_COLLECTION", "riskagent_rag"),
            index_type=os.getenv("MILVUS_INDEX_TYPE", "IVF_FLAT"),
            metric_type=os.getenv("MILVUS_METRIC", "L2"),
            nlist=int(os.getenv("MILVUS_NLIST", "128")),
            nprobe=int(os.getenv("MILVUS_NPROBE", "16")),
            wait_ready=os.getenv("MILVUS_WAIT_READY", "true").lower().strip() in {"true", "1", "yes"},
            health_port=int(os.getenv("MILVUS_HEALTH_PORT", "9091")),
            ready_timeout_s=float(os.getenv("MILVUS_READY_TIMEOUT_S", "120")),
            consistency_level=os.getenv("MILVUS_CONSISTENCY", "Session"),
            use_docker=os.getenv("RISKAGENT_USE_DOCKER_MILVUS", "").lower().strip() in {"true", "1", "yes"},
        )


@dataclass
class EmbeddingsConfig:
    """Embedding 模型配置"""
    provider: str = "hf"  # hf, openai, etc.
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    @classmethod
    def from_env(cls) -> EmbeddingsConfig:
        return cls(
            provider=os.getenv("EMBEDDINGS_PROVIDER", "hf"),
            model_name=os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        )


@dataclass
class LLMConfig:
    """LLM 服务配置"""
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    provider: str = "openai_compatible"  # openai, ollama, vllm, etc.

    @classmethod
    def from_env(cls) -> LLMConfig:
        return cls(
            api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            model=os.getenv("LLM_MODEL"),
            provider=os.getenv("LLM_PROVIDER", "openai_compatible"),
        )


@dataclass
class PathConfig:
    """项目路径配置"""
    project_root: pathlib.Path = field(default_factory=lambda: pathlib.Path(__file__).resolve().parents[3])
    
    @property
    def corpus_dir(self) -> pathlib.Path:
        return self.project_root / "corpus"
    
    @property
    def milvus_lite_dir(self) -> pathlib.Path:
        return self.project_root / ".milvus"
    
    @property
    def models_dir(self) -> pathlib.Path:
        return self.project_root / "models"
    
    @property
    def hf_cache_dir(self) -> pathlib.Path:
        return self.models_dir / "hf"


@dataclass
class FeatureConfig:
    """功能开关配置"""
    use_langgraph: bool = False
    
    @classmethod
    def from_env(cls) -> FeatureConfig:
        return cls(
            use_langgraph=os.getenv("USE_LANGGRAPH", "").lower().strip() in {"true", "1", "yes"}
        )


@dataclass
class Settings:
    """全局配置聚合类"""
    milvus: MilvusConfig = field(default_factory=MilvusConfig.from_env)
    embeddings: EmbeddingsConfig = field(default_factory=EmbeddingsConfig.from_env)
    llm: LLMConfig = field(default_factory=LLMConfig.from_env)
    paths: PathConfig = field(default_factory=PathConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig.from_env)
    
    project_name: str = "RiskAgent-AgenticRAG"


# 单例实例
settings = Settings()

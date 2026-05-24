"""RiskAgent Configuration -- 使用 pydantic-settings 管理配置."""

from __future__ import annotations

import os
import pathlib
from typing import Annotated, Literal

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# 在创建 Settings 单例之前加载 .env 文件，override=True 确保项目 .env 覆盖旧的 OS 环境变量
_env_path = pathlib.Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_env_path, override=True)


class MilvusConfig(BaseSettings):
    """Milvus 向量数据库配置."""

    model_config = SettingsConfigDict(env_prefix="MILVUS_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    uri: str | None = None
    host: str = "localhost"
    port: int = 19530
    user: str | None = None
    password: SecretStr | None = None
    secure: bool = False
    collection_name: str = "riskagent_agenticrag"
    index_type: str = "IVF_FLAT"
    metric_type: Literal["L2", "IP", "COSINE"] = "L2"
    nlist: int = 128
    nprobe: int = 16
    wait_ready: bool = True
    health_port: int = 9091
    ready_timeout_s: float = 120.0
    consistency_level: Literal["Strong", "Session", "Bounded", "Eventually"] = "Session"
    use_docker: bool = Field(default=False, alias="RISKAGENT_USE_DOCKER_MILVUS")


class RedisConfig(BaseSettings):
    """Redis 缓存配置."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = "localhost"
    port: int = 6379
    password: SecretStr = SecretStr("riskagent")
    db: int = 0
    url: str | None = None

    @property
    def redis_url(self) -> str:
        """构建 Redis 连接 URL."""
        if self.url:
            return self.url
        password_str = self.password.get_secret_value()
        if password_str:
            return f"redis://:{password_str}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class EmbeddingsConfig(BaseSettings):
    """Embedding 模型配置."""

    model_config = SettingsConfigDict(env_prefix="EMBEDDINGS_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    provider: Literal["hf", "openai", "hash"] = "hf"
    model_name: str = "BAAI/bge-large-zh-v1.5"


class LLMConfig(BaseSettings):
    """LLM 服务配置."""

    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_key: SecretStr | None = Field(default=None, alias="LLM_API_KEY")
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    base_url: str = "https://ark.cn-beijing.volces.com/api/coding/v3"
    model: str = "ark-code-latest"
    provider: str = "openai_compatible"

    @property
    def resolved_api_key(self) -> SecretStr:
        """获取解析后的 API Key."""
        if self.api_key:
            return self.api_key
        if self.openai_api_key:
            return self.openai_api_key
        raise ValueError("No API key configured")


class PathConfig(BaseSettings):
    """项目路径配置."""

    model_config = SettingsConfigDict(env_prefix="RISKAGENT_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_root: pathlib.Path = Field(
        default_factory=lambda: pathlib.Path(__file__).resolve().parents[3]
    )
    corpus_dir: pathlib.Path = Field(default_factory=lambda: pathlib.Path("corpus"))
    persist_dir: pathlib.Path = Field(default_factory=lambda: pathlib.Path(".milvus"))

    @property
    def milvus_lite_dir(self) -> pathlib.Path:
        runtime_persist_dir = os.getenv("RISKAGENT_PERSIST_DIR", "").strip()
        if runtime_persist_dir:
            return pathlib.Path(runtime_persist_dir)
        return self.persist_dir

    @property
    def models_dir(self) -> pathlib.Path:
        return self.project_root / "models"

    @property
    def hf_cache_dir(self) -> pathlib.Path:
        return self.models_dir / "hf"


class FeatureConfig(BaseSettings):
    """功能开关配置."""

    model_config = SettingsConfigDict(env_prefix="RISKAGENT_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    use_langgraph: bool = Field(default=False, alias="USE_LANGGRAPH")
    self_rag_enabled: bool = True
    query_intel_enabled: bool = True
    retrieval_pipeline: str = "hybrid_query_intel_advanced_index"
    prompt_version: str = "v1"
    trace_snippet_chars: int = 240


class RateLimitConfig(BaseSettings):
    """速率限制配置."""

    model_config = SettingsConfigDict(env_prefix="RATE_LIMIT_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    enabled: bool = True
    per_minute: int = 60
    per_hour: int = 1000


class LLMGovernanceConfig(BaseSettings):
    """LLM traffic management and governance configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM_GOVERNANCE_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Token Bucket rate limiting
    rate_limit_tokens_per_min: int = 60000
    rate_limit_tokens_per_min_non_critical: int = 8000
    burst_tokens: int = 0  # 0 means use per_min value
    burst_tokens_non_critical: int = 0

    # Token alert thresholds
    token_alert_hourly: int = 100000
    token_alert_daily: int = 2000000

    # Retry configuration
    max_retries: int = 3
    retry_backoff_base: float = 1.0

    # Timeout configuration (seconds)
    timeout_total: int = 120
    timeout_connect: int = 10
    timeout_read: int = 90

    # Cache
    cache_enabled: bool = True
    cache_max_size: int = 1000

    # Concurrency limit
    max_concurrent_requests: int = 10


class APIAuthConfig(BaseSettings):
    """API 认证配置."""

    model_config = SettingsConfigDict(env_prefix="API_KEY_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    enabled: bool = True
    secret: SecretStr = SecretStr("change-me-in-production")


class Settings(BaseSettings):
    """全局配置聚合类."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = "RiskAgent-AgenticRAG"

    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    llm_governance: LLMGovernanceConfig = Field(default_factory=LLMGovernanceConfig)
    api_auth: APIAuthConfig = Field(default_factory=APIAuthConfig)


# 单例实例
settings = Settings()


def get_settings() -> Settings:
    """获取全局配置单例."""
    return settings

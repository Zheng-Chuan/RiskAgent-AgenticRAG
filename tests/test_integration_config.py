"""配置集成测试 - 测试配置管理."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from riskagent_agenticrag.config.settings import Settings
from riskagent_agenticrag.constants import DEFAULT_LLM_MODEL


class TestSettings:
    """配置测试."""

    def test_default_settings(self):
        """测试默认配置."""
        settings = Settings()
        assert settings.project_name == "RiskAgent-AgenticRAG"
        assert settings.llm.model == DEFAULT_LLM_MODEL

    def test_milvus_config_defaults(self):
        """测试 Milvus 配置默认值."""
        settings = Settings()
        assert settings.milvus.host == "localhost"
        assert settings.milvus.port == 19530
        assert settings.milvus.collection_name == "riskagent_agenticrag"

    def test_redis_config_defaults(self):
        """测试 Redis 配置默认值."""
        settings = Settings()
        assert settings.redis.host == "localhost"
        assert settings.redis.port == 6379

    @patch.dict(os.environ, {"MILVUS_HOST": "test-host", "MILVUS_PORT": "12345"})
    def test_env_var_override(self):
        """测试环境变量覆盖."""
        settings = Settings()
        assert settings.milvus.host == "test-host"
        assert settings.milvus.port == 12345

    @patch.dict(os.environ, {"REDIS_URL": "redis://custom:6379/1"})
    def test_redis_url_config(self):
        """测试 Redis URL 配置."""
        settings = Settings()
        assert settings.redis.url == "redis://custom:6379/1"

    def test_secret_str_handling(self):
        """测试 SecretStr 处理."""
        settings = Settings()
        password = settings.redis.password
        assert hasattr(password, "get_secret_value")
        assert password.get_secret_value() == "riskagent"

    @patch.dict(os.environ, {"API_KEY_ENABLED": "false"})
    def test_api_auth_disabled(self):
        """测试 API 认证禁用."""
        settings = Settings()
        assert settings.api_auth.enabled is False

    @patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "100", "RATE_LIMIT_PER_HOUR": "1000"})
    def test_rate_limit_config(self):
        """测试速率限制配置."""
        settings = Settings()
        assert settings.rate_limit.per_minute == 100
        assert settings.rate_limit.per_hour == 1000


class TestSettingsValidation:
    """配置验证测试."""

    def test_literal_validation(self):
        """测试 Literal 类型验证."""
        settings = Settings()
        assert settings.milvus.metric_type in ["L2", "IP", "COSINE"]
        assert settings.milvus.consistency_level in ["Strong", "Session", "Bounded", "Eventually"]

    def test_path_config(self):
        """测试路径配置."""
        settings = Settings()
        assert settings.paths.project_root.exists()
        assert settings.paths.models_dir.exists() or settings.paths.models_dir.parent.exists()


def test_settings_singleton():
    """测试配置单例（如果是单例的话）."""
    from riskagent_agenticrag.config.settings import settings as singleton_settings
    settings1 = Settings()
    assert singleton_settings is not None
    assert settings1.project_name == singleton_settings.project_name

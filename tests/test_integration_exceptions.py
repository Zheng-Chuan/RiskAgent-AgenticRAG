"""异常集成测试 - 测试自定义异常层级."""

from __future__ import annotations

import pytest

from riskagent_agenticrag.exceptions import (
    APIError,
    AuthenticationError,
    CacheConnectionError,
    CacheError,
    ConfigurationError,
    DocumentProcessingError,
    LLMAPIError,
    LLMError,
    LLMTimeoutError,
    MilvusConnectionError,
    MilvusSearchError,
    RateLimitExceededError,
    RetrievalError,
    RiskAgentError,
    ToolError,
    ValidationGateError,
    VectorStoreError,
)


class TestBaseException:
    """基础异常测试."""

    def test_riskagent_error(self):
        """测试基础异常."""
        error = RiskAgentError("test message")
        assert str(error) == "test message"
        assert error.message == "test message"
        assert error.details == {}

    def test_riskagent_error_with_details(self):
        """测试带详情的异常."""
        details = {"key": "value", "code": 500}
        error = RiskAgentError("test message", details=details)
        assert error.details == details


class TestExceptionHierarchy:
    """异常层级测试."""

    def test_configuration_error_inheritance(self):
        """测试配置异常继承."""
        error = ConfigurationError("config error")
        assert isinstance(error, RiskAgentError)

    def test_llm_error_inheritance(self):
        """测试 LLM 异常继承."""
        error = LLMError("llm error")
        assert isinstance(error, RiskAgentError)

        api_error = LLMAPIError("api error")
        assert isinstance(api_error, LLMError)

        timeout_error = LLMTimeoutError("timeout")
        assert isinstance(timeout_error, LLMError)

    def test_retrieval_error_inheritance(self):
        """测试检索异常继承."""
        error = RetrievalError("retrieval error")
        assert isinstance(error, RiskAgentError)

    def test_vector_store_error_inheritance(self):
        """测试向量数据库异常继承."""
        error = VectorStoreError("vector store error")
        assert isinstance(error, RiskAgentError)

        milvus_error = MilvusConnectionError("connection error")
        assert isinstance(milvus_error, VectorStoreError)

        search_error = MilvusSearchError("search error")
        assert isinstance(search_error, VectorStoreError)

    def test_cache_error_inheritance(self):
        """测试缓存异常继承."""
        error = CacheError("cache error")
        assert isinstance(error, RiskAgentError)

        conn_error = CacheConnectionError("connection error")
        assert isinstance(conn_error, CacheError)

    def test_api_error_inheritance(self):
        """测试 API 异常继承."""
        error = APIError("api error")
        assert isinstance(error, RiskAgentError)

        auth_error = AuthenticationError("auth error")
        assert isinstance(auth_error, APIError)

        rate_error = RateLimitExceededError("rate limit")
        assert isinstance(rate_error, APIError)

    def test_document_processing_error_inheritance(self):
        """测试文档处理异常继承."""
        error = DocumentProcessingError("doc error")
        assert isinstance(error, RiskAgentError)

    def test_validation_error_inheritance(self):
        """测试验证异常继承."""
        error = ValidationGateError("validation error")
        assert isinstance(error, RiskAgentError)

    def test_tool_error_inheritance(self):
        """测试工具异常继承."""
        error = ToolError("tool error")
        assert isinstance(error, RiskAgentError)


class TestExceptionUsage:
    """异常使用测试."""

    def test_exception_catching_hierarchy(self):
        """测试异常捕获层级."""
        try:
            raise LLMAPIError("test api error", details={"status_code": 500})
        except LLMError:
            caught = True
        except RiskAgentError:
            caught = False
        assert caught

    def test_exception_catching_base(self):
        """测试捕获基础异常."""
        try:
            raise MilvusSearchError("search failed")
        except RiskAgentError as e:
            assert isinstance(e, VectorStoreError)

    def test_exception_details_access(self):
        """测试异常详情访问."""
        details = {"attempt": 3, "retryable": True}
        try:
            raise CacheConnectionError("connection failed", details=details)
        except CacheError as e:
            assert e.details == details
            assert e.details["attempt"] == 3


def test_all_exceptions_importable():
    """测试所有异常都可导入."""
    from riskagent_agenticrag import exceptions

    assert hasattr(exceptions, "RiskAgentError")
    assert hasattr(exceptions, "ConfigurationError")
    assert hasattr(exceptions, "LLMError")
    assert hasattr(exceptions, "RetrievalError")
    assert hasattr(exceptions, "VectorStoreError")
    assert hasattr(exceptions, "CacheError")
    assert hasattr(exceptions, "APIError")
    assert hasattr(exceptions, "DocumentProcessingError")
    assert hasattr(exceptions, "ValidationGateError")
    assert hasattr(exceptions, "ToolError")

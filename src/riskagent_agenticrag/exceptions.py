"""RiskAgent 自定义异常层级."""

from __future__ import annotations


class RiskAgentError(Exception):
    """RiskAgent 基础异常类."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# ==========================================
# 配置相关异常
# ==========================================

class ConfigurationError(RiskAgentError):
    """配置错误异常."""
    pass


class MissingEnvironmentVariableError(ConfigurationError):
    """缺少环境变量异常."""
    pass


class InvalidConfigurationError(ConfigurationError):
    """无效配置异常."""
    pass


# ==========================================
# LLM 相关异常
# ==========================================

class LLMError(RiskAgentError):
    """LLM 调用基础异常."""
    pass


class LLMAPIError(LLMError):
    """LLM API 调用异常."""
    pass


class LLMTimeoutError(LLMError):
    """LLM 调用超时异常."""
    pass


class LLMInvalidResponseError(LLMError):
    """LLM 无效响应异常."""
    pass


class LLMTokenLimitExceededError(LLMError):
    """LLM Token 超限异常."""
    pass


# ==========================================
# 检索相关异常
# ==========================================

class RetrievalError(RiskAgentError):
    """检索基础异常."""
    pass


class IndexNotFoundError(RetrievalError):
    """索引未找到异常."""
    pass


class RetrievalTimeoutError(RetrievalError):
    """检索超时异常."""
    pass


class NoDocumentsFoundError(RetrievalError):
    """未找到文档异常."""
    pass


# ==========================================
# 向量数据库相关异常
# ==========================================

class VectorStoreError(RiskAgentError):
    """向量存储基础异常."""
    pass


class MilvusConnectionError(VectorStoreError):
    """Milvus 连接异常."""
    pass


class MilvusCollectionNotFoundError(VectorStoreError):
    """Milvus 集合未找到异常."""
    pass


class MilvusInsertError(VectorStoreError):
    """Milvus 插入异常."""
    pass


class MilvusSearchError(VectorStoreError):
    """Milvus 搜索异常."""
    pass


# ==========================================
# 缓存相关异常
# ==========================================

class CacheError(RiskAgentError):
    """缓存基础异常."""
    pass


class CacheConnectionError(CacheError):
    """缓存连接异常."""
    pass


class CacheOperationError(CacheError):
    """缓存操作异常."""
    pass


# ==========================================
# API 相关异常
# ==========================================

class APIError(RiskAgentError):
    """API 基础异常."""
    pass


class AuthenticationError(APIError):
    """认证失败异常."""
    pass


class AuthorizationError(APIError):
    """授权失败异常."""
    pass


class RateLimitExceededError(APIError):
    """速率限制超限异常."""
    pass


class ValidationError(APIError):
    """请求验证异常."""
    pass


# ==========================================
# 文档处理相关异常
# ==========================================

class DocumentProcessingError(RiskAgentError):
    """文档处理基础异常."""
    pass


class UnsupportedDocumentTypeError(DocumentProcessingError):
    """不支持的文档类型异常."""
    pass


class DocumentCorruptedError(DocumentProcessingError):
    """文档损坏异常."""
    pass


class DocumentParsingError(DocumentProcessingError):
    """文档解析异常."""
    pass


# ==========================================
# 验证相关异常
# ==========================================

class ValidationGateError(RiskAgentError):
    """验证门禁异常."""
    pass


class ResponseValidationError(ValidationGateError):
    """响应验证失败异常."""
    pass


# ==========================================
# 工具异常
# ==========================================

class ToolError(RiskAgentError):
    """工具调用基础异常."""
    pass


class ToolExecutionError(ToolError):
    """工具执行异常."""
    pass


class ToolNotFoundError(ToolError):
    """工具未找到异常."""
    pass

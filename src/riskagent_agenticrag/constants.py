"""RiskAgent 常量配置 - 集中管理魔法数字和字符串."""

from __future__ import annotations

# ==========================================
# 默认值
# ==========================================

DEFAULT_LLM_TEMPERATURE = 0.0
DEFAULT_LLM_MAX_TOKENS = 4096
DEFAULT_RETRIEVAL_K = 4
DEFAULT_MAX_AGENTIC_ROUNDS = 2

# ==========================================
# 嵌入模型配置
# ==========================================

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"
DEFAULT_EMBEDDING_DIMENSION = 1024

# ==========================================
# Milvus 配置
# ==========================================

DEFAULT_MILVUS_PORT = 19530
DEFAULT_MILVUS_HEALTH_PORT = 9091
DEFAULT_MILVUS_COLLECTION = "riskagent_agenticrag"
DEFAULT_MILVUS_INDEX_TYPE = "IVF_FLAT"
DEFAULT_MILVUS_METRIC_TYPE = "L2"
DEFAULT_MILVUS_NLIST = 128
DEFAULT_MILVUS_NPROBE = 16
DEFAULT_MILVUS_READY_TIMEOUT_S = 120.0
MILVUS_CONSISTENCY_LEVELS = ["Strong", "Session", "Bounded", "Eventually"]

# ==========================================
# Redis 配置
# ==========================================

DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0
DEFAULT_REDIS_PASSWORD = "riskagent"
DEFAULT_CACHE_TTL = 3600  # 1 hour
LLM_CACHE_TTL = 3600 * 24  # 24 hours
EMBEDDING_CACHE_TTL = 3600 * 24 * 7  # 7 days

# ==========================================
# 文档处理配置
# ==========================================

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
MAX_CHUNK_SIZE = 5000
MIN_CHUNK_SIZE = 100

SUPPORTED_DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".html": "text/html",
    ".htm": "text/html",
    ".md": "text/markdown",
    ".txt": "text/plain",
}

# ==========================================
# API 配置
# ==========================================

DEFAULT_API_HOST = "0.0.0.0"
DEFAULT_API_PORT = 8000
DEFAULT_RATE_LIMIT_PER_MINUTE = 60
DEFAULT_RATE_LIMIT_PER_HOUR = 1000

# ==========================================
# 验证门禁配置
# ==========================================

MIN_RETRIEVED_DOCS = 1
MAX_RETRIEVED_DOCS = 20
CitationPrecision_THRESHOLD = 0.7
DomainConsistency_THRESHOLD = 0.8

# ==========================================
# 提示词版本
# ==========================================

PROMPT_VERSION_V1 = "v1"
PROMPT_VERSION_V2 = "v2"
DEFAULT_PROMPT_VERSION = PROMPT_VERSION_V1

# ==========================================
# 追踪配置
# ==========================================

DEFAULT_TRACE_SNIPPET_CHARS = 240
MAX_TRACE_SNIPPET_CHARS = 1000

# ==========================================
# LLM 模型配置
# ==========================================

DEFAULT_LLM_MODEL = "qwen3-8b"
DEFAULT_LLM_BASE_URL = "https://api.n1n.ai/v1"

# ==========================================
# 项目路径
# ==========================================

CORPUS_DIR_NAME = "corpus"
PERSIST_DIR_NAME = ".milvus"
MODELS_DIR_NAME = "models"
ARTIFACTS_DIR_NAME = ".artifacts"

# ==========================================
# HTTP 状态码
# ==========================================

HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_503_SERVICE_UNAVAILABLE = 503

# ==========================================
# 日志配置
# ==========================================

LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL = "INFO"

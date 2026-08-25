# ---- 构建阶段: 安装依赖 ----
FROM python:3.10-slim AS builder

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# 先复制依赖文件 利用 Docker 缓存
COPY pyproject.toml setup.cfg* ./

# 安装 Python 依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 安装项目依赖 (不安装 dev 依赖, 不安装 hf 可选依赖; eval 组启用 RAGAS 评测)
COPY src/ /build/src/
RUN pip install --no-cache-dir -e "/build[eval]" || pip install --no-cache-dir -e /build

# ---- 运行阶段: 精简镜像 ----
FROM python:3.10-slim AS runtime

# 运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl procps \
    && rm -rf /var/lib/apt/lists/*

# 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# HuggingFace 离线模式 (仅 hf provider 需要, 默认用远程 API)
ENV TOKENIZERS_PARALLELISM=false

WORKDIR /app

# 复制项目文件
COPY src/ /app/src/
COPY corpus/ /app/corpus/
COPY config/ /app/config/
# 评测数据集 (50 题 + qrels) bake 进镜像, 避免每次重建 pod 后手动 kubectl cp
COPY tests/data/ /app/tests/data/
COPY pyproject.toml /app/

# 持久化目录
RUN mkdir -p /app/.milvus /app/.artifacts /app/models/hf

# 暴露 API 端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -sf http://localhost:8000/healthz || exit 1

# 启动 API 服务
CMD ["python", "-m", "riskagent_agenticrag.api.server"]

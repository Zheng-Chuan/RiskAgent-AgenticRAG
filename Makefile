.PHONY: install install-dev lock-env test lint typecheck format clean docs help offline-regression accept-release

# 定义默认目标
.DEFAULT_GOAL := help

# ==========================================
# 依赖管理
# ==========================================

install:  ## 安装项目依赖
	pip install -e .

install-dev:  ## 安装项目依赖（含开发依赖）
	pip install -e ".[dev]"

lock-env:  ## 生成可复现环境
	conda env create -f environment.yml || conda env update -f environment.yml --prune

# ==========================================
# 代码质量
# ==========================================

test:  ## 运行测试
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/ -v --tb=short

test-cov:  ## 运行测试并生成覆盖率报告
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_cov tests/ -v --cov=src --cov-report=html --cov-report=term

test-watch:  ## 监听文件变化并自动运行测试
	ptw tests/

lint:  ## 运行代码检查
	ruff check src/ tests/
	ruff format --check src/ tests/

format:  ## 格式化代码
	ruff format src/ tests/
	isort src/ tests/

typecheck:  ## 运行类型检查
	mypy src/
	pyright src/

check: lint typecheck test  ## 运行所有检查（lint + typecheck + test）

# ==========================================
# 开发服务
# ==========================================

up:  ## 启动 Docker 服务（Milvus + Redis）
	docker compose -f deploy/dev/docker-compose.yml up -d

down:  ## 停止 Docker 服务
	docker compose -f deploy/dev/docker-compose.yml down

logs:  ## 查看 Docker 服务日志
	docker compose -f deploy/dev/docker-compose.yml logs -f

# ==========================================
# 项目操作
# ==========================================

index:  ## 构建索引
	conda run -n LangChain python -m riskagent_agenticrag.cli index --corpus-dir corpus --persist-dir .milvus

ask:  ## CLI 提问（使用示例问题）
	conda run -n LangChain python -m riskagent_agenticrag.cli ask --question "what is FRTB"

api:  ## 启动 API 服务器
	conda run -n LangChain python -m riskagent_agenticrag.api.server

eval:  ## 运行评测
	conda run -n LangChain python -m riskagent_agenticrag.evaluation.run --label unified_pipeline

offline-regression:  ## 运行纯离线回归
	bash scripts/run_offline_regression.sh

accept-release:  ## 运行最小发布验收
	bash scripts/release_acceptance.sh

# ==========================================
# 清理
# ==========================================

clean:  ## 清理构建文件和缓存
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -f {} +

# ==========================================
# 帮助
# ==========================================

help:  ## 显示此帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

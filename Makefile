.PHONY: install install-dev lock-env test lint typecheck format clean docs help offline-regression accept-release test-unit test-smoke test-scenario test-perf test-all test-coverage test-cov test-watch check up down logs index ask api eval

# 定义默认目标
.DEFAULT_GOAL := help

# 统一执行环境
CONDA_ENV ?= agenticrag
CONDA_RUN := conda run -n $(CONDA_ENV)
PYTHON := $(CONDA_RUN) python
PIP := $(CONDA_RUN) pip
PYTEST := PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $(PYTHON) -m pytest

# ==========================================
# 依赖管理
# ==========================================

install:  ## 安装项目依赖
	$(PIP) install -e .

install-dev:  ## 安装项目依赖（含开发依赖）
	$(PIP) install -e ".[dev]"

lock-env:  ## 生成可复现环境
	conda env create -f environment.yml || conda env update -f environment.yml --prune

# ==========================================
# 代码质量
# ==========================================

test:  ## 运行测试
	$(PYTEST) tests/ -v --tb=short

test-cov:  ## 运行测试并生成覆盖率报告
	$(PYTEST) -p pytest_cov tests/ -v --cov=src --cov-report=html --cov-report=term

test-watch:  ## 监听文件变化并自动运行测试
	$(CONDA_RUN) ptw tests/

# ─── Test Targets ─────────────────────────────────────────
test-unit:  ## 运行单元测试
	$(PYTEST) tests/unit/ -v --cov=src/riskagent_agenticrag --cov-report=term-missing -m unit

test-smoke:  ## 运行冒烟测试
	$(PYTEST) tests/smoke/ -v -m smoke

test-scenario:  ## 运行场景测试
	$(PYTEST) tests/scenario/ -v -s -m scenario

test-perf:  ## 运行性能测试
	$(PYTEST) tests/performance/ -v -s -m performance

test-all:  ## 运行所有测试
	$(PYTEST) tests/ -v --cov=src/riskagent_agenticrag --cov-report=html --cov-report=term-missing

test-coverage:  ## 运行测试覆盖率检查
	$(PYTEST) tests/unit/ tests/smoke/ -v --cov=src/riskagent_agenticrag --cov-report=html --cov-report=term-missing --cov-fail-under=90

lint:  ## 运行代码检查
	$(CONDA_RUN) ruff check src/ tests/
	$(CONDA_RUN) ruff format --check src/ tests/

format:  ## 格式化代码
	$(CONDA_RUN) ruff format src/ tests/
	$(CONDA_RUN) isort src/ tests/

typecheck:  ## 运行类型检查
	$(CONDA_RUN) mypy src/
	$(CONDA_RUN) pyright src/

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
	$(PYTHON) -m riskagent_agenticrag.cli index --corpus-dir corpus --persist-dir .milvus

ask:  ## CLI 提问（使用示例问题）
	$(PYTHON) -m riskagent_agenticrag.cli ask --question "what is FRTB"

api:  ## 启动 API 服务器
	$(PYTHON) -m riskagent_agenticrag.api.server

eval:  ## 运行评测
	$(PYTHON) -m riskagent_agenticrag.evaluation.run --label unified_pipeline

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

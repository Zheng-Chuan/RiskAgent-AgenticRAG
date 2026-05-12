# RiskAgent-AgenticRAG

面向金融风险知识检索与解释的 Agentic RAG 系统.
核心目标: 可验证回答 -- 回答必须附带引用, 可回放 可排障 可回归.

## 快速开始

```bash
make install
docker compose -f deploy/dev/docker-compose.yml up -d
conda run -n LangChain python -m riskagent_agenticrag.cli index --corpus-dir corpus --persist-dir .milvus
conda run -n LangChain python -m riskagent_agenticrag.cli ask --question "what is FRTB"
```

详细步骤见 [QUICKSTART](docs/QUICKSTART.md).

## 文档导航

| 文档 | 说明 |
| --- | --- |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 系统概览 模块边界 数据流 LangGraph 流程 |
| [QUICKSTART](docs/QUICKSTART.md) | 安装 中间件 语料 CLI API 全流程 |
| [API](docs/API.md) | HTTP API v1 契约和调用示例 |
| [DATA](docs/DATA.md) | 核心数据结构 字段约定 Trace 排障 |
| [EVALUATION](docs/EVALUATION.md) | 指标定义 对比实验 历史数据 门禁策略 面试速答 |
| [PRD](docs/PRD.md) | 当前现状 顶尖 RAG 改进方案 与可验收 checklist |
| [ROADMAP](docs/ROADMAP.md) | 里程碑 交付项 验收状态 |
| [eval_thresholds.yaml](docs/eval_thresholds.yaml) | 阈值门禁配置 |

## 常用命令

```bash
# 增量索引
conda run -n LangChain python -m riskagent_agenticrag.cli index --corpus-dir corpus --persist-dir .milvus

# CLI 提问
conda run -n LangChain python -m riskagent_agenticrag.cli ask --question "what is FRTB"

# 运行评测
conda run -n LangChain python -m riskagent_agenticrag.evaluation.run --stage step4 --label step4

# 启动 API
conda run -n LangChain python -m riskagent_agenticrag.server

# 运行测试
python -m pytest tests/ -v
```

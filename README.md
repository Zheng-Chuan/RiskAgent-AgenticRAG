# RiskAgent-AgenticRAG

面向金融风险知识检索与解释的高可信 RAG 系统.
核心目标: 可验证回答 -- 回答必须附带引用, 可回放 可排障 可回归.

## 快速开始

```bash
make install
docker compose -f deploy/dev/docker-compose.yml up -d
conda run -n LangChain python -m riskagent_agenticrag.cli index --corpus-dir corpus --persist-dir .milvus
conda run -n LangChain python -m riskagent_agenticrag.cli ask --question "what is FRTB"
```

详细设计见 [ARCHITECTURE](docs/ARCHITECTURE.md).

## 文档导航

| 文档 | 说明 |
| --- | --- |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 系统概览 模块边界 数据流 LangGraph 流程 |
| [PRD](docs/PRD.md) | 当前现状 顶尖 RAG 改进方案 与可验收 checklist |
| [INTERVIEW](docs/INTERVIEW.md) | 面向资深面试官的项目专属 RAG 拷打题库 与追问方向 |

## 常用命令

```bash
# 增量索引
conda run -n LangChain python -m riskagent_agenticrag.cli index --corpus-dir corpus --persist-dir .milvus

# CLI 提问
conda run -n LangChain python -m riskagent_agenticrag.cli ask --question "what is FRTB"

# 运行评测
conda run -n LangChain python -m riskagent_agenticrag.evaluation.run --label unified_pipeline

# 启动 API
conda run -n LangChain python -m riskagent_agenticrag.server

# 运行测试
python -m pytest tests/ -v
```

## 评测口径

- 核心回答指标: `citation_coverage` `faithfulness` `answer_relevancy`
- 句级证据分析: 报告会输出 `supported_sentences` 与 `unsupported_sentences`
- 金融专项指标: `numeric_consistency_score` `glossary_consistency_score`
- 阈值配置: [eval_thresholds.json](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/config/eval_thresholds.json)

## 报告引用

- 基准报告 JSON: [rag_eval_baseline_sample.json](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts/reports/rag_eval_baseline_sample.json)
- 基准报告 Markdown: [rag_eval_baseline_sample.md](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts/reports/rag_eval_baseline_sample.md)
- 后续在 `README.md` `docs/ARCHITECTURE.md` `docs/PRD.md` 中出现的关键数字 必须能映射到具体报告文件

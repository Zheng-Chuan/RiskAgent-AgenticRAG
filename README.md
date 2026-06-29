# RiskAgent-AgenticRAG

## 项目概述

这是一个面向金融风控知识问答场景的高可信 RAG 系统.  
项目目标不是做巨无霸 Agent 平台.  
项目目标是把 `检索` `召回` `证据链` `评测` `发布门禁` 这几件事做到很强.

当前主链已经具备下面这些真实能力.

- 默认执行链路固定为 `rewrite -> retrieve_and_critique -> revise_query loop -> synthesize_answer -> validate_and_save`
- 统一检索主链固定为 `Hybrid Retrieval + Query Intelligence + Advanced Index`
- 检索侧已经具备 `dense + BM25 + RRF + cross-encoder rerank + diversity select`
- 索引侧已经具备 `parent child` `summary index` `HyDE index` `incremental index`
- 生成侧会产出 `answer` `citations` `claims` `evidence_set` `decision_log`
- 校验侧已经具备 `refusal gate` `evidence gate` `numeric gate`
- 评测侧已经具备 `qrels` `citation precision` `answer eval` `domain consistency` `threshold gate`

## 当前口径

这个仓库现在只对外讲已经被真实代码 真实测试 真实评测和真实报告证明过的能力.  
如果实现和文档冲突 先修正文档口径或重新讨论设计 再继续开发.

## 文档体系

本项目现在采用和 `RiskMonitor-MultiAgent` 同一类分层文档体系.  
文档和代码必须一起演进.

- `README.md`: 对外总览和目录. 只讲已经被代码 测试 评测证明过的能力
- `docs/PRD.md`: 产品总纲 范围边界 成功标准 文档索引
- `docs/ARCHITECTURE.md`: 运行时主链和系统结构的权威说明
- `docs/STRATEGY.md`: 项目长期方向和核心取舍
- `docs/RESUME.md`: 对外表述和简历口径收敛
- `docs/decisions/ADR-*.md`: 已接受的架构决策和 trade-off
- `docs/decisions/RFC-*.md`: 大改动提案和待决问题
- `docs/phases/*.md`: 分阶段迭代计划 checkpoint exit criteria 和交付物
- `docs/INTERVIEW.md`: 面向高压面试追问的专项问答

文档迭代流程.

1. 先在 `RFC` 或对应 `phase` 文档里写清楚目标 约束 trade-off 风险和验收方式
2. 方案确认后 在 `PRD` `ARCHITECTURE` `ADR` 中沉淀权威口径
3. 编码时和代码同 PR 更新文档
4. 验收通过后 回写 `phase` 状态 证据路径 和 README 对外口径
5. 如果方案回退或收缩 必须同步清理冲突文档

## 代码入口

- 应用门面: `src/riskagent_agenticrag/app.py`
- LangGraph 主链: `src/riskagent_agenticrag/orchestration/langgraph_runner.py`
- 检索装配: `src/riskagent_agenticrag/rag/retriever_factory.py`
- 索引入口: `src/riskagent_agenticrag/indexing/indexer.py`
- 评测入口: `src/riskagent_agenticrag/evaluation/run.py`
- API 入口: `src/riskagent_agenticrag/api/server.py`

## 文档

- [docs/PRD.md](docs/PRD.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/STRATEGY.md](docs/STRATEGY.md)
- [docs/RESUME.md](docs/RESUME.md)
- [docs/INTERVIEW.md](docs/INTERVIEW.md)
- [docs/decisions/](docs/decisions/)
- [docs/phases/](docs/phases/)

## 快速开始

```bash
make install
make up
make index
make ask
```

## 常用命令

```bash
# 使用默认 conda 环境 agenticrag
make index
make ask
make api
make eval
make test
make accept-release

# 如果本地环境名不同
make test CONDA_ENV=riskagent-agenticrag
```

## 评测口径

- 核心回答指标: `citation_coverage` `faithfulness` `answer_relevancy`
- 检索指标: `retrieval_recall_at_k` `retrieval_mrr` `retrieval_ndcg_at_k`
- 句级证据分析: `supported_sentences` `unsupported_sentences`
- 金融专项指标: `numeric_consistency_score` `glossary_consistency_score`
- 阈值配置: [eval_thresholds.json](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/config/eval_thresholds.json)

## 报告引用

- 基准报告 JSON: [rag_eval_baseline_sample.json](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts/reports/rag_eval_baseline_sample.json)
- 基准报告 Markdown: [rag_eval_baseline_sample.md](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts/reports/rag_eval_baseline_sample.md)
- 后续在 `README.md` `docs/ARCHITECTURE.md` `docs/PRD.md` 中出现的关键数字 都应该能映射到具体报告文件

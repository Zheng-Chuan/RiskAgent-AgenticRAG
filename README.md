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
- `docs/evaluations/EVALUATION_LOG.md`: 每次正式评测的结果台账 FAIL 根因和修复追踪
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
- [docs/evaluations/EVALUATION_LOG.md](docs/evaluations/EVALUATION_LOG.md)

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

- 样例基准报告 JSON: [rag_eval_baseline_sample.json](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts/reports/rag_eval_baseline_sample.json)
- 样例基准报告 Markdown: [rag_eval_baseline_sample.md](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts/reports/rag_eval_baseline_sample.md)
- 当前仓库里的样例报告主要用于验证报告结构和 threshold gate 流程
- 该样例报告仍带有旧字段 `retriever_mode=step4` 不应被当成当前统一检索主链的正式新基线
- `scripts/release_acceptance.sh` 现在支持两条路径
- 有可用 `LLM key` 时优先跑 fresh eval
- 没有可用 `LLM key` 时回退到样例报告做 smoke 级校验
- 当前最新的真实新报告已经是 `50` 题 full baseline fresh eval
- 历次评测结果 FAIL 根因和修复追踪见 [docs/evaluations/EVALUATION_LOG.md](docs/evaluations/EVALUATION_LOG.md)
- 当前最新 gate 全绿报告: `prod_pipeline_v10b_targ_rerank_recallfix` (2026-08-18, `passed=47/50` `faithfulness=0.895` `citation_coverage=0.940` `answer_relevancy=0.943` `retrieval_recall_at_5=0.78`, gate PASS)
- v10b 报告 Markdown: [rag_eval_prod_pipeline_v10b_targ_rerank_recallfix_20260818_073514.md](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts/reports/rag_eval_prod_pipeline_v10b_targ_rerank_recallfix_20260818_073514.md)
- full baseline 报告 JSON: [rag_eval_unified_full_baseline_after_judge_parallel_bugfix_20260718_20260718_065654.json](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts_fresh/reports/rag_eval_unified_full_baseline_after_judge_parallel_bugfix_20260718_20260718_065654.json)
- full baseline 报告 Markdown: [rag_eval_unified_full_baseline_after_judge_parallel_bugfix_20260718_20260718_065654.md](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts_fresh/reports/rag_eval_unified_full_baseline_after_judge_parallel_bugfix_20260718_20260718_065654.md)
- smoke 报告 JSON: [rag_eval_unified_smoke_5q_20260706_20260706_103824.json](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts_fresh/reports/rag_eval_unified_smoke_5q_20260706_20260706_103824.json)
- smoke 报告 Markdown: [rag_eval_unified_smoke_5q_20260706_20260706_103824.md](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.artifacts_fresh/reports/rag_eval_unified_smoke_5q_20260706_20260706_103824.md)
- 这份 smoke 报告已经证明外部 `LLM key` 和当前统一主链能够真实打通
- 2026-07-18 full baseline 的关键结果是 `passed=38/50` `citation_coverage=0.960` `faithfulness=0.775` `answer_relevancy=0.848` `retrieval_recall_at_5=0.500` gate `fail`
- 该瓶颈已在 2026-08-18 `v10b` 报告中解决 (`retrieval_recall_at_5=0.78` gate 首次全绿), 详见评测台账
- `release acceptance` 尚未用 `v10b` 报告重跑
- 遗留: v10b 3 个 FAIL (`FVA` `MVA` `ColVA`) 根因是 TARG 词表缺失, 修复已合入待部署, 详见评测台账
- 后续在 `README.md` `docs/ARCHITECTURE.md` `docs/PRD.md` 中出现的关键数字 都应该能映射到具体报告文件

## 当前工程现实

- 默认 conda 环境口径是 `agenticrag`
- `deploy/dev/docker-compose.yml` 定义了本地 `Milvus` 和 `Redis` 两个依赖
- 仓库里已经存在本地数据卷快照 说明曾经跑过真实中间件和索引流程
- 当前仓库审计时已经验证 `Milvus` 和 `Redis` 容器可正常启动并处于 healthy 状态
- GitHub CI 已经收口到当前真实门禁链 `offline regression + release acceptance`
- fresh eval 需要同时满足 `本地 embeddings 模型可用` 和 `外部 LLM key 可用`
- 当前仓库内新增了 `scripts/run_fresh_eval_with_current_env.py` 用于在不污染本项目 `.env` 的前提下 临时注入外部 `LLM` 配置做 fresh eval

## 测试覆盖率现状

- 2026-08-20 实测 (`make test-unit`, conda `agenticrag` 环境): 单测覆盖率 `90.24%` (706 个单测全过), 达到 `Makefile` `90%` 阈值
- 覆盖率口径说明: `pyproject.toml` `[tool.coverage.run]` 的 `omit` 排除了 `evaluation/*` 与 `cli/*` (分别由顶层集成测试和场景测试独立覆盖), 度量聚焦 RAG 检索/编排/代理/LLM 治理/可观测性/校验器
- 2026-08-20 修复了 `Makefile` `PYTEST` 定义的存量 bug: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 禁用插件后未显式加载 `pytest_cov`, 导致 `--cov` 参数从未被识别 (历史 "33%" 数据源于该 bug, 实际覆盖率远高于此)
- 历史低覆盖大缺口已补齐: `rag/remote_reranker.py` (0% -> 全覆盖, 新增 11 个测试), `artifacts/storage.py` bundle 分支 (73% -> 92%+)
- 存量技术债: 全仓 `ruff check` 尚有约 755 个历史告警 (之前因 `W503` 配置 parse error 从未跑通过), 其中约半数可 `--fix` 自动修复, 待专项治理
- 当前测试文件共 `55+` 个 覆盖 unit smoke scenario performance milestone acceptance 等多个层次

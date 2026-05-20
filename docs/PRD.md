# Product Requirements Document

## 一句话目标

把 `RiskAgent-AgenticRAG` 收敛成一个顶尖的高可信 RAG 项目.

## 本阶段约束

- 不做 tool use 主路径
- 不做任务完成度评估
- 不做多智能体协作
- 不扩展为通用工作流编排平台
- 只聚焦高可信检索 高可信生成 高可信评测

## 里程碑状态

- [x] Milestone 1. 纯 RAG 收敛
- [x] Milestone 2. 评测独立化
- [x] Milestone 3. 门禁与报告可信化
- [x] Milestone 4. 工程稳定化

## 任务 checklist

### Milestone 1. 纯 RAG 收敛

- [x] 从主流程移除 `decide_tool_use` 与 `call_tool`
  - 验收标准: 默认执行链路固定为 `rewrite -> retrieve_and_critique -> revise_query loop -> synthesize_answer -> validate_and_save`
  - 验收证据: `src/riskagent_agenticrag/orchestration/langgraph_runner.py` 中不再注册 tool 节点. `tests/test_milestone1_acceptance.py` 通过

- [x] 删除 API 主响应中的 `tool_traces`
  - 验收标准: public API 返回字段不再把 tool trace 作为主能力输出
  - 验收证据: `src/riskagent_agenticrag/api/schemas.py` 与 `src/riskagent_agenticrag/api/server.py` 更新. `tests/test_api_v1.py` 已同步更新

- [x] 收敛主链路生成逻辑为纯检索上下文生成
  - 验收标准: 主链路回答生成不再依赖 tool output
  - 验收证据: `src/riskagent_agenticrag/rag/agentic_primitives.py` 中主路径使用 `synthesize_answer()`

- [x] 更新仓库主文档定位
  - 验收标准: `README.md` `docs/ARCHITECTURE.md` `docs/PRD.md` 统一描述项目为高可信 RAG 系统
  - 验收证据: 文档搜索结果中不存在以 tool use 为主卖点的描述

### Milestone 2. 评测独立化

#### 2.1 qrels 数据集

- [x] 为现有评测集补齐 qrels
  - 验收标准: 每题至少有 1 个 gold chunk id. 支持一题多 relevant chunk
  - 验收证据: `tests/data/qrels.json` 已新增. `tests/test_evaluation_dataset.py` 与 `tests/test_milestone2_acceptance.py` 通过

- [x] 为数据集增加题型标签
  - 验收标准: 每题至少包含 1 个 `tags` 标签, 如 `definition` `compare` `numeric` `regulation`
  - 验收证据: `tests/data/questions.json` 已增加 `tags` 字段. 数据加载测试通过

- [x] 在 PRD 或 ARCHITECTURE 中补齐 qrels 标注约定
  - 验收标准: 明确 relevant 定义 chunk 粒度 边界样例 标注流程
  - 验收证据: 本 PRD 的 Milestone 2 checklist 已固定 qrels 和 tags 的数据口径. 示例样本可在 `tests/data/qrels.json` 复核

#### 2.2 retrieval eval

- [x] 用 qrels 重写 retrieval metrics
  - 验收标准: `retrieval_recall_at_k` `retrieval_mrr` `retrieval_ndcg_at_k` 全部基于 qrels 计算
  - 验收证据: `src/riskagent_agenticrag/evaluation/advanced_metrics.py` 已更新. `tests/test_advanced_metrics.py` 通过

- [x] 分离 retrieval metrics 与 citation diagnostics
  - 验收标准: 报告中 gold retrieval 指标与生成侧诊断指标分开输出
  - 验收证据: `src/riskagent_agenticrag/evaluation/run.py` 中 `retrieval_metrics` 已拆成 `gold_metrics` `slice_metrics` `citation_diagnostics`. `tests/test_evaluation_reporting.py` 通过

- [x] 增加 retrieval slice report
  - 验收标准: 报告支持按题型输出 recall mrr ndcg
  - 验收证据: `slice_metrics` 已进入 report 输出. `tests/test_milestone2_acceptance.py` 通过

### Milestone 3. 门禁与报告可信化

#### 3.1 answer eval

- [x] 规范核心回答指标
  - 验收标准: `citation_coverage` `faithfulness` `answer_relevancy` 有固定定义 固定计算方式 固定阈值
  - 验收证据: `src/riskagent_agenticrag/evaluation/answer_eval.py` 与 `config/eval_thresholds.json` 已提交. `tests/test_answer_eval.py` 通过

- [x] 增加句级支持结果
  - 验收标准: 每个样本都能下钻到 supported sentences 与 unsupported sentences
  - 验收证据: `src/riskagent_agenticrag/evaluation/citation_precision.py` 与 `src/riskagent_agenticrag/evaluation/run.py` 已输出句级字段. `tests/test_citation_precision.py` 通过

- [x] 保留金融专项指标并输出失败明细
  - 验收标准: `numeric_consistency` 与 `glossary_consistency` 除聚合分数外 还能输出样本级失败原因
  - 验收证据: `src/riskagent_agenticrag/evaluation/domain_consistency.py` 已输出 `numeric_failures` 与 `glossary_violations`. `tests/test_domain_consistency.py` 通过

#### 3.2 gate

- [x] 关闭正式评测中的 LLM appeal 覆盖逻辑
  - 验收标准: 正式评测模式下 gate failure 不会被 appeal 自动清空
  - 验收证据: `src/riskagent_agenticrag/orchestration/nodes.py` 现已默认关闭 appeal, 仅允许显式环境变量开启. `tests/test_milestone3_acceptance.py` 通过

- [x] 分离 threshold failure 与 baseline regression
  - 验收标准: 报告里两个概念独立展示 不共用一个字段
  - 验收证据: `src/riskagent_agenticrag/evaluation/reporting.py` 与 `src/riskagent_agenticrag/evaluation/thresholds.py` 已更新. `tests/test_threshold_gate.py` 与 `tests/test_evaluation_reporting.py` 通过

- [x] 将 gate benefit 与 false kill 改为基于标注样本计算
  - 验收标准: 不再只依赖 answer 空值与 citation 数
  - 验收证据: `tests/data/gate_labels.json` 已新增. `src/riskagent_agenticrag/evaluation/advanced_metrics.py` 已改为基于标注样本计算. `tests/test_advanced_metrics.py` 通过

#### 3.3 reports

- [x] 提交至少 1 组基准评测报告到仓库
  - 验收标准: 仓库内可直接查看基准 JSON 与 Markdown 报告
  - 验收证据: `.artifacts/reports/rag_eval_baseline_sample.json` 与 `.artifacts/reports/rag_eval_baseline_sample.md` 已提交

- [x] 把版本元信息写入每份报告
  - 验收标准: 报告包含 dataset version prompt version retrieval pipeline reranker model git commit
  - 验收证据: `src/riskagent_agenticrag/evaluation/run.py` 已写入 `dataset_version` `prompt_version` `retrieval_pipeline` `reranker_model` `git_commit`. 样例报告字段完整

- [x] 建立数字引用规范
  - 验收标准: README docs RESUME 中的关键数字都能映射到具体报告文件
  - 验收证据: `README.md` 已增加报告引用章节并绑定 `.artifacts/reports/rag_eval_baseline_sample.json` 与 `.md`

### Milestone 4. 工程稳定化

- [x] 锁定关键依赖并修复环境兼容问题
  - 验收标准: 新环境执行核心评测与核心测试时 不因 Milvus protobuf FastAPI pydantic 等依赖冲突失败
  - 验收证据: `pyproject.toml` `requirements-lock.txt` `environment.yml` 已更新. `bash scripts/run_offline_regression.sh` 通过

- [x] 增加纯离线回归入口
  - 验收标准: 在无在线 judge 条件下仍可跑完最小回归集
  - 验收证据: `scripts/run_offline_regression.sh` 已固定离线环境变量与最小回归集. 本地执行通过 45 项测试

- [x] 建立最小发布验收命令
  - 验收标准: 1 条命令完成 index eval report gate 的标准验收流程
  - 验收证据: `scripts/release_acceptance.sh` 与 `Makefile` 的 `accept-release` 已就绪. `bash scripts/release_acceptance.sh` 执行通过

## 发布验收口径

只有同时满足以下条件 才能认为本阶段完成:

- 默认主路径已经收敛为纯 RAG
- retrieval eval 已基于 qrels 独立计算
- answer eval 已支持句级证据分析
- threshold failure 与 baseline regression 已分离
- 仓库内已有可复核的基准报告
- 核心测试与最小验收命令稳定通过

## 最终交付物

- 纯 RAG 架构代码与文档
- qrels 标注数据集
- 独立 retrieval eval 模块
- 高可信 answer eval 模块
- 确定性 gate 模块
- 基准报告样例
- 一键验收命令
- 与报告绑定的 README 与简历表述

---

## 附录. 背景说明

### 项目定位

面向金融风控与衍生品知识问答的高可信 RAG 系统.
核心卖点是 `检索可信` `答案有证据` `评测可复现` `回归可审计`.

### 当前项目现状

#### 已有能力

- 已有完整的 LangGraph RAG 主流程, 包含 query rewrite retrieval critique revise synthesize validate artifact save
- 已有混合检索能力, 包含 Dense 检索 BM25 RRF Cross Encoder rerank
- 已有高级索引能力, 包含 Parent Child Summary HyDE
- 已有 Self RAG 风格的检索充足性判断与提前停止
- 已有 answer citations claims evidence_set decision_log trace artifact
- 已有离线评测入口, 支持 baseline diff threshold gate 与多种指标输出
- 已有 API CLI tests docs 等基本工程骨架

#### 当前主要问题

- 检索评测不够独立. 当前 retrieval metrics 仍存在 answer 自举偏差
- 数据集标注强度不够. 缺少稳定 qrels 与 slice 标签
- 门禁判定还不够硬. 当前还有 LLM appeal 覆盖失败结果
- 结果证据链不够完整. 仓库内缺少固定提交的评测报告样例
- 工程稳定性还不够顶尖. 缺少环境锁定与复现实验基线

### 目标状态

- 对外定位清晰. 这是一个顶尖 RAG 项目, 不是 Agent 平台
- 主链路清晰. 不依赖 tool use, 不依赖任务执行
- 检索评测独立. retrieval 有人工或半人工 gold qrels
- 生成评测可信. answer grounding 与 citation support 可单独复核
- 门禁稳定可审计. 失败结果不能被隐藏覆盖
- 报告可复现. 任意一次结论都能追溯到数据集 代码版本 配置 产物
- 回归可比较. 任意改动都能看到总体指标和 slice 指标变化

### 非目标

- 不做 tool use 主路径设计
- 不做任务完成率 task success 评估
- 不做 planner executor reviewer 等多智能体拆分
- 不做数据库操作型 agent
- 不做长流程业务编排

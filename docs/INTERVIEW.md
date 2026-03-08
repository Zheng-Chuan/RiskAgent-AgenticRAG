# INTERVIEW

本页只保留可直接复述的项目亮点和高频追问速答。

## 指标速答卡 Week16

- 对比口径
  - baseline: `.artifacts/reports/rag_eval_step1_real_20260127_072539.json`
  - final: `.artifacts/reports/rag_eval_step4_20260202_102949.json`
  - 数据集: `tests/data/questions.json` 共 20 题
- 关键可背指标
  - `domain_consistency_score`: `0.6234 -> 0.7606` `(+0.1372)`
  - `numeric_consistency_score`: `0.2468 -> 0.5212` `(+0.2744)`
  - `citations_coverage`: `1.0000 -> 1.0000` `(持平)`
- 追问应答
  - 为什么 `citation_precision` 下降: 这是跨阶段历史报告对比，口径与配置并非完全同构，最终上线以同口径重跑结果为准。
  - 如何阻断退化发布: 使用 `--enforce-thresholds` 和 `docs/eval_thresholds.yaml`，门禁失败返回非零退出码。

## 高频题速答

- Q1 多智能体方案的价值是什么  
  A: 把检索、生成、评审拆成独立职责，便于定位退化来源并做节点级治理。
- Q2 为什么强调引用是 contract  
  A: 回答必须可回溯到语料证据，否则无法用于工程排障与风险解释。
- Q3 如何定义有效引用  
  A: 引用必须能映射到真实 `source` 与片段位置，并支撑当前句结论。
- Q4 如何判断检索优化是否真实有效  
  A: 先看 `retrieval_recall_at_K` `retrieval_mrr` `retrieval_ndcg_at_K`，再看样本级失败分布是否收敛。
- Q5 门禁指标最核心看什么  
  A: 主要看 `gate_block_benefit_rate` 和 `gate_false_kill_rate`，目标是高收益低误杀。
- Q6 为什么需要阈值门禁  
  A: 把评测结果转成可执行发布规则，避免主观判断带来质量回退。
- Q7 如何解释性能与成本  
  A: 用 `latency_p95_ms` `latency_p99_ms` 说明尾时延，用 `cost_estimated_total_tokens` 与 `cost_estimated_usd` 说明成本。
- Q8 如何保证实验可复现  
  A: 固定数据集、固定评测命令、保留 baseline 报告并输出对比 diff。
- Q9 为什么要有 trace  
  A: trace 能定位失败节点、上下游输入输出和时延瓶颈，是排障主入口。
- Q10 线上问题优先排查顺序  
  A: 先看 `threshold_gate` 与 `baseline.diff`，再看 `samples.failure_reason`，最后下钻 trace。
- Q11 如何避免“看起来提升但不可上线”  
  A: 必须同口径对比并通过阈值门禁，单次离线提升不等于可发布。
- Q12 项目对业务方最直接的价值  
  A: 提供可验证、可解释、可回归的风险问答，不只给结论，还给证据与退化边界。

## 面试建议

- 讲结果时固定四步: 口径 -> 指标 -> 机制 -> 风险边界
- 讲优化时固定三步: baseline 问题 -> 改动策略 -> 指标变化
- 讲风险时主动补充: 哪些指标仍需同口径重跑确认

## 对应文档

- 指标定义与实验方案: [EVALUATION.md](./EVALUATION.md)
- 链路与架构: [ARCHITECTURE.md](./ARCHITECTURE.md)
- 排障与证据字段: [TRACE.md](./TRACE.md)

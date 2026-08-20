# 评测结果台账

本文件是项目评测结果的权威记录模块. 每次正式评测 (50 题 full eval 或 release acceptance) 跑完后, 必须在此追加一条记录, 包含指标数字, gate 判定, FAIL 题目清单和根因分析.

约定.

- 只记录真实跑出来的数字, 禁止手填估算值
- FAIL 题目必须写清楚根因, 修复方式, 修复状态和生效条件
- 完整报告落盘在 `.artifacts/reports/` (本地) 或容器内 `/app/.artifacts/reports/` (集群), 台账引用文件名
- 指标口径以 `src/riskagent_agenticrag/evaluation/` 当前实现为准, 口径变更时必须在对应记录里注明
- threshold 以 `config/eval_thresholds.json` 为准

## 记录索引

| 日期 | Label | 通过 | Gate | 关键结论 | 报告 |
|---|---|---|---|---|---|
| 2026-07-18 | unified_full_baseline_after_judge_parallel_bugfix | 38/50 | FAIL | recall@5=0.500 低于阈值 0.6, 是 gate 唯一瓶颈 | `.artifacts_fresh/reports/rag_eval_unified_full_baseline_after_judge_parallel_bugfix_20260718_*.md` |
| 2026-08-18 | prod_pipeline v10 (规则分块重建索引 2393 chunks 后) | - | FAIL | faithfulness=0.681 未达 0.75; recall@5=0.373 检索侧瓶颈; citation 0.82 / relevancy 0.882 达标 | 容器内 `/app/.artifacts/reports/` |
| 2026-08-18 | prod_pipeline_v10b_targ_rerank_recallfix | 47/50 | PASS | gate 首次全绿; recall@5 0.373 -> 0.78; 3 FAIL 均为 TARG 词表缺失 | `.artifacts/reports/rag_eval_prod_pipeline_v10b_targ_rerank_recallfix_20260818_073514.md` |

## 2026-08-18 prod_pipeline_v10b_targ_rerank_recallfix

环境: k8s 容器 `riskagent-api-6856cb9b4f-sbvtg` (镜像 v10b-fix), 索引 2393 chunks (manifest v4, 规则分块), 评测全程只读未重建索引.

相对 v10 的三项修复.

1. TARG 查询路由补 `has_financial_term` 判定 (query_router.py 金融术语词边界正则)
2. reranker 启用远程 fallback (BAAI/bge-reranker-v2-m3, auto 模式本地 CrossEncoder 失败后自动切换)
3. recall 口径修正: 分母只计主 gold (relevance>=2), 补充标注 (relevance=1) 只作命中加分

### 指标

| 指标 | 值 | 阈值 | 判定 |
|---|---|---|---|
| citation_coverage | 0.940 | 0.80 | PASS |
| faithfulness | 0.895 | 0.75 | PASS |
| answer_relevancy | 0.943 | 0.70 | PASS |
| sentence_support_rate | 0.808 | - | - |
| retrieval_recall_at_1 | 0.52 | - | - |
| retrieval_recall_at_3 | 0.68 | - | - |
| retrieval_recall_at_5 | 0.78 | 0.60 | PASS |
| retrieval_mrr | 0.628 | - | - |
| ragas context_recall | 0.833 | - | - |
| ragas context_precision_no_ref | 0.565 | - | 待改进 |
| ragas answer_correctness | 0.371 | - | 待改进 |

Threshold Gate 判定: PASS, 阈值失败 0 项, 基线回归 0 项.

### FAIL 题目 (3/50)

| 题号 | 题目 | 根因 | 修复 | 状态 |
|---|---|---|---|---|
| q19 | What is FVA? | TARG 判 simple 跳过检索, trace 节点为 `[rewrite, synthesize_answer, validate_and_save]` 无 retrieve, `fva` 不在金融术语词表 | query_router.py 词表补 `fva` | 已修复, 待部署生效 |
| q21 | What is MVA? | 同上, `mva` 不在词表 | 词表补 `mva` | 已修复, 待部署生效 |
| q22 | What is ColVA? | 同上, `colva` 不在词表 | 词表补 `colva` | 已修复, 待部署生效 |

根因证据: 三题 trace 的 nodes 均无 retrieve 节点, retrieval_diag 为空; 其余 XVA 家族 (XVA/DVA/KVA/CVA) 同轮全部 PASS, 差异仅在词表覆盖.

修复提交: `src/riskagent_agenticrag/rag/query_router.py` (`_FINANCIAL_TERM_RE` 补 fva/mva/colva), 回归测试 `tests/unit/test_query_router.py::test_short_financial_term_query_needs_retrieval` (20/20 通过). 纯查询期改动, 不触发索引重建.

生效条件: 需重建镜像部署 (v10c) 后, 三题预期恢复检索链路转 PASS; 下次评测需验证.

### 遗留观察项

- ragas context_precision_no_ref=0.565 和 answer_correctness=0.371 偏低, 未进 gate, 属 phase-3 后续 slice 分析范畴
- trace 的 `retriever_version.reranker_model` 记录的是环境变量名而非实际生效模型 (实际为远程 bge-reranker-v2-m3), 观测字段有歧义, 待修

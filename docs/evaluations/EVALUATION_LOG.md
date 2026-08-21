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
| 2026-08-20 | prod_pipeline_v10c_fva_mva_colva_fix | 3/3 | PASS | v10b 的 3 个 FAIL 复跑全部转 PASS; 只跑 FAIL 子集未重建索引 | 容器内 `/app/.artifacts/reports/rag_eval_prod_pipeline_v10c_fva_mva_colva_fix_20260820_103543.md` |
| 2026-08-21 | prod_pipeline_v10d_full_reeval | 50/50 | PASS | 全量 50/50 首次达成; recall@5 0.78 -> 0.82; citation 0.940 -> 1.000; 评测只读未重建索引 | `.artifacts/reports/rag_eval_prod_pipeline_v10d_full_reeval_20260821_141306.md` |

## 2026-08-21 prod_pipeline_v10d_full_reeval (50 题全量复评, 发布闭环)

背景: v10c 只复跑了 v10b 的 3 个 FAIL 题, 全量 50/50 一直是预期未验证. v10d-fix 镜像在 v10c 词表修复之上合入三项工程改动: (1) schema fingerprint 拆分为索引期/查询期两段, 查询开关 (reranker/self_rag 等) 不再触发全量索引重建; (2) 报告 `inputs` 新增 `resolved_reranker_model`/`resolved_reranker_status` 字段, 记录实际生效的 reranker 而非环境变量名; (3) ruff 存量 348 项风格修复 (纯代码卫生, 不改行为). 本次全量复评一并验证 50/50, 只读索引行为和新报告字段.

环境: k8s 容器 `riskagent-api-868bb4d479-lmwnm` (镜像 v10d-fix), 索引 2393 chunks (manifest v4, 规则分块), 评测全程只读未重建索引 (未带 `--reindex`).

### 指标

| 指标 | v10d | v10b (上次全量) | 阈值 | 判定 |
|---|---|---|---|---|
| citation_coverage | 1.000 | 0.940 | 0.80 | PASS |
| faithfulness | 0.903 | 0.895 | 0.75 | PASS |
| answer_relevancy | 0.928 | 0.943 | 0.70 | PASS |
| sentence_support_rate | 0.829 | 0.808 | - | - |
| retrieval_recall_at_1 | 0.60 | 0.52 | - | - |
| retrieval_recall_at_3 | 0.74 | 0.68 | - | - |
| retrieval_recall_at_5 | 0.82 | 0.78 | 0.60 | PASS |
| retrieval_mrr | 0.69 | 0.628 | - | - |
| ragas context_recall | 0.907 | 0.833 | - | - |
| ragas context_precision_no_ref | 0.543 | 0.565 | - | 待改进 |
| ragas answer_correctness | 0.328 | 0.371 | - | 待改进 |

Threshold Gate 判定: PASS, 阈值失败 0 项, 基线回归 0 项. 题目级 50/50 全部 PASS, 无 FAIL 根因待分析.

### 新报告字段验证

- `inputs.index_schema_fingerprint` = `7b2759665276aaaeff3989473f010381c47d0886`: 首次随报告落盘, 作为后续评测对比基线; 本次评测前后索引指纹一致, 证实只读行为
- `inputs.resolved_reranker_model` = `BAAI/bge-reranker-v2-m3`, `resolved_reranker_status` = `remote_enabled`: 实际生效模型与配置值 (`cross-encoder/ms-marco-MiniLM-L-6-v2`, 本地不可用后 auto fallback) 区分记录, v10b 遗留的 "trace 记环境变量名" 问题闭环

### 结论

v10b 的 3 个 FAIL (TARG 词表缺失) 在全量口径下确认修复, 全量 50/50 首次达成. release acceptance 以本报告重跑通过 (answer_eval ok / gold_metrics 存在 / gate verdict pass), 发布闭环完成. ragas context_precision_no_ref 与 answer_correctness 仍偏低, 未进 gate, 维持 phase-3 后续 slice 分析范畴.

## 2026-08-20 prod_pipeline_v10c_fva_mva_colva_fix (FAIL 子集复跑)

背景: v10b 评测中 q19/q21/q22 三题因 TARG 词表缺失被判 simple 跳过检索. 修复 (词表补 fva/mva/colva) 已随 v10c-fix 镜像部署到 k8s, 本次只复跑这 3 题, 未跑全量, 未重建索引 (manifest v4 只读).

环境: k8s 容器 `riskagent-api-7d7d4cdb88-9lwwm` (镜像 v10c-fix), 数据集为 3 题子集 (`/app/eval_subset/questions.json` + 同级 `qrels.json`).

### 结果

| 题号 | 题目 | 结果 | 检索链路证据 |
|---|---|---|---|
| q19 | What is FVA? | PASS | nodes 含 retrieve_and_critique, 检回 8 docs, top1 source=`corpus/regulatory_seed/md/en/wikipedia_xva.md` (rerank 0.623) |
| q21 | What is MVA? | PASS | nodes 含 retrieve_and_critique |
| q22 | What is ColVA? | PASS | nodes 含 retrieve_and_critique |

子集指标 (仅 3 题, 不代表全量): retrieval_mrr=0.333, recall@5=0.333. 题目级判定以 answer_eval PASS 为准, 全量口径仍以 v10b 报告为准.

注: 本次 ragas judge 出现 API 噪声 (部分 job 报 `n should not greater than 1` 400 错误和超时), ragas 聚合指标为空, 不影响题目级 PASS 判定. 该 judge 稳定性问题已列入观察项.

结论: v10b 的 3 个 FAIL 全部闭环, 修复链路 = 词表补全 -> v10c-fix 镜像 -> 检索链路恢复 -> 题目转 PASS. 全量 50 题预期 50/50, 待下次全量评测确认.

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
- ~~trace 的 `retriever_version.reranker_model` 记录的是环境变量名而非实际生效模型~~ 已修复 (2026-08-20): 检索节点将 `active_reranker_model` 透传 state, trace/retriever_version 与 retrieval_diag 均记录实际生效模型, simple 直答回退环境变量; 需随下次镜像部署后在容器内生效

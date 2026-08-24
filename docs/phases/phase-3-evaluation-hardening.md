# Phase 3 Evaluation Hardening

## 目标

把 retrieval generation gate 三层评测口径继续做硬.

## 时间

2-3 周

## 本阶段重点

- retrieval metrics 和 citation diagnostics 继续拆清楚
- answer eval 和 domain consistency 继续固定口径
- gate 指标继续基于标注样本做统计
- 报告元信息继续完善到可复现级别

## 当前已落地

- retrieval metrics answer metrics gate metrics 已经分层输出
- 报告已经包含 `dataset_version` `retrieval_pipeline` `reranker_model` `prompt_version` `git_commit`
- threshold gate 和 baseline regression 已经分离展示
- release acceptance 已能校验报告结构和阈值门禁的最小闭环
- 已经新增一条外部 `LLM` 注入脚本 可在不改本项目 `.env` 的情况下运行 fresh eval
- 已生成 `5` 题 smoke fresh report 证明当前统一主链和外部 `LLM` 配置可以真实跑通
- 已正式生成 `50` 题 full baseline fresh report
- 2026-07-18 full baseline 关键结果为 `passed=38/50` `citation_coverage=0.960` `faithfulness=0.775` `answer_relevancy=0.848` `retrieval_recall_at_5=0.500`
- 2026-08-18 `prod_pipeline_v10b_targ_rerank_recallfix` 报告实现 threshold gate 首次全绿 PASS: `passed=47/50` `faithfulness=0.895` `citation_coverage=0.940` `answer_relevancy=0.943` `retrieval_recall_at_5=0.78` (详见 [评测台账](../evaluations/EVALUATION_LOG.md))
- 2026-08-20 v10c FAIL 子集复跑 `3/3` 全 PASS (q19 FVA / q21 MVA / q22 ColVA, TARG 词表补全后检索链路恢复)
- recall 口径已修正: 分母只计主 gold (relevance>=2), 与 IR 惯例对齐
- 评测已默认只读索引 重建需显式 `--reindex`, 评测和索引工作流已分离
- 评测结果台账模块已建立 (`docs/evaluations/EVALUATION_LOG.md`) 历次评测 FAIL 根因可回溯
- 2026-08-20 报告元信息已补 `index_schema_version` `index_schema_fingerprint` (只读 manifest, 不触发索引操作); 同日完成 schema fingerprint 拆分: 查询期 features (retrieval_pipeline/prompt_version/query_intel/self_rag) 移出 mismatch 比较范围, 改开关不再触发全量重建, 老 manifest 平滑迁移无需重建 (生产 manifest 已验证)

## 当前仍未完成

- gate_labels 样本量仍然偏小 统计显著性有限
- ragas 副指标 `context_precision_no_ref=0.543` `answer_correctness=0.328` 偏低 (v10d 口径) 未进 gate 属 slice 分析范畴
- ragas judge 偶发 API 噪声 (400 `n should not greater than 1` 与超时), judge 稳定性待加固

(2026-08-21 更新: v10d 全量复评 50/50 已执行, release acceptance 已用 v10d 报告重跑通过, 两项收尾完成, 详见 [评测台账](../evaluations/EVALUATION_LOG.md))

## P0 必须先做

### 1. retrieval eval 单位继续做硬

- 把 retrieval 指标和 evidence unit 继续对齐
- 明确 qrels 命中规则和边界
- 让 retrieval report 更能指导召回优化

### 2. metrics 分层继续做清楚

- retrieval metrics
- answer metrics
- gate metrics

这三层必须继续独立展示  
避免一个总分掩盖问题来源

### 3. 报告元信息补全

- dataset version
- retrieval pipeline version
- reranker model
- index version
- prompt version

确保任何一次报告都可以回溯配置上下文

### 4. gate 样本继续扩充

- refusal
- evidence mismatch
- numeric mismatch

让 gate benefit false kill miss rate 更有统计意义

## P1 随后做

### 5. 题型 slice 报告强化

- definition
- compare
- numeric
- regulation

按题型稳定输出 retrieval 和 answer 两层 slice 结果

### 6. retrieval cost latency 指标

- fanout 数量
- rerank pairs
- node latency
- estimated tokens

让召回优化不脱离成本视角

### 7. 数值题专项评测

- 更细地统计 numeric consistency
- 继续增强金融术语和数值口径的失败明细

## 建议交付

- 更强的数据集字段定义
- 更可信的基准报告
- 更清晰的阈值门禁和 regression 展示
- 更细的 slice 指标和运行成本指标

## 验收标准

- 评测报告可以直接支持发布判断
- 指标变化能定位到 retrieval 或 generation 或 gate
- 关键数字都能反查到具体报告

## 不做什么

- 不把评测重新退化成单一主观 LLM 分数
- 不让 demo 表现替代报告口径
- 不把 retrieval 和 generation 指标混成一个总分

## 退出标准

- 报告已经可以直接支持 release gate
- 关键题型的 retrieval 和 answer 指标都能单独下钻
- gate 样本统计不再过于单薄
- 后续任何 retrieval 改动都能被更可靠地评估

## 状态

In Progress (2026-08-20 更新: threshold gate 已在 v10b 首次全绿, v10c 后全量复评与 release acceptance 重跑为剩余收尾项)

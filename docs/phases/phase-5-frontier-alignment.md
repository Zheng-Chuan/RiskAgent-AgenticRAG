# Phase 5 Frontier Alignment

## 目标

对照 2025-2026 学术界和工业界 RAG 实践, 把 [RFC-006](../decisions/RFC-006-frontier-gap-closing-roadmap.md) 收窄后的四个差距 (统计置信区间 / 长上下文基线 / PDF 表格解析 / Contextual Retrieval 变体) 做硬.

四项均不动生产主链.

## 时间

2-3 周

## 本阶段重点

- 关键指标补 bootstrap 95% CI, gate 判定接入置信区间
- 补长上下文基线实验, 回答 "为什么不全量塞进上下文"
- PDF 表格感知解析入索引
- Contextual Retrieval 两变体 A/B, 给 RFC-003 一个完整判决

## 当前已落地

- (2026-10-18) A2 bootstrap 置信区间: `evaluation/advanced_metrics.py` 新增 `bootstrap_mean_ci` / `compute_confidence_intervals` (1000 次重采样, seed 固定可复现), 评测报告新增 `confidence_intervals` 节, threshold gate 用保守边界判定 (higher_is_better 用 `ci_low`, lower_is_better 用 `ci_high`), 可经配置 `use_confidence_intervals: false` 关闭; 单测 `tests/test_confidence_intervals.py`
- (2026-10-18) B 长上下文基线实验框架: 新增 `evaluation/baseline_long_context.py` 两模式 (`parent_stuffing` / `rag_main`) 统一指标对比 (faithfulness / answer_relevancy / numeric_consistency / refusal 率 / latency p50 p95 / token 成本, 均带 bootstrap CI), 报告落 `docs/evaluations/`; 入口 `make eval-long-context`; 小样本实验已完成 (见 `docs/evaluations/long_context_baseline_20261018_111636.md`): rag_main 全面优于 parent_stuffing (faithfulness 1.0 vs 0.43, context_precision 0.79 vs 0.56, 成本 1.1k vs 17.7k tokens/题), 实证长上下文塞窗不可替代检索主链. (曾设计 map_reduce_full 全量知识模式, 实测每题约 2.9h 不可行, 已移除)
- (2026-10-18) C2 Contextual Retrieval 变体落地: 变体一 `llm_brief` (BM25 侧注入, brief 生成与 embedding 注入解耦) 与变体二 `short_brief` (title+section_path 短 brief, 无需重建索引), 开关 `RISKAGENT_CONTEXTUAL_BM25_MODE`; A/B 入口 `make eval-contextual-ab`; A/B 已跑完 (off vs short_brief, 同索引 50 题): short_brief 使 context_precision 0.147→0.266 (+81%)、faithfulness +0.014, 检索层 recall@5/MRR 小幅回落但 CI 重叠不显著; 定位为"以轻微检索代价换上下文精度"的可选变体, 生产默认保持 off, 详见 [EVALUATION_LOG](../evaluations/EVALUATION_LOG.md)
- (2026-10-18) C1 PDF 表格感知解析落地: `source_loader` 用 pdfplumber 提取表格转 markdown 独立 chunk (`chunk_type=table`, 误检过滤: >=2 行 2 列且 >=4 非空单元格), `ingestion.split_documents` 表格 chunk 不切割且豁免参考文献 junk 启发式; Milvus schema +`chunk_type` 字段 (MANIFEST_VERSION 4->5), chunking fingerprint +`pdf_tables` 开关与 policy_version v2 (开启默认触发全量重建); d457/d488 实测可提取真实监管表格; 索引已重建 (2498 chunks 含 107 表格); 单测 `tests/test_pdf_table_parsing.py`. 全量评测归因受限: 基线为 LLM 分块而新索引为规则分块, 回归主要来自分块切换; 且 50 题 qrels 无表格标注, 表格检索收益需补表格类问题后才能度量

## P0 必须先做

### 1. bootstrap 置信区间 (A2)

- `evaluation/advanced_metrics.py` 加 bootstrap 重采样 (1000 次), 关键指标输出 95% CI
- 报告 metrics 带 `ci_low` / `ci_high`, threshold gate 判定接入 CI 口径
- 落点: `evaluation/advanced_metrics.py` `evaluation/reporting.py` `evaluation/thresholds.py`

### 2. 长上下文基线 (B)

- 新增 `evaluation/baseline_long_context.py`, 两模式对比:
  - `parent_stuffing`: parent corpus 塞满 128k 窗口
  - `rag_main`: 现有统一主链对照
- 同一题集同一 judge: faithfulness / answer_relevancy / numeric_consistency / refusal 正确率 / latency p50 p95 / token 成本
- 产出报告落盘 `docs/evaluations/`, 结论 ADR 化

## P1 随后做

### 3. PDF 表格感知解析 (C1)

- pdfplumber 提取 d457 / d488 等监管 PDF 表格, 转 markdown 表格独立 chunk (`chunk_type=table`)
- chunking `policy_version` 升级触发全量重建 (schema fingerprint 机制已有)
- 验收: 表格 chunk 的检索层命中对比 (dense/sparse), 或新增少量表格题进题集做 before/after

### 4. Contextual Retrieval 变体重试 (C2)

- 变体一: 只对 BM25 侧注入 brief, 不动 embedding (规避已实证的术语稀释)
- 变体二: 短 brief (title + section_path, 约 30 token)
- 复用 `settings.features.contextual_briefs` flag, 用现有 50 题评测集 A/B; 无收益关闭并回写 [RFC-003](../decisions/RFC-003-contextual-retrieval.md)
- 已知限制: 50 题以 definition 类为主, 结论对 compare/numeric 题型的外推有限, 记录时注明

## 建议交付

- 带 95% CI 的评测报告与 gate 口径
- 长上下文基线对比报告与 ADR
- 表格感知索引与表格召回对比结果
- Contextual Retrieval 变体 A/B 结论 (RFC-003 回写)

## 验收标准

- 任何指标变化能回答 "是否在置信区间内"
- 长上下文基线结论可复现 (报告元信息齐备)
- 表格 chunk 入索引且召回对比完成
- RFC-003 有明确的开/关终态
- 所有结论可在 [评测台账](../evaluations/EVALUATION_LOG.md) 反查

## 不做什么

- 不做评测集扩充 / judge 校准 / 外部基准 / GraphRAG (2026-10-18 范围调整, 见 [RFC-006](../decisions/RFC-006-frontier-gap-closing-roadmap.md))
- 不做 web search fallback (closed-domain 边界)
- 不做在线反馈闭环 / 语义缓存 / 安全鲁棒性 (生产化范畴, 边界外)
- 不做中文分词改造 (语料全英文)
- 不动生产检索主链形态

## 退出标准

- CI 口径进入常规评测报告与 gate
- 长上下文基线给出明确架构结论
- 表格解析与 contextual 变体均有可反查的落地/关闭结论
- 文档口径 (PRD STRATEGY) 与新口径同步

## 状态

Done (2026-10-06 立项, 2026-10-18 四项全部收口: A2 完成; B 两模式结论落地 (rag_main 胜出, map_reduce_full 因成本移除); C2 A/B 完成, 生产保持 off; C1 代码+索引落地, 收益度量待表格类问题入题集)

# Phase 5 Frontier Alignment

## 目标

对照 2025-2026 学术界和工业界 RAG 实践, 把 [RFC-006](../decisions/RFC-006-frontier-gap-closing-roadmap.md) 审计发现的四个差距 (评测学 / 长上下文基线 / 语料索引工程 / 架构覆盖) 做硬.

核心判断: 瓶颈不在检索算法, 在评测能力. 先把评测做硬, 再让技术决策可验证.

## 时间

4-6 周

## 本阶段重点

- 评测集 50 -> 200 题, 补齐多跳 / 聚合 / 不可回答题型
- 关键指标补 bootstrap 95% CI, gate 判定接入置信区间
- 补长上下文基线实验, 回答 "为什么不全量塞进上下文"
- PDF 表格感知解析与 Contextual Retrieval 变体重试
- 外部基准 (FinanceBench) 检索层锚定

## 当前已落地

(无, 计划态; 本阶段于 2026-10-06 立项, 方案见 [RFC-006](../decisions/RFC-006-frontier-gap-closing-roadmap.md))

## P0 必须先做

### 1. 评测集扩展 (A1)

- 现有 50 题原样保留, dataset_version 升 v2
- 新增 150 题: compare 跨文档 30 / multi-hop 聚合 40 / numeric 含表格 30 / unanswerable 20 / definition 及其他 30
- 多 gold qrels: multi-hop 题按题内 gold 集合计算 recall@k, 不再单 gold
- unanswerable 题验收 refusal gate 正确拒答率, 复用 `week5_refusal_set.json` 机制
- 合成流程: LLM 生成 -> chunk_id 级 qrels 自动对齐 -> 人工审核 -> allowlist 白名单守口径
- 落点: `tests/data/questions.json` `tests/data/qrels.json` `evaluation/dataset.py`

### 2. bootstrap 置信区间 (A2)

- `evaluation/advanced_metrics.py` 加 bootstrap 重采样 (1000 次), 关键指标输出 95% CI
- 报告 metrics 带 `ci_low` / `ci_high`, threshold gate 判定接入 CI 口径
- 落点: `evaluation/advanced_metrics.py` `evaluation/reporting.py` `evaluation/thresholds.py`

### 3. 长上下文基线 (B)

- 新增 `evaluation/baseline_long_context.py`, 三模式对比:
  - `map_reduce_full`: 全语料 (约 2M tokens) 分段摘要后作答
  - `parent_stuffing`: parent corpus 塞满 128k 窗口
  - `rag_main`: 现有统一主链对照
- 同一题集同一 judge: faithfulness / answer_relevancy / numeric_consistency / refusal 正确率 / latency p50 p95 / token 成本
- 产出报告落盘 `docs/evaluations/`, 结论 ADR 化

## P1 随后做

### 4. judge 校准 (A3)

- ragas judge 结果抽样约 50 条人工标注, 报告 Cohen's kappa >= 0.6
- 不达标修 judge prompt 复测, 结果记入 [评测台账](../evaluations/EVALUATION_LOG.md)

### 5. PDF 表格感知解析 (C1)

- pdfplumber 提取 d457 / d488 等监管 PDF 表格, 转 markdown 表格独立 chunk (`chunk_type=table`)
- chunking `policy_version` 升级触发全量重建 (schema fingerprint 机制已有)
- 验收: 表格题 slice 的 gold recall@5 不低于 textual gold 水平

### 6. Contextual Retrieval 变体重试 (C2)

- 变体一: 只对 BM25 侧注入 brief, 不动 embedding (规避已实证的术语稀释)
- 变体二: 短 brief (title + section_path, 约 30 token)
- 复用 `settings.features.contextual_briefs` flag, 用扩展后评测集 A/B; 无收益关闭并回写 [RFC-003](../decisions/RFC-003-contextual-retrieval.md)

### 7. 外部基准锚定 (D1)

- FinanceBench 公开子集 (约 50 题) 跑 dense / sparse / hybrid 检索层对比
- 产出横向定位报告; 只做检索层, 不做端到端接入, 不进发布门禁

## P2 视情况做

### 8. GraphRAG 轻量 PoC (D2)

- 依赖 P0-1 的多跳题先落盘
- LLM 抽取实体关系 (机构 / 文档 / 条款 / 指标) 建轻量图, 对比图检索与 hybrid 在多跳题上的 gold 命中
- 无显著收益记录 ADR 后关闭, 不引入生产主链

## 建议交付

- 200 题以上带 chunk_id 级 qrels 的评测数据集 (dataset_version v2)
- 带 95% CI 的评测报告与 gate 口径
- 长上下文基线对比报告与 ADR
- 表格感知索引与表格题 slice 指标
- judge 校准记录与外部基准定位报告

## 验收标准

- 多跳 / 聚合 / 不可回答题型的 retrieval 和 answer 指标能单独下钻
- 任何指标变化能回答 "是否在置信区间内"
- 长上下文基线结论可复现 (报告元信息齐备)
- threshold gate 在 200 题口径下重校准并通过
- 所有结论可在 [评测台账](../evaluations/EVALUATION_LOG.md) 反查

## 不做什么

- 不做 web search fallback (closed-domain 决策已在 [RFC-006](../decisions/RFC-006-frontier-gap-closing-roadmap.md) D3 显式记录)
- 不做在线反馈闭环 / 语义缓存 / 安全鲁棒性 (生产化范畴, 边界外)
- 不做中文分词改造 (语料全英文)
- 不动生产检索主链形态
- 不以外部基准分数为发布门禁

## 退出标准

- 评测集和 CI 口径能支撑下一轮技术决策 (GraphRAG / Agentic 迁移 / RAPTOR 类方向可重新评估)
- 长上下文基线给出明确架构结论
- 表格题与 judge 校准达标
- 文档口径 (PRD STRATEGY ARCHITECTURE) 与新评测口径同步

## 状态

Planned (2026-10-06 立项, 方案见 [RFC-006](../decisions/RFC-006-frontier-gap-closing-roadmap.md))

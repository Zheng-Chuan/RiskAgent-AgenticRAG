# RFC-006 Frontier Gap-Closing Roadmap

## 状态

Proposed (2026-10-06): 业界前沿对齐审计后立项; 2026-10-18 范围收窄至 A2/B/C1/C2 四项 (范围调整记录见下). 执行跟踪见 [phase-5-frontier-alignment](../phases/phase-5-frontier-alignment.md).

## 目标

对照 2025-2026 学术界和工业界 RAG 实践与评测标准, 把审计发现的四个高性价比差距做硬.

- A2 统计置信区间: 关键指标点估计无置信区间, 无法回答 "指标变化是否在噪声区间"
- B 长上下文基线: 缺少与 RAG 竞争的 long-context 基线, 检索栈的必要性论证不完整
- C1 PDF 表格解析: 监管 PDF 的表格结构在索引时丢失, 数值条款类问题召回受损
- C2 Contextual Retrieval 变体: RFC-003 只验证了 embedding 单侧注入就关闭, BM25 侧与短 brief 变体未测

四项均为不动生产主链的实验与工程加固.

## 背景 (2026-10 前沿对齐审计)

### 审计结论概览 (收窄后范围)

| 维度 | 项目现状 (2026-10-06) | 业界 2025-2026 参考 | 差距 |
|---|---|---|---|
| 统计显著性 | 点估计, 无置信区间 | bootstrap CI / 显著性检验为标配 | A2 |
| 长上下文基线 | 未做 | 1M token 级模型下 RAG vs stuffing 对比是 2026 年必答实验 | B |
| PDF 表格解析 | page 级 parent, 表格结构丢失 | 表格感知解析为金融监管语料标配 | C1 |
| Contextual Retrieval | embedding 侧注入失败即关闭 | Anthropic 67% 收益来自 embedding + BM25 双侧注入 | C2 |

### 审计中修正的两个旧判断

- C1 的结构感知分块不是差距: `ingestion.py` 的 `_markdown_sections` 已做 heading 感知切分, 且默认走 `llm_semantic_split_document` 语义切割. 真实差距集中在 PDF 侧 (表格 + 无结构 page 级切分).
- 检索主链不落后: Hybrid + RRF + Cross-Encoder rerank 是 2026 年工业标准形态; CRAG/TARG/SEAL-RAG 落地密度高于多数生产系统. 本 RFC 不动主链.

### 范围调整记录 (2026-10-18)

立项时审计还发现四项差距: 评测集扩充 (50->200 题, 多跳/不可回答题型) / judge 人工校准 / 外部基准锚定 (FinanceBench) / GraphRAG PoC. 经评估移出本轮范围:

- 评测集扩充与 judge 校准: 投入大 (合成+人工审核), 且现有 50 题回归口径刚稳定, 暂不扩
- 外部基准锚定与 GraphRAG: 依赖更硬的评测集先行, 顺延

如后续重开, 另立 RFC.

## 提案范围

### A2 统计显著性: bootstrap 置信区间 (P0)

- `evaluation/advanced_metrics.py` 增加 bootstrap 重采样 (1000 次), 关键指标输出 95% CI
- 报告 metrics 带 `ci_low` / `ci_high`; threshold gate 判定接入 CI 口径 (tolerance 机制已有)
- 直接回答 "faithfulness 0.903 -> 0.982 是否在噪声区间" 这类问题
- 落点: `evaluation/advanced_metrics.py` `evaluation/reporting.py` `evaluation/thresholds.py`

### B 长上下文基线 (P0, 一次性实验)

语料 8.1MB 约 2M tokens, 在 128k context 的 DeepSeek-V3 下必须回答 "为什么不全量塞进上下文".

- 新增 `evaluation/baseline_long_context.py`, 两种模式同一题集同一 judge 对比:
  - `parent_stuffing`: parent corpus 按相关性塞满 128k 窗口 (RAG 的最强朴素变体)
  - `rag_main`: 现有统一检索主链 (对照)
  - (曾设计 `map_reduce_full` 全量知识模式, 实测每题需遍历 577 段约 2.9h, 于 2026-10-18 移除)
- 统一指标: faithfulness / answer_relevancy / numeric_consistency / refusal 正确率 / latency p50 p95 / token 成本
- 产出: 基线对比报告落盘 `docs/evaluations/`, 结论 ADR 化 (是否纳入每期评测对照列)

### C1 PDF 表格感知解析 (P1)

- 用 pdfplumber 为 d457 / d488 等监管 PDF 提取表格, 转为 markdown 表格独立 chunk (`chunk_type=table`)
- chunking `policy_version` 升级触发全量重建 (schema fingerprint 机制已有)
- 验收: 选取有表格 gold 的题目做 before/after 对比, 表格来源 gold 的召回不低于 textual gold 水平
- 注意: 现有 50 题评测集不含表格题, 验收通过检索层对比 (dense/sparse 命中表格 chunk) 或新增少量表格题进题集完成

### C2 Contextual Retrieval 变体重试 (P1, RFC-003 遗留)

- 变体一: 只对 BM25 侧注入 context brief, 不动 embedding (规避已实证的术语稀释)
- 变体二: 短 brief (title + section_path, 约 30 token) 替代文档级摘要
- feature flag `settings.features.contextual_briefs` 已有, 用现有 50 题评测集 A/B; 无收益则关闭并回写 [RFC-003](./RFC-003-contextual-retrieval.md)
- 已知限制: 50 题以 definition 类为主, A/B 结论对 compare/numeric 题型的外推有限, 结论记录时需注明

## 优先级与顺序

| 优先级 | 条目 | 理由 |
|---|---|---|
| P0 | A2 bootstrap CI | 所有后续指标结论必须带置信度 |
| P0 | B 长上下文基线 | 一次性实验, 决定架构叙事方向 |
| P1 | C1 表格解析 | 金融语料收益最直接 |
| P1 | C2 contextual 变体 | RFC-003 遗留, flag 已有成本低 |

预期总周期 2-3 周.

## 不做什么

- 不做评测集扩充 / judge 校准 / 外部基准 / GraphRAG (2026-10-18 范围调整, 见上)
- 不做 web search fallback (closed-domain 边界, 语料外问题由 refusal gate 拒答)
- 不做在线反馈闭环 / 语义缓存 / prompt injection 防护 (生产化范畴, 边界外)
- 不做中文分词改造 (语料全英文)
- 不动生产检索主链形态 (Hybrid + Query Intelligence + Advanced Index + CRAG/TARG/SEAL)

## 成功标志

- 关键指标全部带 95% CI, threshold gate 判定考虑置信区间
- 长上下文基线报告落盘并有 ADR 结论
- PDF 表格以独立 chunk 入索引, 表格召回对比完成
- Contextual Retrieval 两变体 A/B 有明确开/关结论并回写 RFC-003
- 上述结论均可在 [EVALUATION_LOG](../evaluations/EVALUATION_LOG.md) 反查

## 关联文档

- [RFC-001](./RFC-001-retrieval-hardening-roadmap.md) - 第一轮检索强化 (已收口), 本 RFC 是第二轮
- [RFC-003](./RFC-003-contextual-retrieval.md) - C2 变体重试的上游决策
- [phase-5-frontier-alignment](../phases/phase-5-frontier-alignment.md) - 执行跟踪
- [EVALUATION_LOG](../evaluations/EVALUATION_LOG.md) - 评测台账

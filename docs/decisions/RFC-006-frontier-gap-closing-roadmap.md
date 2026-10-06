# RFC-006 Frontier Gap-Closing Roadmap

## 状态

Proposed (2026-10-06): 业界前沿对齐审计后立项, 执行跟踪见 [phase-5-frontier-alignment](../phases/phase-5-frontier-alignment.md).

## 目标

对照 2025-2026 学术界和工业界 RAG 实践与评测标准, 把审计发现的四个系统性差距做硬.

- A 评测学: 评测集规模与题型无法支撑技术决策, 是其余差距的根因
- B 长上下文基线: 缺少与 RAG 竞争的 long-context 基线, 检索栈的必要性论证不完整
- C 语料与索引工程: PDF 表格结构丢失, Contextual Retrieval 只验证了 embedding 单侧就关闭
- D 架构覆盖面: 无外部基准锚定, GraphRAG 未评估, CRAG web fallback 偏差未记录

第一轮 (RFC-001) 已把 CRAG / TARG / SEAL-RAG 落到工业领先水平.
本轮的核心判断是: 下一步的瓶颈不在检索算法, 在评测能力.
评测集 50 题 (46 题 definition 类, 0 道多跳题) 决定了 RAPTOR 与 Agentic 迁移这类决策 "收益无法验证" (见 [RFC-004](./RFC-004-agentic-rag-paradigm.md)) -- 语料里天然存在 BCBS d457 与 d488 两代框架对比、BCBS/IOSCO/CFTC 跨机构口径对比的素材, 但评测集没有能触发这些能力的题型.
先把评测做硬, 再让后续技术决策可验证.

## 背景 (2026-10 前沿对齐审计)

### 审计结论概览

| 维度 | 项目现状 (2026-10-06) | 业界 2025-2026 参考 | 差距 |
|---|---|---|---|
| 评测集规模与题型 | 50 题, 46 definition, 4 compare, 0 multi-hop, 0 unanswerable | FRAMES 800+ 多跳题; 企业实践普遍数百到千级, LLM 合成持续扩充 | A1 |
| 统计显著性 | 点估计, 无置信区间 | bootstrap CI / 显著性检验为标配 | A2 |
| judge 校准 | LLM-as-judge 无人工一致性校准 | judge 与人工标注 kappa 校准 | A3 |
| 长上下文基线 | 未做 | 1M token 级模型下 RAG vs stuffing 对比是 2026 年必答实验 | B |
| PDF 表格解析 | page 级 parent, 表格结构丢失 | 表格感知解析为金融监管语料标配 | C1 |
| Contextual Retrieval | embedding 侧注入失败即关闭 | Anthropic 67% 收益来自 embedding + BM25 双侧注入 | C2 |
| 外部基准锚定 | 仅私有 50 题自洽 | BEIR / FinanceBench 等公共基准横向定位 | D1 |
| GraphRAG | 未评估 (RAPTOR 以 "无宏观题型" 取消) | 合规领域是 GraphRAG 真实落地场景 | D2 |
| CRAG web fallback | 未实现且未记录决策 | CRAG 原论文核心闭环含 web search 兜底 | D3 |

### 审计中修正的两个旧判断

- C2 结构感知分块不是差距: `ingestion.py` 的 `_markdown_sections` 已做 heading 感知切分, 且默认走 `llm_semantic_split_document` 语义切割. 真实差距集中在 PDF 侧 (表格 + 无结构 page 级切分).
- 检索主链不落后: Hybrid + RRF + Cross-Encoder rerank 是 2026 年工业标准形态; CRAG/TARG/SEAL-RAG 落地密度高于多数生产系统. 本 RFC 不动主链.

## 提案范围

### A 评测学 (P0, 根因项)

#### A1 评测集扩展: 50 -> 200 题

- 现有 50 题原样保留 (回归可比, dataset_version 升 v2)
- 新增 150 题, 目标题型配比:

| 题型 | 现有 | 目标 | 新增来源 |
|---|---|---|---|
| definition | 46 | 60 | XVA 子项 / Greeks 扩展补齐 |
| compare (跨文档) | 4 | 30 | d457 vs d488 两代 FRTB 对比, BCBS vs IOSCO vs CFTC 口径对比 |
| multi-hop 聚合 | 0 | 40 | 跨 2-3 个 gold 的概念交叉题 (多 gold qrels) |
| numeric (含表格) | 9 | 30 | 条款数值条件 / 阈值 / breach 判定 |
| unanswerable | 0 | 20 | 语料外问题, 验收 refusal gate 的正确拒答率 |
| 其他 (procedure/chronology/greek) | 10 | 20 | 现有标签维度扩充 |

- 合成流程: LLM 生成候选 -> chunk_id 级 qrels 自动对齐 -> 人工审核 -> 落盘; 沿用 `qrels_gap_allowlist.json` 白名单机制守住口径
- retrieval metrics 需扩展多 gold 口径 (recall@k 按题内 gold 集合命中率, 不再单 gold)
- 落点: `tests/data/questions.json` `tests/data/qrels.json`, 加载器 `evaluation/dataset.py` 已支持扩展

#### A2 统计显著性: bootstrap 置信区间

- `evaluation/advanced_metrics.py` 增加 bootstrap 重采样 (1000 次), 关键指标输出 95% CI
- 报告 metrics 带 `ci_low` / `ci_high`; threshold gate 判定接入 CI 口径 (tolerance 机制已有)
- 直接回答 "faithfulness 0.903 -> 0.982 是否在噪声区间" 这类问题
- 落点: `evaluation/advanced_metrics.py` `evaluation/reporting.py` `evaluation/thresholds.py`

#### A3 judge 校准 (P1)

- 从 ragas judge 结果抽样约 50 条做人工标注, 与 judge 分数对齐
- 报告 Cohen's kappa, 目标 >= 0.6; 不达标则修 judge prompt 并复测
- 结果记入 [EVALUATION_LOG](../evaluations/EVALUATION_LOG.md)

### B 长上下文基线 (P0, 一次性实验)

语料 8.1MB 约 2M tokens, 在 128k context 的 DeepSeek-V3 下必须回答 "为什么不全量塞进上下文".

- 新增 `evaluation/baseline_long_context.py`, 三种模式同一题集同一 judge 对比:
  - `map_reduce_full`: 全语料分段摘要后作答 (全量知识, 高成本)
  - `parent_stuffing`: parent corpus 按相关性塞满 128k 窗口 (RAG 的最强朴素变体)
  - `rag_main`: 现有统一检索主链 (对照)
- 统一指标: faithfulness / answer_relevancy / numeric_consistency / refusal 正确率 / latency p50 p95 / token 成本
- 产出: 基线对比报告落盘 `docs/evaluations/`, 结论 ADR 化 (是否纳入每期评测对照列)

### C 语料与索引工程

#### C1 PDF 表格感知解析 (P1)

- 用 pdfplumber 为 d457 / d488 等监管 PDF 提取表格, 转为 markdown 表格独立 chunk (`chunk_type=table`)
- chunking `policy_version` 升级触发全量重建 (schema fingerprint 机制已有)
- 验收: 新增表格题 slice, 表格 gold 的 recall@5 不低于现 textual gold 水平

#### C2 Contextual Retrieval 变体重试 (P1, RFC-003 遗留)

- 变体一: 只对 BM25 侧注入 context brief, 不动 embedding (规避已实证的术语稀释)
- 变体二: 短 brief (title + section_path, 约 30 token) 替代文档级摘要
- feature flag `settings.features.contextual_briefs` 已有, A/B 用 A1 扩展后的评测集验证; 无收益则关闭并回写 [RFC-003](./RFC-003-contextual-retrieval.md)

### D 架构覆盖面

#### D1 外部基准锚定 (P1)

- 取 FinanceBench 公开子集 (约 50 题, 金融领域), 跑 dense / sparse / hybrid 检索层对比, 输出横向定位报告
- 只做检索层锚定, 不做端到端接入

#### D2 GraphRAG 轻量 PoC (P2, 依赖 A1)

- 用 LLM 抽取语料实体关系 (机构 / 文档 / 条款 / 指标), 构建轻量图
- 对比图检索与现 hybrid 在 A1 多跳题上的 gold 命中率
- 无显著收益则记录 ADR 后关闭, 不引入生产主链

#### D3 CRAG web fallback 决策记录 (仅记录, 不实现)

- CRAG 原论文 (arXiv 2401.15884) 的 web search 兜底与本项目 closed-domain 边界不符
- 语料外问题的正确行为已由 refusal gate 覆盖 (拒答 + next_actions)
- 该偏差此前未在任何决策文档中显式记录, 本条即记录; 不接外部搜索

## 优先级与顺序

| 优先级 | 条目 | 理由 |
|---|---|---|
| P0 | A1 评测集扩展 | 解锁所有后续决策的可验证性 |
| P0 | A2 bootstrap CI | 新评测集的结论必须带置信度 |
| P0 | B 长上下文基线 | 一次性实验, 决定架构叙事方向 |
| P1 | A3 judge 校准 | 评测集扩大后 judge 可信度需校准 |
| P1 | C1 表格解析 | 金融语料收益最直接 |
| P1 | C2 contextual 变体 | RFC-003 遗留, flag 已有成本低 |
| P1 | D1 外部基准 | 检索层锚定, 成本低 |
| P2 | D2 GraphRAG PoC | 依赖 A1 多跳题先行 |

预期总周期 4-6 周.

## 不做什么

- 不做 web search fallback (D3, closed-domain 决策显式化)
- 不做在线反馈闭环 / 语义缓存 / prompt injection 防护 (属生产化范畴, 见审计 E 项, 本 RFC 边界外)
- 不做中文分词改造 (语料全英文; 若未来引入中文语料再立项)
- 不动生产检索主链形态 (Hybrid + Query Intelligence + Advanced Index + CRAG/TARG/SEAL)
- 不以外部基准分数为发布门禁 (外部基准仅用于定位, 门禁仍以私有评测 + threshold gate 为准)

## 成功标志

- 评测集 >= 200 题, 多跳 / 聚合 / 不可回答题型齐备, qrels 全部 chunk_id 级, allowlist 保持清空
- 关键指标全部带 95% CI, threshold gate 判定考虑置信区间
- 长上下文基线报告落盘并有 ADR 结论
- 表格题 slice 与 judge kappa 达标 (>= 0.6)
- 外部基准定位报告落盘
- 上述结论均可在 [EVALUATION_LOG](../evaluations/EVALUATION_LOG.md) 反查

## 关联文档

- [RFC-001](./RFC-001-retrieval-hardening-roadmap.md) - 第一轮检索强化 (已收口), 本 RFC 是第二轮
- [RFC-003](./RFC-003-contextual-retrieval.md) - C2 变体重试的上游决策
- [RFC-004](./RFC-004-agentic-rag-paradigm.md) - "收益无法验证" 收口判断的背景, 由 A1 解锁
- [phase-5-frontier-alignment](../phases/phase-5-frontier-alignment.md) - 执行跟踪
- [EVALUATION_LOG](../evaluations/EVALUATION_LOG.md) - 评测台账

# RiskAgent-AgenticRAG Strategy

## 1. 战略目标

把 `RiskAgent-AgenticRAG` 做成一个非常强的高可信 RAG 项目.  
核心竞争力不是花哨的 Agent 编排.  
核心竞争力是下面 6 件事.

- 检索召回强
- 证据链清楚
- 评测可信
- 回归可比较
- 链路可观测
- 范式可持续

---

## 2. 战略边界

### 2.1 我们要做什么

- 做金融文档问答里的强检索和强召回
- 做高可信回答和结构化证据链
- 做 retrieval first 的评测和发布门禁
- 做可复现的索引 评测 报告和回归
- 做全链路可观测和退化告警
- 持续对齐业界最新 RAG 范式

### 2.2 我们不做什么

- 不做巨无霸 Agent 平台
- 不做无边界工具扩展
- 不做和检索召回关系很弱的功能堆砌
- 不把系统演化成通用工作流编排产品

---

## 3. 核心差异化

### 3.1 统一检索主链

- 统一主链便于评测和回归
- 运行时不再切多套对外 mode
- 复杂度压回同一条可验收链路

### 3.2 证据优先

- 回答不是只有自然语言
- 还要有 `citations` `claims` `evidence_set` `decision_log`
- 后置 gate 负责把 refusal evidence numeric 这几类失败拦住

### 3.3 评测先行

- 检索和生成要分开评
- 指标和报告必须可回放
- 发布门禁依赖报告 而不是演示主观感受

### 3.4 范式前沿

- 持续追踪学术界 2025-2026 最新 RAG 范式
- 选择性引入: Contextual Retrieval / CRAG / TARG / SEAL-RAG / Agentic RAG / RAPTOR
- 不盲目追新, 只引入能直接提升召回/精度/效率的范式

---

## 4. 2026 时间点的判断

- 对这个项目最值钱的不是继续堆重型 agent 流程
- 更值钱的是把 `qrels` `检索充分性判断` `索引一致性` `rerank` `领域评测` 做硬
- Enhanced RAG 在很多真实场景下仍然比重型 agentic RAG 更稳 更便宜 更容易验收
- 但要持续吸收新范式的优点, 不能停在 2023 年的 Advanced RAG 水平

---

## 5. 接下来最值得投入的方向

### 5.1 第一优先级 (P0)

- Contextual Retrieval: 索引时注入上下文摘要, 直接提升 recall ([RFC-003](./decisions/RFC-003-contextual-retrieval.md))
- 把 retrieval eval 从宽松 text 匹配继续升级到更硬的 evidence unit
- 把索引和 retriever cache 做成真正的版本化一致性机制

### 5.2 第二优先级 (P1)

- CRAG 纠错检索: 把 Self-RAG 升级为三档评估 (sufficient/insufficient/irrelevant) ([RFC-001](./decisions/RFC-001-retrieval-hardening-roadmap.md))
- TARG 自适应门控: 简单查询跳过检索, 减少 50%+ 不必要调用 ([RFC-001](./decisions/RFC-001-retrieval-hardening-roadmap.md))
- 强化数值型问题上的 typed evidence 和 numeric gate
- 做 token latency budget 和降级策略

### 5.3 可观测性 (跨阶段基础设施)

- 全链路 trace: 每次请求的 rewrite -> retrieve -> critique -> revise -> synthesize -> validate 全过程可追踪
- 检索诊断: dense/sparse/rerank/diversity 每个环节的延迟 返回数 过滤原因
- 退化告警: 自动发现 recall / faithfulness 退化 不依赖人工跑评测
- 详见 [RFC-002](./decisions/RFC-002-observability-full-chain-trace.md)

### 5.4 第三优先级 (P2)

- SEAL-RAG 替换式检索: 固定 budget 替换最弱证据, 避免 context 膨胀 ([RFC-001](./decisions/RFC-001-retrieval-hardening-roadmap.md))
- RAPTOR 递归摘要树: 多层级索引, 支持宏观问题 ([RFC-005](./decisions/RFC-005-raptor-recursive-abstractive-tree.md))
- 只在复杂多跳问题上引入有限度的多步 retrieval
- 不对全链路做无限扩张式 agent 化

### 5.5 长期方向 (P3)

- Agentic RAG 范式迁移: 从预定义 pipeline 到模型自主检索 ([RFC-004](./decisions/RFC-004-agentic-rag-paradigm.md))
- 引入 A-RAG 层次化检索接口, 让模型自主决定检索策略
- 引入 MARAG-R1 多工具协调思路 (semantic/keyword/filtering/aggregation)
- 前置条件: P0-P2 全部落地 + 可观测性就绪

---

## 6. 范式引入路线图

```
2026 Q3 (P0):
  └── Contextual Retrieval → recall_at_5 >= 0.6

2026 Q4 (P1):
  ├── CRAG 纠错检索 → sufficiency 三档评估
  ├── TARG 自适应门控 → 简单查询跳过检索
  └── 全链路 trace (RFC-002) → 可观测性就绪

2027 Q1 (P2):
  ├── SEAL-RAG 替换式检索 → 避免 context 膨胀
  └── RAPTOR 递归摘要树 → 多层级索引

2027 Q2+ (P3):
  └── Agentic RAG 范式迁移 → 模型自主检索
```

---

## 7. 一句话战略口径

`RiskAgent-AgenticRAG` 不是要做一个无边界 Agent 系统.  
它要做的是一个在金融文档问答场景里 检索强 召回强 证据硬 评测硬 链路可观测 范式可持续 的顶级 RAG 项目.

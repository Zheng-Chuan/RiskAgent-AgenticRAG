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
- 做全链路可观测 (退化告警经评估后不做, 见 [RFC-002](./decisions/RFC-002-observability-full-chain-trace.md))
- 选择性引入业界最新 RAG 范式 (第一轮 2026-08-25 收口; 2026-10-06 经前沿对齐审计重开第二轮, 见 [RFC-006](./decisions/RFC-006-frontier-gap-closing-roadmap.md))

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

- 项目期内追踪并选择性引入了学术界 2025-2026 RAG 范式: Contextual Retrieval (已实现默认关闭) / CRAG / TARG / SEAL-RAG 已落地, Agentic RAG 检索工具化已实现 (默认关闭), RAPTOR 评估后取消
- 不盲目追新, 只引入能直接提升召回/精度/效率的范式
- 第一轮已收口 (2026-08-25); 2026-10 前沿对齐审计判断下一瓶颈在评测学 (评测集规模与题型锁死了技术决策的可验证性), 第二轮 [RFC-006](./decisions/RFC-006-frontier-gap-closing-roadmap.md) 聚焦评测学 / 长上下文基线 / 语料索引 / 架构覆盖, 不动检索主链

---

## 4. 2026 时间点的判断

- 对这个项目最值钱的不是继续堆重型 agent 流程
- 更值钱的是把 `qrels` `检索充分性判断` `索引一致性` `rerank` `领域评测` 做硬
- Enhanced RAG 在很多真实场景下仍然比重型 agentic RAG 更稳 更便宜 更容易验收
- 项目期内已吸收新范式的优点 (CRAG/TARG/SEAL-RAG 等), 未停留在 2023 年的 Advanced RAG 水平

---

## 5. 已完成的投入 (2026-08-25 收口)

### 5.1 第一优先级 (P0)

- Contextual Retrieval: 已实现, 默认关闭 (Qwen3-Embedding-4B 下 briefs 稀释术语信号), 见 [RFC-003](./decisions/RFC-003-contextual-retrieval.md)
- retrieval eval 从宽松 text 匹配升级到 chunk_id 级 evidence unit
- 索引和 retriever cache 版本化一致性机制 (schema fingerprint 拆分)

### 5.2 第二优先级 (P1)

- CRAG 纠错检索: Self-RAG 升级为三档评估, ON/OFF/混合三组 A/B 数据闭环, 混合策略已上线生产 ([RFC-001](./decisions/RFC-001-retrieval-hardening-roadmap.md))
- TARG 自适应门控: 简单查询跳过 fanout, 金融术语词表修复 12 题误判 ([RFC-001](./decisions/RFC-001-retrieval-hardening-roadmap.md))
- 数值型问题上的 typed evidence 和 numeric gate
- token latency budget 与降级策略

### 5.3 可观测性 (跨阶段基础设施)

- 全链路 trace: 每次请求的 rewrite -> retrieve -> critique -> revise -> synthesize -> validate 全过程可追踪
- 检索诊断: dense/sparse/rerank/diversity 每个环节的延迟 返回数 过滤原因
- 退化告警未实现 (收口决策: 不做, 质量退化依赖人工跑评测), 见 [RFC-002](./decisions/RFC-002-observability-full-chain-trace.md)

### 5.4 第三优先级 (P2)

- SEAL-RAG 替换式检索: capacity=5 预算制替换, 跨轮 dedup 修复后 50 题 0 重复 ([RFC-001](./decisions/RFC-001-retrieval-hardening-roadmap.md))
- RAPTOR 递归摘要树: 已取消 (评测集无宏观题型, 收益无法验证)
- Agentic RAG 范式迁移: 检索工具化阶段一已实现 (默认关闭), 完整迁移已取消, 见 [RFC-004](./decisions/RFC-004-agentic-rag-paradigm.md)

### 5.5 范式落地时间线 (实际)

P0-P2 计划于 2026 Q3 起排期, 实际全部在 2026-08-25 前完成闭环 (v10b gate 首次全绿 -> v10d 50/50 -> v10f 混合策略上线), 未启动方向 (RAPTOR / Agentic RAG 完整迁移 / 退化告警) 经评估后取消, 项目收口.

---

## 6. 一句话战略口径

`RiskAgent-AgenticRAG` 不是要做一个无边界 Agent 系统.  
它要做的是一个在金融文档问答场景里 检索强 召回强 证据硬 评测硬 链路可观测 范式可持续 的顶级 RAG 项目.

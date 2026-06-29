# RiskAgent-AgenticRAG Strategy

## 1. 战略目标

把 `RiskAgent-AgenticRAG` 做成一个非常强的高可信 RAG 项目.  
核心竞争力不是花哨的 Agent 编排.  
核心竞争力是下面 4 件事.

- 检索召回强
- 证据链清楚
- 评测可信
- 回归可比较

---

## 2. 战略边界

### 2.1 我们要做什么

- 做金融文档问答里的强检索和强召回
- 做高可信回答和结构化证据链
- 做 retrieval first 的评测和发布门禁
- 做可复现的索引 评测 报告和回归

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

---

## 4. 2026 时间点的判断

- 对这个项目最值钱的不是继续堆重型 agent 流程
- 更值钱的是把 `qrels` `检索充分性判断` `索引一致性` `rerank` `领域评测` 做硬
- Enhanced RAG 在很多真实场景下仍然比重型 agentic RAG 更稳 更便宜 更容易验收

---

## 5. 接下来最值得投入的方向

### 5.1 第一优先级

- 把 retrieval eval 从宽松 text 匹配继续升级到更硬的 evidence unit
- 把索引和 retriever cache 做成真正的版本化一致性机制
- 把 Self-RAG 的 stop continue 判断升级成更强的 sufficiency scorer

### 5.2 第二优先级

- 升级 reranker 和 query intelligence
- 强化数值型问题上的 typed evidence 和 numeric gate
- 做 token latency budget 和降级策略

### 5.3 第三优先级

- 只在复杂多跳问题上引入有限度的多步 retrieval
- 不对全链路做无限扩张式 agent 化

---

## 6. 一句话战略口径

`RiskAgent-AgenticRAG` 不是要做一个无边界 Agent 系统.  
它要做的是一个在金融文档问答场景里 检索强 召回强 证据硬 评测硬 的顶级 RAG 项目.

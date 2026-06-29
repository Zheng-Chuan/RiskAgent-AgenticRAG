# Phase 2 Retrieval Hardening

## 目标

把项目的主要投入集中到 retrieval 和 recall 强化.

## 时间

2-3 周

## 本阶段重点

- 强化 qrels 和 retrieval eval 的可信度
- 强化 query intelligence 和 revise loop 的有效性
- 强化 rerank 和 advanced index 的领域适配
- 强化索引一致性和 cache key 治理

## P0 必须先做

### 1. qrels 升级

- 把当前偏 text match 的 qrels 继续升级到 chunk_id 或 evidence unit
- 让 recall@k MRR nDCG 更真实反映召回变化
- 优先覆盖 `definition` `compare` `numeric` `regulation` 四类题型
- 当前未硬化题已显式收口到 `qrels_gap_allowlist.json`
- 只有批准过的 corpus gap 才允许保留 text only qrel

### 2. index manifest 版本化

- 把 `embedding model` `embedding dim` `chunking policy` `advanced index config` 纳入版本键
- 避免旧索引被误复用
- 避免 retrieval 实验结论被缓存污染
- 当前已落地 `manifest v2 + schema_fingerprint`
- schema 变化时会拒绝 partial include 并要求全量重建

### 3. sufficiency scorer

- 把当前轻量 Self-RAG 规则升级为更强的 sufficiency scorer
- 至少按题型区分 `definition` `compare` `numeric`
- 让 stop continue 判断更贴近真实 answerability
- 当前已落地轻量题型感知版
- 已把 `query_coverage` `source_diversity` `parent_diversity` `numeric_evidence` 纳入判断

### 4. reranker 领域适配

- 系统评估更适合中文金融文档的 reranker
- 比较通用 baseline 和候选领域 reranker 的效果与时延
- 当前实现已支持 `reranker candidates` 离线候选列表
- 启动时会优先尝试候选模型 找不到再自动回退到可用 baseline
- 评测报告会写出请求模型 候选列表 和实际生效模型

## P1 随后做

### 5. query intelligence 自适应

- 不是每题都默认做全套 fanout
- 根据题型决定 step back decomposition acronym expansion 的强度
- 当前实现已切到 route policy
- `default` 题型默认只保留 base query 不再盲目扩写
- `background` `procedure` 保留 keywordize 和 step back
- `compare` 保留更强 fanout 包括 decomposition

### 6. advanced index query aware expand

- parent expand 不再一刀切
- 根据题型和证据缺口控制 expand 强度
- 当前实现已切到轻量规则策略
- `compare` `background` `procedure` 会优先扩 top docs 的 parent 上下文
- `default` `numeric` 只在强 parent signal 或更强证据条件下才扩
- expand 理由会写回 metadata 方便 trace 和评测解释

### 7. retrieval observability

- 记录 fanout 数量 rerank pairs node latency token 预算
- 为后续做 retrieval budget 提供依据

## 建议交付

- 更硬的 qrels 单位
- 更强的 sufficiency scorer
- 版本化 index manifest
- 领域更贴合的 reranker 评估结论
- query intelligence 策略化配置
- retrieval 运行观测字段

## 验收标准

- 检索指标能更真实反映召回变化
- 关键 retrieval 改动可以做 regression compare
- 文档问答中的召回和证据链有可见提升

## 不做什么

- 不扩张成通用 Agent 平台
- 不优先做复杂前端
- 不优先做大规模 GraphRAG 迁移
- 不做和检索召回弱相关的功能堆砌

## 退出标准

- qrels 和 retrieval eval 口径明显变硬
- 至少一类高难题型的召回质量有稳定提升
- 索引和缓存污染风险下降
- phase 3 可以在更硬的 retrieval 基础上继续做 evaluation hardening

## 状态

In Progress

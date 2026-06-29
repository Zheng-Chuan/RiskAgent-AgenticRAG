# RiskAgent-AgenticRAG Resume Notes

## 1. 项目一句话

面向金融风控知识问答场景的高可信 RAG 系统.  
核心卖点是 `检索可信` `回答带证据` `评测可复现` `回归可审计`.

---

## 2. 最适合对外讲的能力

- 统一 LangGraph 主链把 `rewrite` `retrieve` `critique` `revise` `synthesize` `validate` 收到同一条可审计流程里
- 统一检索主链默认包含 `hybrid retrieval` `query intelligence` `advanced index`
- 检索层同时利用 `dense` `BM25` `RRF` `cross-encoder rerank` 和 `diversity select`
- 输出层不是只有 answer 还会产出 `citations` `claims` `evidence_set` `decision_log`
- 评测层把 `retrieval` `generation` `gate` 三层分开统计
- 发布层有最小离线回归和阈值门禁

---

## 3. 最好主动承认的边界

- 这个项目不是通用 Agent 平台
- 工具增强目前是窄场景的数值型风险补充 不是无边界 tool use
- 当前最强的部分是检索 召回 证据链和评测闭环
- 后续继续深化 也会优先投入在 retrieval 和 evidence hardening 上

---

## 4. 面试时推荐主动说的话

- 我们没有把项目做成巨无霸 Agent 平台 而是主动把边界收敛到了高可信 RAG
- 这个项目最关键的不是多加一个 fancy retriever 而是把 retrieval generation gate evaluation 拆清楚
- 默认主链固定走统一检索链 这样评测口径和发布门禁才稳定
- 我们对外更强调 evidence first 和 evaluation first 而不是 demo first

---

## 5. 文档回链

- 架构主链: [ARCHITECTURE.md](./ARCHITECTURE.md)
- 产品总纲: [PRD.md](./PRD.md)
- 长期方向: [STRATEGY.md](./STRATEGY.md)
- 技术决策: [decisions/](./decisions/)
- 阶段规划: [phases/](./phases/)

# INTERVIEW

目标: 收集 50 个偏硬核的 MultiAgent RAG 面试题, 并在开发过程中逐题回答.

使用方式:

- 每个问题用 checklist 管理
- 你在实现某个模块时, 顺手补对应题目的答案

## 基础概念与系统边界

- [ ] Q1. 什么是 MultiAgent RAG, 它和单 Agent RAG 的关键差异是什么?
  - 答案: TODO
- [ ] Q2. 什么时候你不应该使用多智能体架构?
  - 答案: TODO
- [ ] Q3. 你如何定义 MultiAgent 系统的最小可行边界(MVP)?
  - 答案: TODO
- [ ] Q4. 在企业场景中, 为什么 citations 是 contract 而不是 optional feature?
  - 答案: TODO
- [ ] Q5. 如何区分 groundedness, faithfulness, factuality, helpfulness?
  - 答案: TODO

## 数据与索引

- [ ] Q6. chunk size 和 overlap 如何影响 citations 可读性与覆盖率?
  - 答案: chunk size 和 overlap 主要在 recall, noise, 以及 citations 可读性之间做权衡.
    - chunk size 过小
      - 优点: citations 更精确, 每条引用更容易对应到具体结论
      - 缺点: chunk 数暴增, 向量库更大, 检索更容易碎片化, top_k 不够时 recall 会下降
    - chunk size 过大
      - 优点: 单条 chunk 覆盖更完整上下文, recall 更容易保证
      - 缺点: citations 指向的片段太长, 工程师难以快速定位证据, 噪声也会增加
    - overlap 的作用
      - overlap 用来减少跨边界信息丢失, 特别是标题切分不完美时
      - overlap 过大则会带来重复内容, 降低有效信息密度, 也会让相近 chunk 都被召回
    - 本项目的 Week 2 选择
      - 采用 chunk_size=900, chunk_overlap=120 作为可复现 baseline
      - 目标是先把 20 题问题集的 citations coverage 跑通, 再用指标驱动调参
- [ ] Q7. 你如何设计 chunk metadata schema 才能支持稳定可追溯 citations?
  - 答案: metadata schema 的目标是稳定, 可回放, 可定位.
    - 必备字段
      - source: 原始文件路径或稳定 ID
      - start_index: chunk 在 source 内的起始字符位置, 用于快速定位
      - chunk_id: 稳定 ID, 不能依赖 chunk 顺序, 否则语料轻微改动会导致引用漂移
    - 本项目的 Week 2 选择
      - split 时开启 add_start_index
      - 用 sha1(source:start_index:text) 生成 digest, 再组成 chunk_id, 例如 filename:digest
      - 这样只要文本片段不变, chunk_id 就稳定, 适合做回归与对比
- [ ] Q8. 在 ingest 阶段你会记录哪些 artifacts 来保证可复现?
  - 答案: TODO
- [ ] Q9. 何时需要 rebuild index, 何时只需要 rerun query?
  - 答案: TODO
- [ ] Q10. 如何避免 index 缓存导致 citations 指向旧语料的问题?
  - 答案: TODO

## Retrieval

- [ ] Q11. top_k 过大和过小各自会带来什么问题?
  - 答案: TODO
- [ ] Q12. 什么是 retrieval drift, 如何检测并缓解?
  - 答案: TODO
- [ ] Q13. reranking 应该放在什么位置, 以及为什么?
  - 答案: TODO
- [ ] Q14. 在金融衍生品风险领域, 你会如何构建一个可评测的检索问题集?
  - 答案: TODO

## 多智能体编排(LangGraph)

- [ ] Q15. LangGraph 的 state schema 设计原则是什么?
  - 答案: TODO
- [ ] Q16. 多智能体之间的输入输出 contract 应该如何定义才能可测?
  - 答案: TODO
- [ ] Q17. researcher -> writer -> reviewer 流程里, reviewer 应该检查什么?
  - 答案: TODO
- [ ] Q18. 多智能体如何共享上下文但又控制 token 成本?
  - 答案: TODO
- [ ] Q19. 如何避免 agent 之间循环对话或无效迭代?
  - 答案: TODO
- [ ] Q20. 多智能体引入后, 系统的非确定性来自哪里, 如何压住?
  - 答案: TODO

## 生成, 引用, 解释

- [ ] Q21. 为什么 citations 必须从 retriever artifacts 计算, 而不是由 LLM 自己输出?
  - 答案: TODO
- [ ] Q22. 你如何定义有效 citations? 最小验收口径是什么?
  - 答案: TODO
- [ ] Q23. 如何避免模型在 citations 不足时胡编?
  - 答案: TODO
- [ ] Q24. 你会如何设计面向工程师的回答模板, 让解释既可读又可追溯?
  - 答案: TODO

## 评测与回归

- [ ] Q25. 你会如何设计 e2e smoke test, 它应该断言什么, 不应该断言什么?
  - 答案: TODO
- [ ] Q26. citations coverage 如何定义与计算?
  - 答案: TODO
- [ ] Q27. 如何构建一个 20 题的 seed question set, 并让它能长期使用?
  - 答案: TODO
- [ ] Q28. 如何做 ablation studies 来定位收益来自哪里(retrieval, prompt, agent flow)?
  - 答案: TODO
- [ ] Q29. 你会记录哪些线上指标来监控质量退化?
  - 答案: TODO

## LLM provider 与 OpenAI compatible

- [ ] Q30. 为什么要采用 OpenAI compatible server, 它解决了什么工程问题?
  - 答案: TODO
- [ ] Q31. OpenAI compatible 的 API 行为不一致会带来哪些坑, 如何规避?
  - 答案: TODO
- [ ] Q32. 如果从 deterministic fallback 迁移到真实 LLM, 你要锁定哪些 contract?
  - 答案: TODO
- [ ] Q33. 如何做 prompt versioning, 让结果可复现?
  - 答案: TODO

## Guardrails 与安全

- [ ] Q34. 什么是 guardrails, 在 RAG 系统里应如何分层实现?
  - 答案: TODO
- [ ] Q35. 如何处理敏感信息, 合规与审计需求?
  - 答案: TODO
- [ ] Q36. 当语料无法支持问题时, 系统应该如何拒答或引导?
  - 答案: TODO

## 工程化与可观测性

- [ ] Q37. request_id 在 RAG 与多智能体系统里有什么价值?
  - 答案: TODO
- [ ] Q38. 你会如何设计日志分层, 让排障可控?
  - 答案: TODO

- [ ] Q39. 为什么 artifacts 落盘对评测与回归是基础设施?
  - 答案: TODO
- [ ] Q40. 如何选择 embeddings 模型, 并保证不同环境下 embeddings 维度一致, 避免 silent bug?
  - 答案: 选择 embeddings 的关键是可复现, 可解释, 并能支持评测.
    - 为什么要在 Week 2 切换到真实 embeddings
      - citations coverage 的硬指标高度依赖 retrieval 质量
      - FakeEmbeddings 只能保证链路可跑, 但无法代表真实检索效果
    - 为什么选择 sentence-transformers/all-MiniLM-L6-v2
      - 384 维, 在本地 CPU 上相对轻量, 适合作为 baseline
      - 社区使用广泛, 可解释性强, 便于面试叙事
      - 先用稳定 baseline, 后续再做 domain specific 或更大模型对比
    - 如何避免 silent bug
      - pin EMBEDDINGS_MODEL, 并把 rebuild index 作为默认语义
      - persist 目录与 embeddings 配置必须绑定, embeddings 模型或维度变化就必须清空重建
      - 在评测输出中记录 embeddings 配置, 让对比可追溯

## 性能与成本

- [ ] Q41. 你如何降低端到端 latency, 以及优先优化哪里?
  - 答案: TODO
- [ ] Q42. 如何控制 token cost, 以及多智能体引入后的成本上升如何治理?
  - 答案: TODO
- [ ] Q43. 并发上来后, vector store 与 LLM 调用的瓶颈各是什么?
  - 答案: TODO

## 业务与场景

- [ ] Q44. 你如何定义一个可展示的金融衍生品风险 demo 场景?
  - 答案: TODO
- [ ] Q45. 你如何把输出对齐到工程师的日常任务(排障, 解释字段, 风险归因)?
  - 答案: TODO

## 失败案例与 tradeoff

- [ ] Q46. 举例说明一个会导致 citations 失真或不可追溯的设计错误.
  - 答案: TODO
- [ ] Q47. 你如何处理 retrieval 为空的情况?
  - 答案: TODO
- [ ] Q48. 多智能体系统的最大维护成本是什么, 如何控制?
  - 答案: TODO

## 迁移与演进

- [ ] Q49. 如何从单轮 Q&A 演进到多轮对话, 但不破坏 citations contract?
  - 答案: TODO
- [ ] Q50. 如果后续要把系统服务化, 你会如何设计 API contract 与版本兼容?
  - 答案: TODO

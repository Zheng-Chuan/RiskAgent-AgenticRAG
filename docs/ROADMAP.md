# 开发计划

采用最小可运行 demo -> 逐步扩充的策略. 目标是基于金融衍生品与风险管理资料, 为企业内部软件工程师提供通俗易懂且可追溯引用来源的业务解释, 降低理解门槛.

## 当前技术栈

- UI: Gradio
- Multi-agent orchestration: LangGraph
- RAG framework: LangChain
- Vector store: Chroma
- Runtime env: conda env LangChain

LLM strategy:

- Week 1 允许无 key 的 deterministic fallback, 先验证 RAG 数据链路与 citations.
- Week 2 开始引入真实 LLM, 优先采用 OpenAI compatible server.
  - 商业 API 或开源模型推理服务都可.
  - 开源模型建议通过 vLLM 或 TGI 对外提供 OpenAI compatible endpoint.

## 2026-01 1 个月交付目标

定位: 以 AI Agent 能力展示为第一优先级.

硬性验收口径:

- 端到端可复现: 清空索引 -> ingest -> 查询 -> 返回 answer + citations.
- 可控与可测: 至少 1 条 e2e smoke test, 评测脚本可一键运行并输出报告.
- 工程化底线: 无明文 secrets.

备注: 当前 roadmap 聚焦本地可运行 demo, 暂不包含生产化能力.

### Week 1: baseline 跑通 + 工程化骨架

- 交付
  - [x] requirements.txt 与 Python 版本固化
  - [x] secrets 全部走环境变量
  - [x] 最小 CLI 或 Gradio UI 启动
  - [x] 最小 ingest -> retrieve -> answer 流程
  - [x] docs/INTERVIEW.md: 50 道硬核面试题清单, 用于边做项目边答题
- 验收
  - [x] 1 条命令启动 demo
    - [x] UI: `conda run -n LangChain python gradio_app.py`
    - [x] CLI: `conda run -n LangChain python demo_cli.py --rebuild-index --question "what is FRTB"`
  - [x] 返回 citations, 且可定位来源
  - [x] 至少 1 条 e2e smoke test 可通过
    - [x] `conda run -n LangChain python smoke_test.py`
  - 进度: Week 1 已完成
  - 为什么要做: 先把可复现的启动路径与回归入口固定, 避免后续每次改动都在环境与手工验证上耗时.
  - 为 Week 2 打基础: Week 2 要扩充语料与问题集, 需要稳定入口来做回归对比, 才能判断引用质量是变好还是变差.

### Week 2: RAG MVP 闭环与引用质量

- 交付
  - [x] docs/sources 语料接入(至少包含 Background.md)
  - [x] chunk 规则与 metadata schema 固化
  - [x] 20 个种子问题集
- 验收
  - [x] 20 个问题中, 80% 以上回答包含有效 citations
  - 为什么要做: 引用覆盖率是最直接的 groundedness proxy, 可以压住幻觉并逼迫我们改检索与切分.
  - 为 Week 3 打基础: Week 3 引入多智能体时, 每个 agent 的结论都必须能回指证据, 否则会放大幻觉.

### Week 3: 业务场景驱动的多 agent MVP

北极星场景(先做 1 个, 其余作为扩展):

- Desk exposure monitoring: 生成 desk 级风险简报, 并对 breaches 给出解释与下一步.
- Limit breach investigation: 针对 breach 做归因假设, 证据地图, 以及建议动作.

多 agent 的必要性来自职责互斥与可控性, 不是 roleplay.

- 交付
  - [ ] 明确输入输出 contract
    - 输入: query, as_of, desk, abs_delta_limit
    - 输出: report, breaches, evidence_set, claims
  - [ ] 定义 agents roster(功能型, 硬边界)
    - DataAgent: 只负责调用工具取结构化数据, 不写结论
    - RAGAgent: 只负责从 docs/sources 找口径与概念, 只产出 evidence
    - AnalysisAgent: 基于 data + evidence 形成 claims 列表
    - ValidatorAgent: 校验每条 claim 的证据与数字一致性, 不通过就返回 failure_reason
    - ReportAgent: 生成面向工程师的最终报告, 带 citations
  - [ ] 引入工具调用(本地优先)
    - 先用本地 mock tool 结构跑通
    - 后续如需接入外部服务, 再单独评估
  - [ ] Guardrails
    - 无证据则拒答, 并输出 next_actions
    - 数字不一致则 fail, 不允许用模糊措辞糊过去
- 验收
  - [ ] 1 条端到端场景命令可跑通
    - 清空 index -> ingest -> 调工具 -> 生成 report -> 落盘结果
  - [ ] 每条关键结论必须能回指 evidence_set
  - [ ] 失败路径可解释, 输出包含 failure_reason

### Week 4: 结构化输出与评测升级

- 交付
  - [ ] 结构化输出落盘(便于调试与回归)
    - evidence_set: source, chunk_id, start_index
    - claims: claim_id, statement, evidence_ids, confidence, failure_reason
  - [ ] 评测升级
    - citations coverage
    - citation precision(抽样检查 evidence 是否真正支持 claim)
    - refusal quality(该拒答时必须拒答)
    - numeric consistency(报告数字必须等于 tool 输出)
  - [ ] README 与使用说明
    - 一键运行
    - 常见问题与排障
- 验收
  - [ ] 新人按 README 10-15 分钟可跑通 demo
  - [ ] 评测脚本可一键运行并输出报告
  - 为什么要做: 多 agent 系统的技术深度来自 contract, 可控性, 与可回归.

## 设计与阶段拆分(用于实现路径)

说明: 下述 Phase 用于组织工程工作, 但 2026-01 内按上面的 4 周计划完成交付.

## Phase 0: 基础强化与项目骨架

**目标**: 先把工程化基础打牢, 让后续迭代稳定可扩展.

- [x] 确认 conda 环境 LangChain 可用, 固化 Python 版本
- [x] 增加 requirements.txt, 不 pin 版本, 以当前环境为准
- [x] 增加最小测试框架, 至少覆盖 1 条端到端 smoke test
- [x] 定义核心抽象
  - [x] 文档源与元数据 schema
  - [x] chunk schema
  - [ ] embedding provider 接口
  - [x] vector store 接口(Chroma)
  - [x] graph state schema(LangGraph)
  - [x] retrieval 输出 schema, 必须包含 citations

**验收标准**:

- [x] 项目可在本地一键启动或一键运行 demo
- [x] 无明文 secrets
- [x] 至少 1 条端到端测试可通过

## Phase 1: RAG MVP, 面向工程师的业务解释

**目标**: 跑通 ingest -> index -> retrieve -> generate 的闭环, 输出带引用的解释结果.

### 1.1 资料与数据接入

- [x] 定义资料目录约定, 例如 docs/sources
- [ ] 接入第 1 批语料
  - [ ] Background.md
  - [ ] 可选: 公开可引用的 FRTB, CVA, Greeks, XVA 资料
- [x] 文档解析
  - [x] markdown 解析
  - [ ] 可选: pdf 解析

### 1.2 切分与索引策略

- [x] chunk 策略
  - [x] baseline: 按长度切分
  - [ ] 以标题层级优先, 再按长度切分
  - [ ] chunk 必须携带 section path 与来源定位
- [x] vector store
  - [x] 本地优先, 例如 Chroma
- [ ] embeddings
  - [x] MVP: FakeEmbeddings(离线可运行)
  - [ ] Week 2: 切换为真实 embeddings, 并固化 provider 与维度

### 1.3 生成与引用

- [ ] 统一回答模板, 面向软件工程师
  - TLDR
  - 概念解释
  - 为什么重要
  - 在系统里的常见数据流与字段
  - 典型示例
  - citations
- [ ] 引用规则
  - 每个关键结论必须能对应到至少 1 个 chunk
  - 模型不确定时必须说明不确定并给出下一步建议

### 1.4 最小交互形态

- [x] CLI
  - [x] ingest(build_index)
  - [x] ask(demo_cli.py)
  - [ ] chat(多轮对话)
- [x] 简单 Web UI, 例如 Gradio

**验收标准**:

- [ ] 给定 20 个种子问题, 80% 以上回答包含有效 citations
- [x] 端到端流程可复现
  - [x] 清空索引 -> ingest -> 查询 -> 返回答案

## Phase 2: 质量提升, 可评测与可控

**目标**: 降低幻觉, 提升检索命中与解释质量, 形成可迭代的评测体系.

- [ ] 建立评测集
  - 检索相关性
  - 事实一致性与引用覆盖
  - 工程师可读性
- [ ] 增加结构化中间产物
  - claims 与 evidence_set 作为一等公民
  - validator 产出 failure_reason
- [ ] 增加 guardrails
  - 无法从语料支持则拒答或要求补充资料
  - 敏感信息与合规提示
- [ ] 领域知识增强
  - 术语表与缩写表
  - 业务对象字典, 例如 position, security, desk, trader

**验收标准**:

- [ ] 评测脚本可一键运行并输出报告
- [ ] 相比 Phase 1, 事实一致性指标显著提升

## Phase 3: 预留

说明: Phase 3 暂不在当前范围内. 当前先把本地 demo 的多 agent 协作与评测做扎实.

## 时间规划

里程碑按本地 demo 倒排.

| Milestone | 预计时间 | 验收输出 |
| --------- | -------- | -------- |
| Week 1 | 已完成 | baseline RAG demo + citations + smoke test |
| Week 2 | 已完成 | 真实 embeddings + 稳定 chunk_id + 20 题评测覆盖 |
| Week 3 | 2026-01-12 to 2026-01-18 | 业务场景多 agent MVP + 工具调用 + guardrails |
| Week 4 | 2026-01-19 to 2026-01-25 | 结构化输出落盘 + 评测升级 + 文档固化 |

**总计**: 4 周

## 开发建议

1. 每完成一个 Phase 就提交 Git, 保持可回溯
2. 以数据口径与引用为第一优先级, 宁可少答也不要编造
3. 每周至少 1 次 demo, 记录输入输出与问题清单
4. 先做 CLI 后做 UI, 降低早期复杂度

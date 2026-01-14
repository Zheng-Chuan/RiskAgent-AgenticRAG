# 开发计划

我们先做一个能跑的最小 demo
再一点点加功能
目标很直接
把金融衍生品和风险管理的资料讲清楚
让工程师更容易上手
每次回答都要能回到原文验证
所以必须带引用

## 当前技术栈

- UI: Gradio
- Multi-agent orchestration: LangGraph
- RAG framework: LangChain
- Vector store: Milvus
- Runtime env: conda env LangChain

LLM strategy

- Week 1 允许无 key 的 deterministic fallback 先验证 RAG 链路和 citations
- Week 2 开始引入真实 LLM 优先用 OpenAI compatible server
  - 商业 API 或开源模型推理服务都可以用
  - 开源模型建议通过 vLLM 或 TGI 对外提供 OpenAI compatible endpoint

## 2026-01 1 个月交付目标

定位 先把 AI Agent 的能力展示出来 其他事情往后放

硬性验收口径

- 端到端可复现: 清空索引 -> ingest -> 查询 -> 返回 answer + citations
- 可控与可测: 至少 1 条 e2e smoke test, tests 一键运行并输出报告
- 工程化底线: 不在仓库里写明文 secrets

备注 这个 roadmap 只盯本地可运行 demo 暂时不做生产化

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
    - [x] `conda run -n LangChain python -m unittest tests.test_week1_acceptance`
  - 进度: Week 1 已完成
  - 为什么要做 先把启动方式和回归入口固定住
  - 不然你每改一次代码 都要花时间在环境和手工验证上
  - 为 Week 2 打基础 Week 2 要扩充语料和问题集
  - 需要稳定入口做回归对比 才知道引用质量到底有没有变好

### Week 2: RAG MVP 闭环与引用质量

- 交付
  - [x] docs/sources 语料接入(至少包含 Background.md)
  - [x] chunk 规则与 metadata schema 固化
  - [x] 20 个种子问题集
- 验收
  - [x] 20 个问题中, 80% 以上回答包含有效 citations
    - [x] `conda run -n LangChain python -m unittest tests.test_week2_acceptance`
  - 为什么要做 引用覆盖率是最简单也最管用的指标
  - 它能压住幻觉 也会逼着我们去优化检索和切分
  - 为 Week 3 打基础: Week 3 引入 agentic loop 时, 每条关键结论都必须能回指证据, 否则会放大幻觉.

### Week 3: 单 agent 的 agentic RAG MVP

目标: 先保持单 agent 编排, 但要有 agentic 行为, 比如会改写 query, 会自检, 会重试检索, 会用工具, 也会做 validator

北极星场景(先做 1 个, 其余作为扩展):

- Desk exposure monitoring: 生成 desk 级风险简报, 并对 breaches 给出解释与 next_actions.
- Limit breach investigation: 针对 breach 做归因假设, 证据地图, 以及建议动作.

说明 这一阶段不强制多智能体
我们更在意 contract evaluator regression 这些能让系统可控可回归的东西

- 交付
  - [x] 头等大事: 接入本地 LLM(Ollama)
    - 默认开发路径走 Ollama, 实时看到效果
    - 环境变量
      - LLM_PROVIDER=ollama
      - `OLLAMA_BASE_URL=http://localhost:11434`
      - OLLAMA_MODEL=qwen3:8b
  - [x] 统一输入输出 contract(可执行 schema, v1)
    - 输入
      - request_id: string, uuid
      - query: string
      - as_of: string, ISO8601 or YYYY-MM-DD
      - desk: string
      - abs_delta_limit: number
    - 输出
      - request_id: string
      - report: string(对话式回答)
      - breaches: list[dict]
      - evidence_set: list[Evidence]
      - claims: list[Claim]
      - tool_traces: list[ToolTrace]
      - decision_log: list[Decision]
      - status: ok or failed
      - failure_reason: FailureReason or null
    - 对话式回答规则
      - 每段关键结论必须能回指至少 1 条 citation
      - citations 必须来自 retriever 返回的 docs metadata, 不允许模型自造引用
  - [x] Agentic loop(单 agent)
    - step 1: interpret intent and choose plan
    - step 2: retrieve with query rewrite(HyDE style optional)
    - step 3: self critique on retrieval quality
    - step 4: if low quality then re-retrieve with revised query, max_rounds=2
    - step 5: tool use for numeric facts
    - step 6: synthesize claims and report
    - step 7: validator gate, fail fast on numeric or evidence issues
  - [x] 引入工具调用(本地优先)
    - desk exposure tool 先用本地 mock 输出结构跑通
  - [x] Validator(确定性规则, 不依赖模型)
    - evidence gate
      - 每条 claim 的 evidence_ids 必须非空
      - evidence_id 必须能在 evidence_set 找到
      - 引用粒度必须到 chunk_id + start_index
    - numeric consistency gate
      - report 与 claims 中出现的关键数字必须能回指到 tool_traces 的结构化输出
      - 如无法回指, 必须标记为 numeric_inconsistent
    - refusal gate
      - retrieval empty 或 evidence empty 时必须拒答并给 next_actions
  - [x] LangGraph 编排层(后续演进)
    - 先保留每个 step 为可单测的纯函数, 再用 LangGraph 作为编排层
    - 目标是统一 state, trace, conditional edges, 便于后续扩展与可视化
    - 通过环境变量 USE_LANGGRAPH=true 启用
- 验收
  - [x] 1 条端到端场景命令可跑通
    - 清空 index -> ingest -> agentic loop -> tool use -> validator -> 落盘 artifacts
  - [x] 输出必须可被 schema 解析, 且包含 tool_traces 与 decision_log
  - [x] 失败路径可解释, 输出包含 failure_reason.category
  - [x] LangGraph 编排层可选启用, 输出与纯函数 runner 保持一致 schema

### Week 4: 基于 RAGAS 的评测模块

- 交付
  - [x] 数据集与记录格式
    - [x] inputs
      - [x] question
      - [x] optional reference_answer
      - [x] optional ground_truth_contexts
    - [x] outputs
      - [x] answer
      - [x] contexts
      - [x] citations
      - [x] structured_response.json 作为结构化落盘入口
    - [ ] 数据集文件建议
      - [x] tests/data/questions.json 作为最小数据集
      - [ ] tests/data/eval_set.json 作为可扩展数据集
  - [ ] RAGAS 指标集落地
    - [ ] RAG triad
      - [ ] context relevance
      - [ ] faithfulness groundedness
      - [ ] answer relevance
    - [ ] retrieval metrics
      - [ ] context precision
      - [ ] context recall
    - [ ] 设计约束
      - [x] 支持 offline baseline 先跑确定性指标
      - [ ] 支持开启 LLM judge 模式用于更贴近人类评价
  - [ ] 自定义指标补齐本项目关注点
    - [x] citations coverage
    - [ ] citation precision 抽样或全量校验 evidence 是否支持 claim
    - [ ] refusal quality 该拒答时必须拒答
    - [ ] numeric consistency 报告数字必须等于 tool 输出
    - [ ] failure taxonomy coverage 每类 failure_reason 至少 1 条用例
  - [x] 评测运行器与报告
    - [x] 一条命令运行评测
      - [x] conda run -n LangChain python -m riskagent_rag.evaluation.run
    - [x] 报告落盘
      - [x] JSON 报告包含 per sample 结果与汇总
      - [x] 报告路径建议放到 .artifacts 下的 reports 子目录
    - [x] 回归对比
      - [x] 支持读取上一份报告作为 baseline
      - [x] 支持阈值配置并标记 regression
  - [ ] 文档与使用说明
    - [ ] 如何新增评测样本
    - [ ] 如何配置 judge 模型与成本控制
    - [ ] 常见问题与排障

- 验收
  - [x] 一条命令可跑完评测并生成 JSON 报告
  - [ ] 报告包含 RAGAS 指标汇总与每条样本明细
  - [x] 支持和上一份报告对比并输出退化项
  - [x] 默认不依赖外部服务即可跑通 offline 指标
  - [x] 为什么要做 agentic RAG 系统的技术深度来自 contract 可控性 与可回归

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
  - [x] vector store 接口(Milvus)
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
- [x] 接入第 1 批语料
  - [x] Background.md
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
  - [x] 本地优先, 例如 Milvus
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

- [x] 给定 20 个种子问题, 80% 以上回答包含有效 citations
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

- [ ] 评测 tests 可一键运行并输出报告
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

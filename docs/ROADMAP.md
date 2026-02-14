# 开发计划

## Agentic RAG 技术亮点里程碑清单

下面按项目实际完成时间顺序整理 每一条都说明它解决了什么问题 以及为什么它重要

### Week 1 已完成 baseline 与工程骨架

- [x] 一键启动 UI 与 CLI 让任何人拉代码就能跑起来
- [x] 端到端闭环 ingest retrieve answer citations 把可回溯作为第一原则
- [x] secrets 全走环境变量 避免仓库泄露与本地配置混乱
- [x] 端到端 smoke test 固化最小回归入口 防止链路被改坏

### Week 2 已完成 语料接入与引用质量

- [x] 语料接入支持 markdown 与 pdf 把知识源扩展到常见格式
- [x] 分层切分 chunk 固化 section path 与来源定位 让 citations 能精确回指原文位置
- [x] embeddings provider 可切换并固化维度 让检索质量可控可对比
- [x] 20 题引用覆盖率评测 用最简单指标压住幻觉并驱动检索迭代

### Week 3 已完成 单 agent agentic loop 与可控性

- [x] query rewrite critique revise re retrieve 闭环 检索差就自动改写并重试
- [x] 工具调用与结构化 contract 输出 把可计算事实从 LLM 生成里剥离出去
- [x] decision log 与 tool traces 落盘 让每一步决策可解释可追踪
- [x] validator gates 证据一致性 数值一致性 拒答 fail fast 让错误早暴露
- [x] LangGraph 编排可选启用 纯函数与图编排双跑 保持可测试与可演进

### Week 4 已完成 评测体系与回归框架

- [x] RAGAS 集成与离线可跑指标 默认不依赖外部服务也能跑评测
- [x] 自定义指标补齐 citations coverage numeric consistency 等本项目关注点
- [x] 报告落盘与回归对比 读取上一份报告标记退化 让优化有数据证据

### Week 5 已完成 拒答机制与负样本评测

- [x] 负样本数据集 覆盖库外知识 无意义输入 恶意输入
- [x] refusal gate 强制在证据不足时拒答 并给 next actions 避免硬编
- [x] refusal rate 指标 让系统在可信度上可量化可回归

### Week 6 已完成 引用精准度与幻觉检测

- [x] citation precision 句粒度评测 衡量 answer 的每句是否被 contexts 支持
- [x] citation judge 支持 auto llm heuristic 三种模式 兼顾成本与可信度
- [x] hallucination rate in citations 指标 直接量化引用相关的幻觉占比

### Week 7 已完成 金融领域一致性

- [x] numeric consistency 自动对齐 answer 数字与工具输出 解决金融场景的数值可信度
- [x] glossary check 检测术语误用 约束领域表达一致性
- [x] domain consistency score 汇总为可追踪的指标 让领域质量可回归

### Week 8 已完成 混合检索与重排序 step1

- [x] Cross encoder reranking 对粗排结果精排 剔除语义相关但事实无关的噪音
- [x] Hybrid search BM25 稀疏 + 向量稠密 让专有名词绝对召回 同时保留语义理解
- [x] 产出阶段评测报告 写入 .artifacts/reports 并记录已做与未做
  - `python -m riskagent_rag.evaluation.run --stage step1 --stage-notes "rerank and hybrid"`

### Week 9 已完成 查询理解与智能路由 step2

- [x] Query expansion 多视角并行检索 覆盖不同表达与不同信息需求角度
- [x] Step back prompting 退一步抽象问题 先拿背景知识再回答细节
- [x] Sub question decomposition 把复杂问题拆成可检索可验证的子问题
- [x] Semantic router 依据意图选择索引与工具 让系统不再一招走天下
- [x] 产出阶段评测报告 写入 .artifacts/reports 并记录已做与未做
  - `python -m riskagent_rag.evaluation.run --stage step2 --stage-notes "query intelligence and routing"`

### Week 10 已完成 高级索引策略 step3

- [x] Parent child indexing small to big 以小 chunk 检索 以大 chunk 生成 兼顾精准与上下文完整
- [x] Summary indexing 为 section 生成摘要并索引 专门服务宏观总结类问题
- [x] HyDE indexing 为 chunk 生成假设性问题并索引 缓解 query 与文档表述不一致
- [x] 产出阶段评测报告 写入 .artifacts/reports 并记录已做与未做
  - `python -m riskagent_rag.evaluation.run --stage step3 --stage-notes "advanced indexing"`

### Week 11 已完成 Self RAG 与动态决策 step4

- [x] Adaptive retrieval 显式判断上下文是否足够 不够则继续检索或拒答
- [x] Self reflection scoring 引入 IsRel IsSup IsUse 等分级评分 输出可度量的反思信号
- [x] Grade docs and grade generation 在生成前后都做质量门控 把 agentic loop 变成可控的闭环
- [x] 产出阶段评测报告 写入 .artifacts/reports 并记录已做与未做
  - `python -m riskagent_rag.evaluation.run --stage step4 --stage-notes "self rag"`

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

备注 本项目优先保证本地可运行与可复现 但会补齐最小生产化闭环 包括接口契约 可观测性 成本控制 安全与质量门禁

## Week 计划

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
    - [x] `conda run -n LangChain python -m unittest tests.test_week1_rag_baseline`
  - 进度: Week 1 已完成
  - 为什么要做 先把启动方式和回归入口固定住
  - 不然你每改一次代码 都要花时间在环境和手工验证上
  - 为 Week 2 打基础 Week 2 要扩充语料和问题集
  - 需要稳定入口做回归对比 才知道引用质量到底有没有变好

#### Phase 0: 基础强化与项目骨架

**目标**: 先把工程化基础打牢 让后续迭代稳定可扩展

- [x] 确认 conda 环境 LangChain 可用 固化 Python 版本
- [x] 增加 requirements.txt 不 pin 版本 以当前环境为准
- [x] 增加最小测试框架 至少覆盖 1 条端到端 smoke test
- [x] 定义核心抽象
  - [x] 文档源与元数据 schema
  - [x] chunk schema
  - [x] embedding provider 接口
  - [x] vector store 接口(Milvus)
  - [x] graph state schema(LangGraph)
  - [x] retrieval 输出 schema 必须包含 citations

**验收标准**:

- [x] 项目可在本地一键启动或一键运行 demo
- [x] 无明文 secrets
- [x] 至少 1 条端到端测试可通过

### Week 2: RAG MVP 闭环与引用质量

- 交付
  - [x] corpus 语料接入(至少包含 Background.md)
  - [x] chunk 规则与 metadata schema 固化
  - [x] 20 个种子问题集
- 验收
  - [x] 20 个问题中, 80% 以上回答包含有效 citations
    - [x] `conda run -n LangChain python -m unittest tests.test_week2_rag_citation_quality`
  - 为什么要做 引用覆盖率是最简单也最管用的指标
  - 它能压住幻觉 也会逼着我们去优化检索和切分
  - 为 Week 3 打基础: Week 3 引入 agentic loop 时, 每条关键结论都必须能回指证据, 否则会放大幻觉.

#### Phase 1: RAG MVP 面向工程师的业务解释

**目标**: 跑通 ingest -> index -> retrieve -> generate 的闭环 输出带引用的解释结果

##### 1.1 资料与数据接入

- [x] 定义资料目录约定 例如 corpus
- [x] 接入第 1 批语料
  - [x] Background.md
  - [x] 公开可引用的 FRTB CVA Greeks XVA 资料
- [x] 文档解析
  - [x] markdown 解析
  - [x] pdf 解析

##### 1.2 切分与索引策略

- [x] chunk 策略
  - [x] baseline: 按长度切分
  - [x] 以标题层级优先 再按长度切分
  - [x] chunk 必须携带 section path 与来源定位
- [x] vector store
  - [x] 本地优先 例如 Milvus
- [x] embeddings
  - [x] MVP: FakeEmbeddings(离线可运行)
  - [x] Week 2: 切换为真实 embeddings 并固化 provider 与维度

##### 1.3 生成与引用

- [x] 统一回答模板 面向软件工程师
  - TLDR
  - 概念解释
  - 为什么重要
  - 在系统里的常见数据流与字段
  - 典型示例
  - citations
- [x] 引用规则
  - 每个关键结论必须能对应到至少 1 个 chunk
  - 模型不确定时必须说明不确定并给出下一步建议

##### 1.4 最小交互形态

- [x] CLI
  - [x] ingest(build_index)
  - [x] ask(demo_cli.py)
  - [x] chat(多轮对话)
- [x] 简单 Web UI 例如 Gradio

**验收标准**:

- [x] 给定 20 个种子问题 80% 以上回答包含有效 citations
- [x] 端到端流程可复现
  - [x] 清空索引 -> ingest -> 查询 -> 返回答案

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

#### Phase 2: 质量提升 可评测与可控(结构化与guardrails)

- [x] 增加结构化中间产物
  - [x] claims 与 evidence_set 作为一等公民
  - [x] validator 产出 failure_reason
- [x] 增加 guardrails
  - [x] 无法从语料支持则拒答或要求补充资料
  - [x] 敏感信息与合规提示
- [x] 领域知识增强
  - [x] 术语表与缩写表 (via Background.md)
  - [x] 业务对象字典 例如 position security desk trader

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
    - [x] 数据集文件建议
      - [x] tests/data/questions.json 作为最小数据集
      - [x] tests/data/eval_set.json 作为可扩展数据集
  - [x] RAGAS 指标集落地
    - [x] RAG triad
      - [x] context relevance
      - [x] faithfulness groundedness
      - [x] answer relevance
    - [x] retrieval metrics
      - [x] context precision
      - [x] context recall
    - [x] 设计约束
      - [x] 支持 offline baseline 先跑确定性指标
      - [x] 支持开启 LLM judge 模式用于更贴近人类评价
  - [x] 自定义指标补齐本项目关注点
    - [x] citations coverage
    - [x] citation precision 抽样或全量校验 evidence 是否支持 claim
    - [x] refusal quality 该拒答时必须拒答
    - [x] numeric consistency 报告数字必须等于 tool 输出
    - [x] failure taxonomy coverage 每类 failure_reason 至少 1 条用例
  - [x] 评测运行器与报告
    - [x] 一条命令运行评测
      - [x] conda run -n LangChain python -m riskagent_rag.evaluation.run
    - [x] 报告落盘
      - [x] JSON 报告包含 per sample 结果与汇总
      - [x] 报告路径建议放到 .artifacts 下的 reports 子目录
    - [x] 回归对比
      - [x] 支持读取上一份报告作为 baseline
      - [x] 支持阈值配置并标记 regression
  - [x] 文档与使用说明
    - [x] 如何新增评测样本
    - [x] 如何配置 judge 模型与成本控制
    - [x] 常见问题与排障

- 验收
  - [x] 一条命令可跑完评测并生成 JSON 报告
  - [x] 报告包含 RAGAS 指标汇总与每条样本明细
  - [x] 支持和上一份报告对比并输出退化项
  - [x] 默认不依赖外部服务即可跑通 offline 指标
  - [x] 为什么要做 agentic RAG 系统的技术深度来自 contract 可控性 与可回归

### Week 5: 拒答机制与负样本评测 (Refusal Quality)

#### Phase 3: Advanced Evaluation & Reliability (2026-02)

**目标**: 将 RAG 系统的"可信度"提升到金融生产级标准 重点解决拒答质量 引用精准度 领域一致性

- **交付**
  - [x] 构建负样本数据集 (Negative Dataset)
    - [x] 包含: 库外知识问题、无意义问题、恶意问题
  - [x] 优化 Refusal Gate
    - [x] 目标: 在 Evidence 不足时果断拒答, 并给出"Could not find evidence in corpus"的标准回复
  - [x] 评测指标: `refusal_rate`
    - [x] 正样本拒答率应趋近 0%
    - [x] 负样本拒答率应趋近 100%

### Week 6: 引用精准度与幻觉检测 (Citation Precision)

- **交付**
  - [x] 自动化 Citation Judge
    - [x] 支持 auto/llm/heuristic 三种模式
    - [x] LLM judge 逐句核对 Answer 是否被 contexts 支持
    - [x] heuristic judge 用确定性规则离线打分用于CI
  - [x] 评测指标: `citation_precision`
    - [x] 定义: supported_sentences / total_sentences (按句子粒度)
  - [x] 评测指标: `hallucination_rate_in_citations`
    - [x] 定义: 出现 unsupported_sentences 的回答占比

### Week 7: 金融领域一致性 (Domain Consistency)

- **交付**
  - [x] 数值一致性校验 (Numeric Consistency)
    - [x] 自动提取 Answer 中的关键数字, 与 contexts 进行比对
    - [x] 误差容忍度配置 (e.g., +/- 1%)
  - [x] 术语表一致性 (Glossary Check)
    - [x] 检测术语误用(基于禁用定义关键字)并计分
  - [x] 评测指标: `domain_consistency_score`

#### Phase 4: SOTA RAG Optimization

> 基于 Advanced RAG 理论图谱 持续提升检索与生成质量

### Week 8: 混合检索与重排序 step1

目标 先把检索侧做强 让同样的评测集在 citations precision 与 domain consistency 上立刻可见提升

- **交付**
  - [x] **Cross encoder reranking**
    - [x] 方案: 在 retriever 之后引入重排序模型 对粗排结果精排
    - [x] 目的: 剔除语义相关但事实无关的噪音 提升 citations precision
  - [x] **Hybrid search**
    - [x] 方案: BM25 稀疏检索 + vector 稠密检索 融合采用 RRF 或加权求和
    - [x] 目的: 确保专有名词绝对召回 同时保留语义理解
  - [x] **召回层增强**
    - [x] 多路召回配额化 基于 source 与 section 做去重与占比约束 避免单篇文档霸榜
    - [x] query aware hybrid 为 sparse 与 dense 构造不同形态查询 提升口语化提问的召回稳定性
  - [x] **粗排层增强**
    - [x] coarse scoring 在融合后加入轻量打分与过滤 把候选压缩到可控规模 再进入 cross encoder
    - [x] citation aware filter 过滤低信息密度 chunk 降低噪音提升 context precision
  - [x] **精排与重排增强**
    - [x] diversity rerank 在最终 topk 引入覆盖与多样性约束 覆盖多 source 多 section
    - [x] confidence signal 输出 rerank score 分布与 gap 作为后续自适应检索与拒答依据
  - [x] **阶段评测报告**
    - [x] 完成后运行并落盘到 .artifacts/reports
      - [x] `python -m riskagent_rag.evaluation.run --stage step1 --stage-notes "rerank and hybrid"`
- **验收**
  - [x] 仅用真实语料与真实 embeddings 与真实 reranker 跑通测试
    - [x] `python -m unittest tests.test_week8_hybrid_rerank_acceptance`
  - [x] 仅用真实语料与真实 embeddings 与真实 reranker 跑通新增验收测试
    - [x] `python -m unittest tests.test_week8_retrieval_highlights_acceptance`
  - [x] 产出 step1 评测报告并可与 baseline 对比
    - [x] `python -m riskagent_rag.evaluation.run --stage step1 --label step1 --enable-citation-judge --citation-judge-mode heuristic`

### Week 9: 查询理解与智能路由 step2

目标 让系统不再只有一招 通过并行检索与路由覆盖更多表达与更复杂的问题结构

- **交付**
  - [x] **Query expansion**
    - [x] 方案: 生成多个 query 变体 并行检索再融合
  - [x] **Step back prompting**
    - [x] 方案: 生成更抽象的背景 query 拉回基础定义与上下文
  - [x] **Sub question decomposition**
    - [x] 方案: 针对对比类问题拆解为多个子 query 再融合
  - [x] **Semantic router**
    - [x] 方案: 基于意图规则选择策略 例如 compare 背景 procedure
  - [x] **阶段评测报告**
    - [x] 完成后运行并落盘到 .artifacts/reports
      - [x] `python -m riskagent_rag.evaluation.run --stage step2 --label step2 --enable-citation-judge --citation-judge-mode heuristic`
- **验收**
  - [x] 仅用真实语料与真实 embeddings 跑通测试
    - [x] `python -m unittest tests.test_week9_query_routing_acceptance`
  - [x] 产出 step2 评测报告并可与 step1 报告对比
    - [x] `python -m riskagent_rag.evaluation.run --stage step2 --label step2 --enable-citation-judge --citation-judge-mode heuristic`

### Week 10: 高级索引策略 step3

目标 从索引结构层面解决长文档与宏观问题 切片太小丢上下文 切片太大语义模糊的矛盾

- **交付**
  - [x] **Parent child indexing small to big**
    - [x] 方案: 对 child chunk 做索引 检索命中后回填 parent chunk 给 LLM
    - [x] 目的: 兼顾检索精准度与生成上下文完整性
  - [x] **Summary indexing**
    - [x] 方案: 对每个 section 生成摘要并索引
    - [x] 目的: 专门响应宏观总结类问题 避免被细节淹没
  - [x] **HyDE indexing**
    - [x] 方案: 为 chunk 生成假设性问题 并对问题做索引
    - [x] 目的: 缓解 query 与文档表述不一致 以 question to question 匹配
  - [x] **阶段评测报告**
    - [x] 完成后运行并落盘到 .artifacts/reports
      - [x] `python -m riskagent_rag.evaluation.run --stage step3 --label step3 --enable-citation-judge --citation-judge-mode heuristic`
- **验收**
  - [x] 仅用真实语料与真实 embeddings 跑通测试
    - [x] `python -m unittest tests.test_week10_advanced_indexing_acceptance`
  - [x] 产出 step3 评测报告并可与 step2 报告对比
    - [x] `python -m riskagent_rag.evaluation.run --stage step3 --label step3 --enable-citation-judge --citation-judge-mode heuristic`

### Week 11: Self RAG 与动态决策 step4

目标 在生成前后引入显式打分与门控 把现有的 agentic loop 升级成可度量可控的动态决策系统

- **交付**
  - [x] **Adaptive retrieval**
    - [x] 方案: 基于检索评分信号决定是否继续检索 或拒答 或进入生成
  - [x] **Self reflection scoring**
    - [x] 方案: 引入 IsRel IsSup IsUse 等信号 输出可度量的反思结果
  - [x] **Grade docs and grade generation**
    - [x] 方案: retrieve grade docs generate grade generation loop if needed
  - [x] **阶段评测报告**
    - [x] 完成后运行并落盘到 .artifacts/reports
      - [x] `python -m riskagent_rag.evaluation.run --stage step4 --label step4 --enable-citation-judge --citation-judge-mode heuristic`
- **验收**
  - [x] 仅用真实语料与真实 embeddings 跑通测试
    - [x] `python -m unittest tests.test_week11_self_rag_acceptance`
  - [x] 产出 step4 评测报告并可与 step3 报告对比
    - [x] `python -m riskagent_rag.evaluation.run --stage step4 --label step4 --enable-citation-judge --citation-judge-mode heuristic`

---

## Phase 5: Productionization 可信上线闭环 (Week 12 - Week 13)

目标 把 demo 升级成可上线的 LLM 应用工程作品集 重点是契约 稳定性 安全 可观测 成本 与质量门禁

### Week 12: 服务化接口与契约 v1

- 交付
  - [x] HTTP API v1
    - [x] /v1/ask 单轮问答
    - [x] /v1/chat 多轮对话
    - [x] /healthz /readyz 健康检查
    - [x] /metrics 基础指标
  - [x] 请求与响应 schema 固化
    - [x] request_id 贯穿全链路
    - [x] 输出始终包含 evidence_set claims tool_traces decision_log
    - [x] 错误返回固定 error_code 与 retryable 标记
  - [x] 可选鉴权
    - [x] 支持 API key via HTTP header
- 验收
  - [x] 50 次连续请求无崩溃
  - [x] 所有响应可被 schema 校验
  - [x] 对同一输入在相同参数下输出结构稳定

### Week 13: 可观测性与调试体验

- 交付
  - [x] 统一日志字段
    - [x] request_id run_id model_id prompt_version retriever_version
  - [x] Trace contract 固化
    - [x] 每次 run 落盘 trace.json 包含节点耗时与关键中间产物路径
- 验收
  - [x] 任意一次失败都能从 trace 定位到 failure_reason 与责任节点

## 时间规划

里程碑按本地 demo 倒排.

| Milestone | 预计时间 | 验收输出 |
| --------- | -------- | -------- |
| Week 1 | 已完成 | baseline RAG demo + citations + smoke test |
| Week 2 | 已完成 | 真实 embeddings + 稳定 chunk_id + 20 题评测覆盖 |
| Week 3 | 已完成 | 业务场景多 agent MVP + 工具调用 + guardrails |
| Week 4 | 已完成 | 结构化输出落盘 + 评测升级 + 文档固化 |
| Week 5 | 已完成 | 负样本集 + Refusal Gate 优化 |
| Week 6 | 已完成 | Citation Precision 自动化评测 |
| Week 7 | 已完成 | 领域一致性校验 数值与术语 |
| Week 8 | 已完成 | 混合检索与重排序 step1 |
| Week 9 | 已完成 | 查询理解与智能路由 step2 |
| Week 10 | 已完成 | 高级索引策略 step3 |
| Week 11 | 已完成 | Self RAG 与动态决策 |
| Week 12 | 已完成 | HTTP API v1 + 契约 |

**总计** 12 周 含 Phase 4

## 开发建议

1. 每完成一个 Week 就提交 Git, 保持可回溯
2. 以数据口径与引用为第一优先级, 宁可少答也不要编造
3. 每周至少 1 次 demo, 记录输入输出与问题清单
4. 先做 CLI 后做 UI, 降低早期复杂度

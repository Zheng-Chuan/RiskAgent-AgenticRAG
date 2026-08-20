## 目录

- [1. 系统 Query 流程](#1-系统-query-流程)
  - [1.1 入口与上下文收敛](#1-系统-query-流程)
  - [1.2 LangGraph 工作流](#1-系统-query-流程)
  - [1.3 统一检索主链](#1-系统-query-流程)
  - [1.4 Query Intelligence](#1-系统-query-流程)
  - [1.5 Hybrid Retrieval](#1-系统-query-流程)
  - [1.6 Advanced Index](#1-系统-query-流程)
  - [1.7 数值型风险工具](#1-系统-query-流程)
  - [1.8 Critique 与 Query 修正](#1-系统-query-流程)
  - [1.9 Answer Synthesis 与 Gate 校验](#1-系统-query-流程)
  - [1.10 Artifacts 与 API 返回](#1-系统-query-流程)
  - [1.11 系统 Index 流程](#111-系统-index-流程)
  - [1.12 Source Loader 与 Ingestion](#111-系统-index-流程)
  - [1.13 Embeddings 初始化](#111-系统-index-流程)
  - [1.14 Milvus 与 Collection 准备](#111-系统-index-流程)
  - [1.15 增量更新判定](#111-系统-index-流程)
  - [1.16 Dense 与 Sparse 语料写入](#111-系统-index-流程)
  - [1.17 Summary 与 HyDE 产物构建](#111-系统-index-流程)
  - [1.18 Index Manifest 更新](#111-系统-index-流程)
- [2. 查询重写模块](#2-查询重写模块)
  - [2.1 模块定位](#21-模块定位)
  - [2.2 两层结构](#22-两层结构)
  - [2.3 技术与问题映射](#23-技术与问题映射)
  - [2.4 路由策略与触发条件](#24-路由策略与触发条件)
  - [2.5 组合收益与局限](#25-组合收益与局限)
- [3. 混合检索架构](#3-混合检索架构)
  - [3.1 架构目标](#31-架构目标)
  - [3.2 调用链路](#32-调用链路)
  - [3.3 核心算法与分数计算](#33-核心算法与分数计算)
  - [3.4 关键技术与优缺点](#34-关键技术与优缺点)
  - [3.5 为什么这样设计](#35-为什么这样设计)
  - [3.6 与 Numeric Consistency 和 Domain Consistency 的关系](#36-与-numeric-consistency-和-domain-consistency-的关系)
- [4. 多级索引架构](#4-多级索引架构)
  - [4.1 架构目标](#41-架构目标)
  - [4.2 Small-to-Big 索引分层](#42-small-to-big-索引分层)
  - [4.3 关键技术与作用分工](#43-关键技术与作用分工)
  - [4.4 调用链与打分逻辑](#44-调用链与打分逻辑)
  - [4.5 为什么要这样做](#45-为什么要这样做)
  - [4.6 优缺点与局限](#46-优缺点与局限)
  - [4.7 有什么更好的做法](#47-有什么更好的做法)
- [5. 自适应检索策略](#5-自适应检索策略)
  - [5.1 策略定位](#51-策略定位)
  - [5.2 具体技术组成](#52-具体技术组成)
  - [5.3 决策流程与停止条件](#53-决策流程与停止条件)
  - [5.4 为什么这样设计](#54-为什么这样设计)
  - [5.5 解决了什么问题](#55-解决了什么问题)
  - [5.6 缺点与风险](#56-缺点与风险)
  - [5.7 怎么改进](#57-怎么改进)
- [6. 质量门禁](#6-质量门禁)
  - [6.1 门禁边界](#61-门禁边界)
  - [6.2 运行时门禁链](#62-运行时门禁链)
  - [6.3 具体做了哪些门禁](#63-具体做了哪些门禁)
  - [6.4 为什么这样设计](#64-为什么这样设计)
  - [6.5 优缺点](#65-优缺点)
  - [6.6 怎么改进](#66-怎么改进)
- [7. 评估体系](#7-评估体系)
  - [7.1 为什么单独设计评估体系](#71-为什么单独设计评估体系)
  - [7.2 参考了业界哪些成果](#72-参考了业界哪些成果)
  - [7.3 三层评估结构](#73-三层评估结构)
  - [7.4 具体指标与计算方式](#74-具体指标与计算方式)
  - [7.5 Threshold Gate 与 Baseline Regression](#75-threshold-gate-与-baseline-regression)
  - [7.6 这个体系的缺点](#76-这个体系的缺点)
  - [7.7 系统 Evaluation 流程](#77-系统-evaluation-流程)
  - [7.8 数据集加载](#77-系统-evaluation-流程)
  - [7.9 Evaluation Run 初始化](#77-系统-evaluation-流程)
  - [7.10 评测前准备](#77-系统-evaluation-流程)
  - [7.11 样本执行主链](#77-系统-evaluation-流程)
  - [7.12 Retrieval Metrics](#77-系统-evaluation-流程)
  - [7.13 Citation Precision 与 Answer Eval](#77-系统-evaluation-流程)
  - [7.14 Domain Consistency 与 Gate Metrics](#77-系统-evaluation-流程)
  - [7.15 Threshold Gate](#77-系统-evaluation-流程)
  - [7.16 Reporting 与 Baseline Compare](#77-系统-evaluation-流程)

# 1. 系统 Query 流程
```text
[用户]
    | 发起 query
    v
[API / CLI 入口]
    | API 场景走 /v1/ask 或 /v1/chat
    | CLI 场景走 ask 或 chat 子命令
    | 生成 request_id
    | API 层做 Pydantic schema 校验
    | chat 场景把多轮 history 收敛成最近几轮上下文
    v
[RiskAgentSystem.chat]
    | 检查索引 manifest 是否存在
    | 根据 persist_dir 初始化或复用 retriever
    | 主路径固定为统一检索链路
    | 默认走 LangGraph
    | docs 只在图内流转 对外返回前会移除
    v
[LangGraph 工作流]
    |
    +-> [Step 1] rewrite
    |       | 用 LLM 把原始问题压缩成单个主检索 query
    |       | 目标是短 小 关键词化 偏领域术语 且尽量控制在 20 tokens 内
    |       | 输出写入 state.current_query 作为后续统一检索主链的 base query
    |       | 记录 decision_log 与 trace
    |       v
    +-> [Step 2] retrieve_and_critique
    |       |
    |       +-> [2.1] 统一检索主链
    |       |       | 构建时固定返回一条包装式检索链
    |       |       | AdvancedIndexRetriever
    |       |       | -> QueryIntelligentRetriever
    |       |       | -> HybridRetriever
    |       |       | 运行时不再切 dense only / hybrid / summary mode
    |       |       | 只是调 dense_k sparse_k candidate_k rerank_k summary_k hyde_k 等参数
    |       |       | 调用顺序是 Advanced 先接 query 然后把 query 传给 QueryIntel 再由 QueryIntel 调 Hybrid
    |       |       v
    |       +-> [2.2] query intelligence 默认发生
    |       |       | 这一层不是再产出新的全局 current_query
    |       |       | 而是围绕 current_query 生成多个检索 variants 并融合结果
    |       |       | a. route 识别: compare / background / procedure / default
    |       |       | b. 按 route policy 决定 fanout 强度 不是每题都全套扩写
    |       |       | c. default 默认只保留 base query 不盲目扩写
    |       |       | d. background 和 procedure 可启用 keywordize acronym expansion step back
    |       |       | e. compare 额外保留 decomposition 做子问题检索
    |       |       | f. variant 去重并按 route budget 截断后分别调用 hybrid retrieval
    |       |       | g. variant 结果再做一层 RRF 融合
    |       |       v
    |       +-> [2.3] hybrid retrieval 主体
    |       |       | dense 向量召回
    |       |       | sparse BM25 召回
    |       |       | 两路先做 RRF 融合并合并成统一候选集
    |       |       | 每个候选会补 dense_rank sparse_rank rrf_score bm25_score bm25_rank retrieval_sources
    |       |       | metadata_boost 来自 query token 与 source / section_path 的命中数
    |       |       | 每命中 1 个 token 加 0.05 最多记 3 次 上限 0.15
    |       |       | 低质量 chunk 会先过滤 例如过短 非文本 目录页 噪声页
    |       |       | coarse ranking 公式是 rrf_score + 0.5 * bm25_score + metadata_boost
    |       |       | 先按 rrf_score 截 candidate_k 再按 coarse_score 排序取 rerank_pool
    |       |       | rerank 用 cross-encoder 对 query 和 chunk 正文成对打分 写入 rerank_score
    |       |       | 若未配置 reranker 则直接用 coarse 结果进入 diversity select
    |       |       | diversity select 限制同 source 和同 section 的重复数量 再补齐 final_k
    |       |       v
    |       +-> [2.4] advanced index 默认发生
    |       |       | 这一层发生在 2.3 之后 不是并列分支 而是对 base docs 的二次补分与扩展
    |       |       | a. summary index: 对 parent summary 语料做 BM25 检索 补主题级信号
    |       |       | b. HyDE index: 对 hyde 语料做 BM25 检索 补 query-doc 表达差异
    |       |       | c. parent expand: 用 parent_id 找回更长上下文 但按 query route 和证据强度决定是否真的展开
    |       |       | d. advanced_index_score = base_score + summary_weight * summary_score + hyde_weight * hyde_score
    |       |       | e. compare background procedure 更积极扩 parent default 和 numeric 更保守
    |       |       | f. expand_parent_reason expand_parent_signal expand_parent_route 会写入 metadata
    |       |       | g. 最终按 final_k 收口返回 docs
    |       |       v
    |       +-> [2.5] 数值型风险工具按需追加
    |       |       | 识别 desk exposure / delta limit / breach 问题
    |       |       | 解析 desk as_of abs delta limit
    |       |       | 调 run_data_agent
    |       |       | tool_output 转成 Document 追加到 docs
    |       |       | tool_trace 写入 state.tool_traces 与 debug.numeric_tool
    |       |       v
    |       +-> [2.6] critique
    |               | LLM 判断当前 docs 是否足够回答问题
    |               | Self-RAG 先做题型感知 sufficiency scorer
    |               | 至少区分 definition compare numeric procedure
    |               | 结合 top_isrel query_coverage source_diversity parent_diversity numeric_evidence
    |               | 产出 sufficient / critique_reason / improved_query
    |               | insufficient 时进入 revise_query 循环
    |       v
    +-> [Step 3] revise_query
    |       | 若检索结果不足则修正 query
    |       | 回到 Step 2
    |       | 受 max_rounds 限制 防止死循环
    |       v
    +-> [Step 4] synthesize_answer
    |       | 严格基于 docs 生成答案
    |       | 若前一步命中数值型风险工具
    |       | 工具输出会以一类可引用上下文参与生成
    |       | 从 docs 中抽取 citations
    |       v
    +-> [Step 5] validate_and_save
    |       |
    |       +-> [5.1] gate 校验
    |       |       | refusal gate
    |       |       | evidence gate
    |       |       | numeric gate
    |       |       | 若存在 tool_traces
    |       |       | 则把计算型数字和工具输出做一致性比对
    |       |       | question 命中 numeric backing 条件时要求更硬证据
    |       |       | appeal 默认关闭
    |       |       | 只有显式设置 RISKAGENT_ENABLE_LLM_APPEAL=true 才会启用
    |       |       v
    |       +-> [5.2] 结构化结果
    |       |       | answer + citations + claims + evidence_set
    |       |       | decision_log + debug + failure_reason + tool_traces
    |       |       v
    |       +-> [5.3] 落盘 artifacts
    |               | 单文件 artifact
    |               | bundle 目录下 request response structured_response trace
    |               | trace 写 retriever_version prompt_version model_id
    |               v
[API 返回]
    | 返回 answer citations claims evidence_set decision_log status
    | docs 不对外暴露
    v
[用户]
```

## 1.11 系统 Index 流程
```text
[corpus]
    | md / pdf 等原始文档
    v
[source_loader]
    | 解析文档并保留 source page file_type 等基础 metadata
    | line metadata 主要在后续 ingestion 阶段补齐
    v
[ingestion]
    | build_parent_documents
    | split_documents
    | 形成 parent 和 chunk 两层语料
    v
[embeddings]
    | 默认 provider = hf
    | 默认模型来自 settings.embeddings.model_name
    | 优先尝试项目本地 models/embeddings/<model>
    | 否则按模型名离线加载 HuggingFace 缓存
    | local_files_only = true
    | 离线回归可切到 hash embeddings
    v
[incremental_index]
    |
    +-> 先 build_embeddings
    |    用 embed_query("dim_probe") 计算向量维度
    |
    +-> build_milvus_client
    |    若设 MILVUS_URI 或 host/port 则连外部 Milvus
    |    否则默认写 .milvus/milvus.db
    |
    +-> 计算源文件 sha1
    |    先结合 manifest 里的 schema_fingerprint 判断是否需要全量重建
    |    schema 未变化时再按 source sha1 决定 indexed / skipped
    |
    +-> ensure_collection
    |    collection 维度由 embeddings 实测决定
    |
    +-> 对每个发生变化的 source
    |    先 delete_by_source 再重建该 source 的全部索引产物
    |
    +-> 写 dense rows 到 Milvus
    |    chunk_id vector text source parent_id section_path 等一起入库
    |
    +-> 写 sparse_corpus.jsonl
    |    给 BM25 / sparse 检索使用
    |
    +-> 写 parent_corpus.jsonl
    |    给 parent expand 使用
    |
    +-> 写 summary_corpus.jsonl
    |    给 summary index 使用
    |
    +-> 写 hyde_corpus.jsonl
    |    给 advanced index 使用
    |
    +-> 更新 index_manifest.json
         记录 schema version schema_fingerprint
         记录 embeddings milvus chunking advanced index features 等版本键
         记录每个 source 的 sha1 和 chunks parents summaries hydes
```

# 2. 查询重写模块

## 2.1 模块定位

查询重写模块的目标不是直接回答问题. 它的职责是把用户语言变成更适合检索系统消费的查询表达. 在这个项目里, 它主要解决 4 类断层.

- 用户自然语言和索引表达之间的词汇断层
- 金融缩写和文档全称之间的术语断层
- 复合问句和单次检索之间的结构断层
- 背景类问题和细粒度 chunk 之间的语义粒度断层

这也是为什么主链不是只做一次 `rewrite_query`. 当前实现实际上分成两层.

## 2.2 两层结构

### 第一层. 主检索 Query Rewrite

- 入口在 `rewrite` 节点
- 用 LLM 把原始问题压缩成单个 base query
- 目标是短, 小, 关键词化, 领域词优先, 尽量控制在 20 tokens 内
- 这一层解决的是 first hop 检索对齐问题

### 第二层. Route Aware Query Intelligence

- 入口在统一检索链里的 `query intelligence`
- 不再改写全局 `current_query`
- 而是围绕 base query 生成多个 query variants
- 再对每个 variant 独立检索, 最后做 variant level RRF 融合

两层的分工很明确.

- 第一层负责把问题改写成一个可检索的主查询
- 第二层负责按题型补充搜索视角, 降低单 query 漏召回

## 2.3 技术与问题映射

下面这张表对应图片里提到的几种关键技术. 其中 `step back` 在本项目里不是重型 LLM prompting, 而是规则化生成一个更泛化的背景查询, 这样写和当前实现是一致的.

| 技术 | 当前实现方式 | 主要解决什么问题 | 优点 | 缺点 |
| --- | --- | --- | --- | --- |
| Base query rewrite | LLM 把原问题压缩成短 query, 保留领域术语和关键词 | 用户提问啰嗦, 聊天式表达过长, embedding 检索不稳定 | 对 first hop 很有效, 能快速把问题拉回检索空间, 对多轮 chat 收敛也友好 | 依赖 LLM 输出稳定性, 若改写过度会丢细节, 失败时只能回退原问题 |
| Keywordize | 去停用词, 保留高信息密度 token | 自然语言里功能词太多, 有效检索词密度不够 | 成本低, 可解释, 对中英混合也比较稳 | 语义压缩比较粗糙, 容易丢掉关系词和限定条件 |
| Acronym Expansion | 识别 `FRTB` `CVA` `XVA` `VaR` `ES` 等缩写并拼接全称 | 金融缩写和文档正文全称不一致, 导致 lexical sparse 召回漏掉 | 对金融文档很实用, 尤其能补 BM25 和 metadata match | 词表覆盖有限, 新缩写和业务别名需要持续维护, 错扩会引入噪声 |
| Step back | 基于 base query 生成更泛化的 `overview definition background ...` 查询 | 背景类和流程类问题太抽象, 直接搜细节 chunk 容易拿不到总览证据 | 能补充定义性和背景性文档, 对 overview 类问题收益明显 | 泛化过强时会把检索拉宽, 可能带来更多弱相关背景材料 |
| Decomposition | 用连接词和分隔符把复合问句拆成多个子查询 | compare 类和复合问题往往包含多个检索意图, 单 query 难以同时命中 | 可以显著降低跨文档 compare 漏召回, 让子问题各自命中文档 | 当前实现偏规则化, 容易误拆, 错拆后会放大召回噪声 |
| Route recognition | 根据 query 判断 `compare` `background` `procedure` `default` | 不是每题都值得全量扩写, 盲目 fanout 会增加噪声和成本 | 让扩写强度和题型绑定, 控制预算, 提高稳定性 | 规则路由有误判风险, 特别是中文口语化问句和混合表达 |
| Variant fusion | 每个 variant 独立检索后, 用 RRF 做结果融合 | 单一路径检索结果脆弱, 某个 query 偏掉就会漏掉关键证据 | 对多视角召回很稳, 不依赖单个 variant 绝对正确 | fanout 越多, 计算成本越高, 也更依赖后续 rerank 和 diversity select 控噪 |

## 2.4 路由策略与触发条件

当前不是每个问题都跑全套扩写. 这是这个模块最关键的工程 trade off.

| 路由 | 典型问题 | 默认启用的技术 | 这样设计的原因 |
| --- | --- | --- | --- |
| `default` | 普通事实问答, 已经很明确的定点问题 | 只保留 base query | 避免过度 fanout, 降低噪声和成本 |
| `background` | 是什么, 定义, 介绍, overview 类问题 | keywordize, acronym expansion, step back | 这类问题需要总览性证据, 不能只盯细粒度 clause |
| `procedure` | 公式, 计算, 怎么算, calculation 类问题 | keywordize, acronym expansion, step back | 这类问题既要术语命中, 又要补流程和方法背景 |
| `compare` | 区别, 对比, difference, vs 类问题 | keywordize, acronym expansion, step back, decomposition | 对比题通常隐含多个子意图, 单 query 最容易漏召回 |

这个策略背后的核心判断是.

- `default` 问题最怕过度扩写
- `background` 和 `procedure` 最怕只命中碎片 chunk, 却拿不到背景定义
- `compare` 最怕把多个问题硬塞进一次检索

## 2.5 组合收益与局限

把这些技术组合起来之后, 查询重写模块解决的不是某一个点问题, 而是一整条检索链前端的意图对齐问题.

### 组合收益

- `base rewrite` 先把自然语言压缩成一个稳定的主查询
- `acronym expansion` 解决金融缩写和正文全称不对齐
- `step back` 解决背景类和流程类问题的语义粒度不匹配
- `decomposition` 解决 compare 类和复合问句的结构失真
- `route policy` 避免每题都全量 fanout
- `variant fusion` 让多视角召回汇总成一个更稳的候选集

### 当前局限

- `decomposition` 目前依赖 regex 和连接词切分, 对复杂金融复合句仍然可能误拆
- `acronym expansion` 目前是静态词表, 对 desk 内部缩写和业务别名覆盖还不够
- `route recognition` 目前是轻量规则, 还不是 learned router
- `step back` 当前是规则化泛化 query, 不是更强的生成式 step back prompting
- 多 variant 检索天然会增加召回成本, 后续需要依赖 rerank 和评测来证明收益

### 为什么这个方案适合当前阶段

- 它比每题都让 LLM 生成很多 rewrite 更便宜, 更稳定, 更容易审计
- 它比只做一次 rewrite 更能处理金融缩写, compare 问题, 跨文档背景问题
- 它也保留了继续演进的空间, 比如后面可以补缩写词典, variant level ablation, learned router

# 3. 混合检索架构

## 3.1 架构目标

混合检索架构的核心目标是同时解决 dense 检索和 sparse 检索各自的偏科问题.

- dense 检索擅长语义相似, 但对精确术语, 缩写全称, 章节名命中不够稳定
- sparse 检索擅长关键词和词面重合, 但对改写表达, 同义说法, 跨文档语义泛化容易漏召回
- 单一路径排序的波动会直接传导到生成和 gate, 让证据基础不稳定

所以当前实现不是在 dense 和 sparse 之间二选一, 而是按下面的流水线串起来.

`Dense Milvus -> Sparse BM25 -> RRF -> metadata boost -> coarse ranking -> Cross-Encoder rerank -> diversity select`

## 3.2 调用链路

当前调用链是分层包装的.

- `build_retriever` 先构造 `DenseMilvusRetriever`
- 然后把稀疏语料加载进 `HybridRetriever`
- `HybridRetriever` 内部先调用 dense 召回, 再调用 BM25 召回
- 两路结果做 RRF 融合和粗排
- 之后进入 Cross-Encoder 精排
- 最后做 diversity select, 把结果收口为最终候选

从代码上看, 混合检索真正的执行顺序是.

1. `DenseMilvusRetriever.invoke(query)` 把 query 编码成向量, 调 Milvus 搜 topk
2. `HybridRetriever._sparse_query(query)` 对 query 去重分词, 给 BM25 用
3. `BM25Okapi.get_scores(q_toks)` 对整个 sparse corpus 打分并取 topk
4. `rrf_scores([dense_keys, sparse_keys], k=rrf_k)` 融合 dense 排名和 sparse 排名
5. 计算 `metadata_boost`
6. 先按 `rrf_score` 截 `candidate_k`
7. 再按 `coarse_score` 排序取 `rerank_k`
8. `CrossEncoder.predict([(query, chunk_text)])` 做 pairwise 精排
9. `diversity_select` 按 source 和 section 限额选出最终 `final_k`

这里有一个很重要的工程细节.

- `candidate_k` 控制融合后保留多大候选池
- `rerank_k` 控制 Cross-Encoder 的计算预算
- `final_k` 控制最后进入回答和后续 advanced index 的文档数

这 3 个参数把召回广度, 精排成本, 结果收口拆开了, 这样可调性更强.

## 3.3 核心算法与分数计算

### 1. Dense 召回

- query 先经过 embedding 模型编码
- 然后送进 Milvus 做向量近邻搜索
- 返回 `dense_rank` 和可选的 `dense_score`

它解决的是语义召回问题. 比如用户写法和文档原文不完全一致时, dense 往往更容易先捞到相关 chunk.

### 2. Sparse 召回

- sparse 侧使用 `BM25Okapi`
- 文档语料来自持久化的 `sparse_corpus.jsonl`
- query 会先分词去重, 最多保留前 24 个 token
- BM25 原始分数会按当前 topk 最大值做归一化

归一化公式是.

```text
bm25_score(key) = raw_bm25_score(key) / max_topk_bm25_score
```

这样处理的作用是把 BM25 分数压到更稳定的量纲里, 方便后面和其他分量一起参加粗排.

### 3. RRF 融合

RRF 的实现非常直接.

```text
rrf_score(key) = sum(1 / (rrf_k + rank_i))
```

在当前代码里, `rank_i` 实际是从 1 开始的名次, 默认 `rrf_k = 60`.

RRF 只看排名, 不直接吃 dense score 和 BM25 raw score. 这样做的原因是.

- dense 和 BM25 的原始分数量纲不一致
- 直接线性混加很容易被某一路的分数尺度劫持
- RRF 对 top rank 更敏感, 对分值校准要求低, 工程上更稳

它的缺点也很明显.

- 只用 rank, 会丢掉原始分数里的强弱差距
- 如果两路排序都一般, RRF 只是稳, 不是自动变强

### 4. Metadata Boost

当前实现还会给命中 `source` 和 `section_path` 的 query token 一个小额加分.

```text
metadata_boost = min(0.15, 0.05 * hit_count)
```

其中.

- 每命中 1 个 token 加 `0.05`
- 最多记 3 次
- 所以上限是 `0.15`

它主要解决这类问题.

- query 明确提到了章节词, 机构名, 文档名
- 正文语义接近, 但标题和 section 更能说明这就是用户想找的证据位置

这样算的好处是.

- boost 很小, 不会压倒主排序
- 但足够在边界样本里把更像目标章节的 chunk 往前推一点

缺点是.

- 这是启发式规则, 依赖 metadata 质量
- 如果 section_path 噪声大, boost 也会放大噪声

### 5. Coarse Score

融合后的粗排分数公式是当前架构里最关键的一步.

```text
coarse_score = rrf_score + 0.5 * bm25_score + metadata_boost
```

这 3 项的含义分别是.

- `rrf_score` 代表 dense 和 sparse 排名共识
- `0.5 * bm25_score` 代表对词面精确匹配的额外偏好
- `metadata_boost` 代表对 source 和 section 命中的轻微纠偏

为什么 `bm25_score` 前面是 `0.5`.

- 如果直接加满 1.0, 稀疏词面匹配太容易压过 dense 和 RRF 的共识
- 如果权重太小, sparse 的补充价值又发挥不出来
- `0.5` 本质上是在表达一种偏好, 词面匹配重要, 但不能凌驾于双路共识之上

这里要注意, 当前仓库里没有把这个权重写成论文式推导. 它更像一个经验型工程权重.

### 6. Cross-Encoder 精排

粗排之后, 系统不会立刻返回结果, 而是对 `rerank_pool` 里的每个 `(query, chunk)` 对做 Cross-Encoder 打分.

```text
rerank_score = CrossEncoder.predict(query, chunk_text)
```

它和 dense 的差别是.

- dense 通常是双塔编码, 适合大规模召回
- Cross-Encoder 是 query 和 chunk 一起编码, 适合小候选集精排

这样做的原因是.

- 召回阶段强调覆盖率
- 精排阶段强调局部判别力
- 两者分工更合理

优点.

- 对法规条款, 术语定义, 近义表达的精细排序更强
- 能明显改善 top few 的相关性

缺点.

- 成本高, 只能跑在 `rerank_k` 个候选上
- 更依赖本地模型可用性
- 如果候选池本身已经漏掉 gold, 精排也救不回来

### 7. Diversity Select

图里提到了 MMR 多样性重排. 当前项目的工程落地更准确地说, 是一个基于配额的 diversity select.

- 默认 `max_per_source = 2`
- 默认 `max_per_section = 1`
- 先按排序从前往后选
- 如果某个 source 或 section 超配额就跳过
- 不够再做回填

它的目标是避免 final topk 全部来自同一篇文档或同一节, 让后续回答有更好的证据覆盖.

优点.

- 简单, 稳定, 成本低
- 对背景题和综合题很有帮助

缺点.

- 严格来说这不是经典 MMR 的相似度优化版本
- 对 very local 的条款问题, 多样性约束可能伤害 recall

## 3.4 关键技术与优缺点

| 技术 | 在当前架构里的作用 | 优点 | 缺点 |
| --- | --- | --- | --- |
| Milvus Dense Retrieval | 提供语义召回主干 | 对改写表达和语义近邻友好, 适合 first pass recall | 对精确术语和标题词面不够敏感 |
| BM25 Sparse Retrieval | 补足关键词和术语命中 | 对法规名, 缩写全称, 章节标题命中稳定 | 对同义改写和表达变化不够鲁棒 |
| RRF | 融合 dense 和 sparse 两路排序 | 不依赖分值校准, 工程上稳, 易解释 | 丢失原始分值差异, 只是稳健融合不是强语义建模 |
| Metadata Boost | 用 `source` 和 `section_path` 做小幅纠偏 | 对章节名和文档名查询很有效, 成本几乎为零 | 启发式强, 依赖 metadata 质量 |
| Cross-Encoder | 对小候选池做精排 | Top few 相关性明显更强, 对最终回答帮助大 | 推理成本高, 无法替代大规模召回 |
| Diversity Select | 限制 source 和 section 重复 | 提高证据覆盖, 缓解同源堆叠 | 对局部精确问答可能带来误伤 |

## 3.5 为什么这样设计

这个组合方案本质上是在平衡 4 件事.

- 召回率
- 排序稳定性
- 推理成本
- 证据多样性

如果只用 dense.

- 语义能力强
- 但会漏掉一些关键词极强的法规和术语定位

如果只用 BM25.

- 词面命中强
- 但用户表达一改写就容易掉

如果把 dense score 和 BM25 raw score 直接线性混合.

- 理论上更精细
- 但工程里很依赖分数量纲校准, 不如 RRF 稳

如果直接让 Cross-Encoder 排全量语料.

- 相关性也许更强
- 但成本完全不可接受

所以现在的设计思路是.

- 用 dense 和 sparse 先把候选池做宽
- 用 RRF 先做稳健融合
- 用粗排分数把 lexical precision 和 metadata hint 补进去
- 用 Cross-Encoder 只精排小池子
- 用 diversity select 给最终答案保留多源证据

## 3.6 与 Numeric Consistency 和 Domain Consistency 的关系

图里提到 `Numeric Consistency Score` 和 `Domain Consistency`. 这里需要特别说明边界.

- 它们不是混合检索内部的排序算法
- 它们属于评测和门禁侧的下游指标
- 当前项目里 `domain_consistency_score = (numeric_consistency_score + glossary_consistency_score) / 2`

混合检索和这些指标的关系是间接的.

- 更稳定的召回和精排, 能让后续生成拿到更可靠的证据上下文
- 证据更稳, 数字抄错, 术语漂移, 引用错位的概率通常会下降
- 所以下游的 numeric consistency 和 domain consistency 往往会随之改善

但要避免把因果说过头.

- 这些指标提升不是由 RRF 或 Cross-Encoder 直接计算出来的
- 它们是整条证据链变稳之后的评测结果
- 具体提升幅度, 比如图里写的百分比, 应该被当成实验观察值, 不是算法保证

# 4. 多级索引架构

## 4.1 架构目标

多级索引架构的核心目标是解决 chunk 检索天然存在的 3 个问题.

- 小 chunk 适合精确召回, 但上下文容易碎
- 大文档适合回答和解释, 但直接拿来检索噪声太大
- 用户 query 和文档表达之间经常有主题粒度差异, 只靠单一索引层很难兼顾

所以当前项目不是只建一个向量索引就结束了, 而是把不同粒度和不同用途的索引产物都物化出来, 再在统一检索主链里按需使用.

这套思路本质上就是 `Small-to-Big`.

- 先用小粒度 child chunk 做高精度召回
- 再用 parent summary 和 HyDE 补主题信号与表达信号
- 最后在必要时回填 parent 上下文, 把证据从小片段拉回可回答的语境

## 4.2 Small-to-Big 索引分层

当前索引侧会物化 4 类核心语料.

| 语料 | 文件 | 主要用途 |
| --- | --- | --- |
| Child chunks | `Milvus + sparse_corpus.jsonl` | 主检索入口, 提供高精度召回 |
| Parent corpus | `parent_corpus.jsonl` | 回填更长上下文, 缓解 chunk 碎片化 |
| Summary corpus | `summary_corpus.jsonl` | 提供主题级信号, 补 overview 和背景类召回 |
| HyDE corpus | `hyde_corpus.jsonl` | 提供表达级信号, 缓解 query 和文档措辞不一致 |

它们之间的关系可以理解成.

- `child` 负责找得准
- `summary` 负责找得宽一些但仍然围绕主题
- `hyde` 负责补 query-doc 表达差异
- `parent` 负责让最终证据变得可读可答

这也是为什么图片里会说把 `Parent-Child` `Summary Index` `HyDE` 和 `Query Rewrite` 收口到统一检索主链.

- `query rewrite` 先把用户问题改写成更适合检索的表达
- `hybrid retrieval` 先在 child 层找候选
- `advanced index` 再用 summary 和 hyde 给 parent 级别补信号
- `parent expand` 最后把证据从 small 拉回 big

## 4.3 关键技术与作用分工

### 1. Parent-Child

当前 ingestion 会先构建 parent 文档, 再把文档切成 child chunks.

- child chunk 用来做 dense 和 sparse 检索
- 每个 chunk 都带 `parent_id`
- parent 文档单独持久化到 `parent_corpus.jsonl`

它解决的问题是.

- 小 chunk 更容易对齐 query
- 但回答时不能只给模型喂碎片
- 需要一个稳定的上级上下文容器把多个碎片挂回去

优点.

- 检索和回答分工清楚
- 对法规文档和长说明文档很友好
- 比直接拿大 chunk 做召回更稳

缺点.

- 需要额外维护 parent-child 一致性
- parent 切分策略如果不稳, 后续 expand 效果也会漂

### 2. Summary Index

当前 summary 不是 LLM abstractive summary, 而是 extractive summary.

- 优先取前 12 行
- 不够再按句子拼接
- 最长默认截到约 900 chars

然后这些 summary docs 会单独建立 BM25 语料, 在 advanced index 阶段用来给 parent 打主题分.

它解决的问题是.

- 原始 child chunk 太细, 宏观主题不明显
- 背景类 query 经常需要主题级而不是句子级匹配

优点.

- 成本低
- 构建稳定
- 可解释性强

缺点.

- extractive summary 对文档头部质量很敏感
- 如果关键信息不在前几段, summary 信号会偏弱
- 它更像主题 hint, 不是完整语义建模

### 3. HyDE Index

当前 HyDE 不是在线让 LLM 生成假设答案, 而是离线为每个 parent 构造一条假设性问题.

生成逻辑比较轻量.

- 优先利用 `section_path`
- 再从 parent 文本里抽一个短 summary
- 拼成类似 `What is ... and why does it matter ...` 的问题表达

然后这些 hyde docs 也会单独走 BM25.

它解决的问题是.

- 用户 query 常常是问题句
- 原文档常常是定义句, 说明句, 或法规条款句
- 两边表达形态不一致时, 纯 child lexical match 容易漏掉

优点.

- 不依赖在线生成
- 比直接拿正文做 sparse 匹配更贴近用户问法
- 对 question-style query 很有补偿作用

缺点.

- 当前 HyDE 模板是规则生成, 不是语义很强的生成式 HyDE
- 模板化太重时, 可能引入同质化表达
- 如果 section_path 本身质量不高, hyde 也会跟着失真

### 4. Parent Expand

当前不是所有命中的 child 都无脑展开 parent. 系统会按 route 和证据强度决定是否展开.

- `compare` `background` `procedure` 更积极
- `default` 和 `numeric` 更保守
- 同时看 `parent_signal` `confidence_gap_to_top1` `chunk_len`

它解决的问题是.

- 检索阶段需要小 chunk
- 生成阶段需要够长的上下文
- 如果不受控地全量展开, 噪声和 token 成本都会失控

优点.

- 兼顾 recall 和 context completeness
- 把 expand 变成可控策略而不是固定动作

缺点.

- 当前仍是启发式规则
- 可能出现该扩没扩, 或不该扩却扩了的边界样本

## 4.4 调用链与打分逻辑

多级索引不是独立跑一套检索, 而是叠在混合检索之后.

完整顺序可以概括成.

1. `query rewrite` 生成 base query
2. `query intelligence` 生成 variants
3. `hybrid retrieval` 在 child chunk 层做 dense + sparse + rerank
4. `advanced index` 基于 parent 级 summary 和 hyde 再补分
5. 满足条件时做 `parent expand`
6. 按 `advanced_index_score` 重排并收口

其中 advanced index 的核心分数公式是.

```text
advanced_index_score = base_score + summary_weight * summary_score + hyde_weight * hyde_score
```

默认参数是.

- `summary_weight = 0.35`
- `hyde_weight = 0.35`

这里的 3 个分量分别表示.

- `base_score` 来自已有主检索结果, 优先取 `rerank_score`, 否则退到 `coarse_score`, 再退到 `rrf_score`
- `summary_score` 来自 summary BM25 topk 归一化后的 parent 分数
- `hyde_score` 来自 hyde BM25 topk 归一化后的 parent 分数

为什么这样算.

- `base_score` 仍然是主干, 防止 advanced index 把主检索完全推翻
- `summary` 和 `hyde` 只做补分, 不是另起炉灶
- 两个辅助项权重相同, 表达的是主题补偿和表达补偿在当前阶段同等重要

它的优点是.

- 结构简单
- 易解释
- 不容易让某个辅助索引直接 dominate 主排序

它的缺点是.

- 这仍然是启发式加权
- 不同分数项量纲并不完全等价
- 后续如果要更强, 需要做 calibration 或 learned fusion

Parent expand 的触发也不是拍脑袋.

- 先根据 query 识别 route
- 不同 route 配不同 `max_docs` `max_chars` `min_parent_signal` `max_gap_to_top1`
- 只有满足策略条件才会写入 `expanded_text`

这一步的核心思想是.

- `compare` `background` `procedure` 更可能需要大上下文
- `numeric` 问题更怕把无关解释扩进来, 所以阈值更严
- `default` 问题默认尽量克制, 只在 evidence signal 足够强时才扩

## 4.5 为什么要这样做

这套架构的根本原因是, 单层索引很难同时满足下面几个目标.

- 既要检索精确
- 又要上下文完整
- 既要对主题类问题有感知
- 又要对用户问法和文档写法不一致有补偿

如果只保留 child chunk.

- 召回会比较准
- 但回答常常碎

如果直接用 parent 做主检索.

- 上下文更完整
- 但大段文本噪声更高, 排序更不稳

如果没有 summary index.

- 背景类和 overview 类问题更容易只命中局部条款, 看不到主题全貌

如果没有 HyDE index.

- query 和文档表达形式一变, sparse 补偿能力会下降

如果每个命中 chunk 都无脑 expand parent.

- token 成本会上去
- 噪声也会上去

所以当前方案不是追求某一个点最强, 而是把 retrieval pipeline 拆成多阶段和多粒度协同.

## 4.6 优缺点与局限

### 优点

- 把检索粒度和回答粒度解耦
- 对长文档和法规文档更友好
- 对背景题, compare 题, 表达漂移题更稳
- 每层都有物化产物, 便于调试和回放

### 缺点

- 索引产物更多, 一致性治理更复杂
- 需要 manifest 和 source sha1 保证多份语料一起更新
- 现在的 summary 和 hyde 都偏规则化, 还不是最强版本
- 融合权重和 expand 策略仍然偏启发式

### 当前局限

- summary 依赖 extractive heuristic, 对文档结构质量敏感
- hyde 是模板生成, 不是生成式语义扩展
- parent expand 还不是 learned policy
- 多级索引提升的是 evidence coverage, 不是对所有题型都一定有收益

## 4.7 有什么更好的做法

如果后面继续演进, 我认为有 4 条路会比当前方案更强.

### 1. 学习式融合替代启发式加权

现在是.

```text
advanced_index_score = base_score + 0.35 * summary_score + 0.35 * hyde_score
```

更好的做法是.

- 统一做分数校准
- 用 qrels 训练一个 lightweight rank fusion 或 learning to rank 模型
- 按题型学习不同权重

这样能减少手工权重的脆弱性.

### 2. 生成式 Summary 和更强 HyDE

现在的 summary 和 hyde 都偏轻量模板化.

更好的做法是.

- 对 parent 生成 query independent 的高质量摘要
- 或者按 query 动态生成 query aware summary
- 用真正的生成式 HyDE 或 pseudo answer expansion 替代模板问题句

这样表达补偿会更强, 但成本和稳定性风险也更高.

### 3. Learned Parent Expand Policy

现在 parent expand 主要看规则阈值.

更好的做法是.

- 把 `route` `confidence_gap` `chunk_len` `summary_score` `hyde_score` 做成特征
- 学一个 expand / not expand 的轻量决策器
- 或者直接让 query aware context packing 决定扩多少

这样能减少阈值 hard code.

### 4. 更细粒度的 Evidence Unit

现在 parent-child 已经比单层 chunk 强很多, 但仍然是比较粗的层次.

更好的做法是.

- 对法规类文档引入 clause-level 或 evidence-unit level 索引
- 让 child 之下再有一层更细粒度证据单元
- 回答时再动态向上拼回 parent

这会让 recall 和 citation precision 都更硬, 但索引和评测复杂度会明显上升

整体上看, 当前这套多级索引架构不是终局方案, 但它有一个很实际的优点.

- 先用低风险和高可解释性的方式解决 chunk 碎片化
- 再给后续 learned routing learned fusion 和 query aware summarization 留出升级空间

# 5. 自适应检索策略

## 5.1 策略定位

这里说的自适应检索, 在当前项目里不是指运行时在很多检索 mode 之间来回切换. 更准确地说, 它是统一主链上的动态决策层.

- 主检索链路始终还是 `rewrite -> hybrid retrieval -> advanced index`
- 自适应部分负责判断当前证据是否已经够回答
- 如果不够, 再决定是否继续下一轮检索和 query 修正
- 如果够了, 就提前停止, 不再多跑一轮

所以它的核心不是换模型, 而是做 `continue / stop / revise` 的受控循环.

这也是图片里说的 `Early Stopping` 的真实工程含义.

- 不在首轮就盲目停止
- 也不默认把所有轮次跑满
- 只在证据充分时停, 不充分时才进入 revise loop

## 5.2 具体技术组成

当前自适应检索策略主要由 4 个技术部件组成.

### 1. Self-RAG 文档充分性评分

这是当前 adaptive retrieval 的第一层判断器.

- 对每轮检索出来的 docs 做 `grade_docs`
- 先识别题型, 至少区分 `definition` `compare` `procedure` `numeric` `default`
- 再计算一组轻量但可解释的指标

当前会计算一组轻量但可解释的指标.

- `top_isrel`
- `avg_isrel`
- `query_coverage`
- `claim_coverage`
- `source_diversity`
- `parent_diversity`
- `numeric_evidence`
- `top_claim_score`
- `redundancy_penalty`

其中直接参与 `sufficient` 判停的核心指标主要是.

- `top_isrel`
- `query_coverage`
- `claim_coverage`
- `source_diversity`
- `parent_diversity`
- `numeric_evidence`
- `top_claim_score`

`avg_isrel` 和 `redundancy_penalty` 当前也会被计算并输出, 但不直接进入 `sufficient` 的 stop / continue 判定.

这些指标的作用分工很明确.

- `query_coverage` 看 query 核心 token 有没有被整体覆盖
- `claim_coverage` 看问题真正想问的 claim 有没有被证据覆盖
- `source_diversity` 和 `parent_diversity` 看证据是不是过于单一
- `numeric_evidence` 专门防止数值题只拿到泛泛解释, 却没有硬证据
- `top_claim_score` 看 top 文档是否已经直接回答了核心问题

### 2. LLM Critique

这是第二层判断器.

- 输入是 `question + top docs`
- 输出是 `sufficient / improved_query / reason`

它的作用不是重新检索, 而是从问答视角判断当前上下文是否足够支撑回答.

和 Self-RAG 的区别是.

- Self-RAG 更像规则化和题型感知的证据审查
- LLM critique 更像语义层面的整体 answerability 判断

### 3. 双门判停

这是当前策略里最关键的保守设计.

当 `RISKAGENT_SELF_RAG=true` 时, 系统不是任意一侧说够就停, 而是要求两侧都说够.

```text
retrieval_sufficient = critique_sufficient and self_rag_sufficient
```

这意味着.

- 只有 LLM critique 认为足够, 但 Self-RAG 认为覆盖不够, 不能停
- 只有 Self-RAG 指标看起来够, 但 LLM critique 认为上下文还不足, 也不能停

它本质上是在减少单侧误判 sufficient 带来的过早停止风险.

### 4. Revise Query Loop

如果当前轮判定不足, 系统不会直接失败, 而是进入 `revise_query`.

- critique 会给出 `improved_query`
- 下一轮检索直接用 `improved_query`
- 循环上限由 `max_rounds` 控制
- 当前默认 `max_rounds = 2`

所以这个 adaptive retrieval 的最小闭环是.

`retrieve -> self_rag + critique -> continue or stop -> revise_query -> retrieve`

## 5.3 决策流程与停止条件

当前决策流程可以概括成下面这样.

1. 先做首轮检索
2. 用 Self-RAG 对 docs 打分
3. 用 LLM critique 判断当前证据是否足够
4. 如果两者都认为足够, 提前停止
5. 如果不足且还没到 `max_rounds`, 进入 query revise
6. 如果不足但已经到轮次上限, 停止继续检索并进入后续生成与 gate

其中 Self-RAG 的判断不是一个统一阈值, 而是题型感知的.

### Definition

- 更强调 `query_coverage`
- 更强调 `claim_coverage`
- 还要求 `top_claim_score` 足够高

这样设计是因为定义题最怕 top 文档只相关, 但不直接回答定义本身.

### Compare

- 更强调 `claim_coverage`
- 还要求 `source_diversity >= 2` 或 `parent_diversity >= 2`
- 也要求 `top_isrel` 不能太低

这样设计是因为对比题最怕证据只来自一个 source, 看起来相关但视角不全.

### Procedure

- 看 `query_coverage`
- 看 `claim_coverage`
- 也要求至少有 parent 级上下文

这样设计是因为流程题最怕只拿到局部步骤词, 没有完整上下文.

### Numeric

- 看 `query_coverage`
- 看 `claim_coverage`
- 必须有 `numeric_evidence`

这样设计是因为数值题不能只靠泛化背景知识, 必须看到数字或足够硬的数值型证据.

### Early Stopping 的真正含义

当前 early stopping 不是为了单纯追求更少轮次, 而是在 recall 质量和响应时延之间做保守平衡.

- 如果首轮已经满足足够回答, 不再为了"也许更好"而继续检索
- 如果首轮明显不足, 就允许再跑一轮修正检索
- 不把所有问题都强行跑满 `max_rounds`

这也是为什么图里会强调平均检索轮次下降这件事, 但它应该被理解成策略结果, 不是硬编码目标.

## 5.4 为什么这样设计

这套设计想平衡 3 件事.

- 检索质量
- 响应延迟
- 可解释性

如果每个问题都固定检索 2 轮或 3 轮.

- recall 可能更高一点
- 但 latency 会更差
- 而且很多简单问题是在浪费算力

如果首轮检索后立刻生成.

- 速度更快
- 但首轮 miss 时没有补救手段

如果完全交给一个 LLM 判断要不要继续.

- 语义上可能更灵活
- 但稳定性和可审计性会更差

所以当前方案选择了.

- 用题型感知的 Self-RAG 先做硬一点的 evidence check
- 再用 LLM critique 做语义层面的补充判断
- 两者同时通过才停
- 否则进入 revise loop

这个设计的核心 trade-off 是.

- 宁可少量多跑一轮
- 也尽量避免过早停止导致回答建立在薄证据上

## 5.5 解决了什么问题

当前自适应检索策略主要解决了 5 类问题.

### 1. 首轮检索偶然命中不足

用户问题第一次 rewrite 后未必就是最好检索表达. revise loop 给了二次修正机会.

### 2. 不同题型对证据的要求不一样

定义题, 对比题, 数值题, 流程题需要的证据形态不同. 统一阈值会很粗糙.

### 3. 固定轮次策略太浪费

很多问题首轮就够了, 没必要为了形式统一把所有轮次跑满.

### 4. 单侧判断容易误停

只看 LLM critique 容易过于乐观, 只看规则指标又可能过于死板. 双门判停能降低误判.

### 5. 数值题和高风险题需要更硬的 stopping 条件

数值题如果没有 numeric backing 就提前停, 后续回答很容易出错. 现在这类题型的 stopping 条件更严.

## 5.6 缺点与风险

当前方案虽然稳, 但也有明显缺点.

### 1. 规则仍然偏启发式

Self-RAG 的很多阈值和题型规则本质上还是 hand-crafted, 不是 learned policy.

### 2. 双门判停会更保守

只有一侧觉得不够就继续, 这会减少误停, 但也可能增加额外轮次和延迟.

### 3. Query revise 还比较轻

当前 revise 主要依赖 critique 返回的 `improved_query`, 还没有更强的 query planning 或 decomposition 级修订.

### 4. 题型识别仍是轻量规则

如果 question type 误判, 充分性判断也会跟着偏.

### 5. 没有显式 retrieval budget learner

当前只有 `max_rounds` 这种硬上限, 还没有真正 learned 的成本约束器.

### 6. 停止条件仍然是 retrieval-centered

它主要判断 docs 是否够, 还不是 claim-level 的 end-to-end answerability verifier.

## 5.7 怎么改进

如果后面继续演进, 我觉得可以往下面 5 个方向升级.

### 1. Learned Sufficiency Scorer

把当前规则式 Self-RAG 升级成更像 classifier 或 ranker 的 learned sufficiency scorer.

- 输入 docs 特征, query 特征, route 特征
- 输出 stop / continue 概率
- 用评测数据和回放数据训练

### 2. Claim-Aware Stop Policy

现在虽然已经有 `claim_coverage`, 但整体还是 token overlap 驱动.

更好的做法是.

- 先把问题拆成 claim units
- 再逐项判断 claim 是否被证据支持
- 只有核心 claim 都被覆盖时才停

### 3. 更强的 Query Revision

当前 revise 还比较像单次 query 替换.

更好的做法是.

- 把 revise 和 query intelligence 联动
- 对 compare 问题直接调整 decomposition
- 对 background 问题调整 step back 强度
- 对 numeric 问题强化 numeric tool routing

### 4. Retrieval Budget Controller

把轮次, fanout, rerank_k, advanced index expand 这些预算统一控制起来.

- 简单问题少花钱
- 难问题多给预算
- 让 adaptive retrieval 不只是决定是否继续, 还决定每轮花多少检索预算

### 5. 线上回放驱动阈值校准

当前很多阈值是工程经验值.

更好的做法是.

- 保留每轮 `self_rag` 和 critique 的 debug traces
- 对比最终 qrels 和 gate 结果
- 反向校准不同题型的 stopping threshold

整体上看, 当前自适应检索策略的价值不在于它已经是最优解, 而在于它把 `早停` `继续` `修 query` 这几个原本隐含在 prompt 里的决策, 变成了可以被观察, 解释, 评测和逐步升级的工程部件.

# 6. 质量门禁

## 6.1 门禁边界

这里需要先把两个容易混淆的概念分开.

- 运行时质量门禁, 指的是 `validate_and_save` 节点里的 response validation gates
- 离线评测门禁, 指的是评测报告里的 `threshold gate`

这两层都属于质量控制, 但职责不一样.

- 运行时门禁负责拦截单次回答里的明显高风险错误
- 离线评测门禁负责判断某个版本是否达到发布标准

所以图片里提到的 `Citation Coverage >= 80%` 和 `Faithfulness >= 75%` 更准确地说, 属于评测侧的 release threshold, 不是当前运行时 validator 直接执行的规则.

当前运行时真正落地的门禁主要有 3 个.

- `refusal gate`
- `evidence gate`
- `numeric consistency gate`

另外还有一个可选的 `LLM appeal` 申诉机制, 用来减少 gate 的误杀.

## 6.2 运行时门禁链

当前统一主链的最后一步是 `validate_and_save`.

在这个节点里, 系统会先把检索结果和最终回答转换成一套可校验的中间结构.

1. 从 docs 构造 `evidence_set`
2. 从 answer 构造 `claims`
3. 依次执行各个 gate
4. 如果显式开启, 再执行 `LLM appeal`
5. 记录 `failure_reason` 和最终状态

这里的两个中间结构很关键.

### Evidence Binding

`evidence_set` 是从 docs 确定性构造出来的证据集合, 每条 evidence 至少带这些锚点.

- `evidence_id`
- `source`
- `chunk_id`
- `start_index`
- `snippet`

如果有更多定位信息, 还会附加.

- `section_path`
- `start_line`
- `end_line`
- `page`
- `tool_name`
- `numeric_payload`

这一步本质上就是把"我引用了哪段证据"从松散文本变成结构化对象. 这也是图片里说的 `Evidence Binding`.

### Claim Binding

`claims` 是从 answer 段落里按规则切出来的 claim 列表.

- 优先从正文或相邻 `Citations:` 段里提取 `chunk_id`
- 如果找不到显式引用, 再退化成和 evidence snippet 做 token overlap 匹配
- 每条 claim 都必须携带 `evidence_ids`

这一步的意义是把"回答内容"和"证据锚点"真正绑起来, 让后面的 gate 可以检查 claim 到 evidence 的对应关系.

## 6.3 具体做了哪些门禁

### 1. Refusal Gate

`refusal gate` 解决的是无证据硬答的问题.

触发条件很简单.

- `docs` 为空
- 或 `evidence_set` 为空

这时系统不允许继续给出像正常答案那样的结论性表述, 而是要求回答满足两件事.

- 明确表达拒答或证据不足
- 明确给出 next actions

如果没有拒答, 会落到下面这些失败类型.

- `retrieval_empty`
- `no_evidence`
- `refusal_incomplete`
- `refusal_unclear`

它解决的问题是.

- 检索为空时还在硬答
- 没有证据时仍然编造结论
- 拒答过于含糊, 对用户没有操作性建议

优点.

- 规则明确
- 风险收益比很高
- 对金融风控这种高代价幻觉场景非常必要

缺点.

- 只看 docs 和 evidence 是否存在, 不看证据质量高低
- 关键词法判断拒答语气, 对表达风格比较敏感

### 2. Evidence Gate

`evidence gate` 是运行时最核心的一层.

它主要检查 4 件事.

1. 每条 claim 必须有 `evidence_ids`
2. 每个 `evidence_id` 必须能在 `evidence_set` 找到
3. 每条 evidence 必须有完整 anchor
4. claim 的内容必须和链接 evidence 形成最基本的支持关系

这里的支持关系不是只检查存在引用, 还会看两个更具体的条件.

- `best_token_overlap >= 3`
- `best_coverage_ratio >= 0.25`

同时如果 claim 里出现数字, 还会检查链接 evidence 里的数字是否支持它.

对应的失败类型包括.

- `evidence_incomplete`
- `evidence_missing`
- `evidence_not_found`
- `evidence_not_supporting`
- `evidence_numeric_mismatch`

它解决的问题是.

- 回答里有 claim 但没有证据
- 引用了一个不存在的 evidence id
- evidence 只有 source 没有定位锚点
- 引用了证据, 但证据其实不支持 claim
- claim 里的数字和证据数字不一致

优点.

- 把"有引用"和"被引用内容真的支持 claim"区分开了
- Evidence Binding 和 claim binding 一起工作, 可以直接反查失败原因
- 对审计和 debug 很友好

缺点.

- 当前支持性判断仍然高度依赖 token overlap
- 对同义改写, 跨句支持, 长距离蕴含的识别能力有限
- `0.25` 这类阈值仍然是启发式经验值

### 3. Numeric Consistency Gate

`numeric consistency gate` 重点处理数值型高风险回答.

它不是一刀切检查所有数字, 而是先区分两种场景.

#### 纯检索链路

- 没有 `tool_traces`
- 把数字视为来自检索证据的陈述
- 只要有 `evidence_set`, gate 本身就先放行
- 更细的准确性由后续 faithfulness 评测继续兜底

#### 有工具链路

- 存在 `tool_traces`
- 先识别回答里的数字哪些是 `calculated`, 哪些是 `stated`
- 对 `calculated` 数字, 必须能在工具输出里找到一致数值
- 允许 `1e-6` 的绝对误差和 `1%` 的相对误差

对应的失败类型主要是.

- `numeric_stated_without_evidence`
- `numeric_calculated_mismatch`

它解决的问题是.

- 工具算出来的数值和最终回答不一致
- 没有任何证据却直接给出数字
- 金融场景里轻微数值漂移直接变成审计风险

优点.

- 把检索型数字和计算型数字分开处理, 比一刀切更合理
- 对真实工具输出做比对, 风险拦截很硬
- 支持相对误差容忍, 避免格式和四舍五入导致的误杀

缺点.

- 计算型和陈述型数字的分类仍然靠上下文关键词
- 纯检索链路下 gate 自身并不验证数字真实性, 需要 faithfulness 继续兜底
- 对单位换算, 区间值, 表格聚合等复杂数值表达还不够强

### 4. LLM Appeal

这不是主 gate, 而是 gate 后面的误杀修正层.

- 默认关闭
- 只有显式设置 `RISKAGENT_ENABLE_LLM_APPEAL=true` 才会启用
- 只在 gate 已经失败时才运行

它会让 LLM 判断当前失败是不是 false positive, 然后返回.

- `is_false_positive`
- `reason`
- `suggested_fix`

如果 appeal 判断这是误杀, 运行时会把这次 gate 失败改写成通过.

它解决的问题是.

- 规则 gate 太硬时的误杀
- 某些边界 case 用规则说不清楚

优点.

- 给确定性 gate 增加了一层柔性兜底
- 便于分析 false positive

缺点.

- 引入新的不确定性
- 正式评测默认关闭是对的, 不然 reproducibility 会变差

### 5. 离线 Threshold Gate

虽然它不属于运行时 validator, 但质量门禁章节里必须顺手说明.

当前评测侧会把聚合指标和阈值对比, 形成版本级门禁. 其中典型阈值包括.

- `citation_coverage >= 0.8`
- `faithfulness >= 0.75`
- 以及其他 retrieval 和 domain consistency 相关阈值

这层门禁解决的是.

- 单次回答看起来没问题, 但版本整体质量退化
- 运行时规则都过了, 但整体忠实度和召回率仍然不达标

所以可以把两层门禁理解成.

- 运行时 gate 防单条高风险回答
- 离线 threshold gate 防版本级回归

## 6.4 为什么这样设计

这套门禁设计的核心思路是分层防守.

### 第一层, 先拦明显硬错误

- 检索空了还继续答
- 没证据还继续答
- claim 和 evidence 根本绑不上
- 工具数值和回答不一致

这类问题用确定性规则拦最稳, 也最容易审计.

### 第二层, 把证据关系结构化

系统不是只看答案文本像不像对, 而是强制构造.

- `evidence_set`
- `claims`
- `failure_reason`

这样每次失败都能定位到是 retrieval 空, evidence 缺, 还是 numeric mismatch. 对金融审计和工程调试都很关键.

### 第三层, 运行时和离线分开

如果把 `faithfulness` `citation_coverage` 这类评测指标全都塞进运行时, 成本会太高, 延迟也会变差.

所以当前策略是.

- 运行时只保留便宜且强约束的 hard gates
- 离线评测再做更完整的质量阈值审查

这个分层在工程上更现实.

## 6.5 优缺点

### 优点

- 规则明确, 失败可解释
- 运行成本低, 适合在线主链
- 对无证据生成和数值漂移这种高风险问题拦截有效
- 和 artifact 落盘结合后, 很适合做 failure taxonomy 分析

### 缺点

- 证据支持判断偏 lexical, 语义支持能力还不够强
- 数值上下文分类还是启发式
- gate 是 fail fast, 只能返回第一个失败原因, 对多错误并发场景信息不够全
- 运行时 gate 和离线 threshold gate 口径分层是合理的, 但也会让人第一次读代码时误以为不一致

### 适用 trade-off

- 这套方案更偏保守和可审计
- 它不是最聪明的, 但非常适合金融风控这种宁可多拦一点也不能乱放的场景

## 6.6 怎么改进

如果后面继续演进, 我觉得有 6 个方向最值得做.

### 1. 语义级 Evidence Verifier

把现在基于 token overlap 的 support check 升级成 claim-evidence entailment 或 cross-encoder verifier.

这样能更好处理.

- 同义改写
- 跨句支持
- 长距离蕴含

### 2. Multi-Failure Reporting

现在 `validate_response` 是 fail fast, 只返回第一个失败原因.

更好的做法是.

- 同时收集所有 gate failures
- 输出主失败原因和次失败原因
- 这样 debug 和标注分析会更完整

### 3. 更强的 Numeric Grounding

把 numeric gate 从简单数字匹配升级成带单位和公式语义的检查.

比如增加.

- unit normalization
- percentage vs absolute delta normalization
- table cell provenance
- formula trace binding

### 4. Better Refusal Policy

现在 refusal 还比较依赖关键词.

更好的做法是.

- 用结构化 answer schema 显式区分 `answer` `refusal_reason` `next_actions`
- 不再依赖自由文本里有没有出现某几个关键词

### 5. Learned Appeal Or Human Review Queue

现在 appeal 只有一个可选 LLM 裁决器.

更好的做法是.

- 对高风险失败接入人工复核队列
- 或者训练一个专门的 false positive triager

### 6. 统一 Online Gate 和 Offline Eval 的谱系

当前两层门禁已经分工清楚, 但还可以继续打通.

更好的做法是.

- 把运行时 `failure_reason` taxonomy 和离线 `gate_metrics` 完全对齐
- 让每种在线失败都能在离线报告里直接聚合统计
- 让 threshold gate 不只是看 aggregate 指标, 也看高风险 failure slice

整体上看, 当前质量门禁的价值不只是"把回答拦下来". 更重要的是它把证据绑定, 数值校验, 拒答策略和版本级阈值审查拆成了可独立演进的质量控制部件.

# 7. 评估体系

## 7.1 为什么单独设计评估体系

这个项目的评估体系不是为了产出一个总分, 而是为了回答 3 个更关键的问题.

- 检索有没有把 gold evidence 找回来
- 回答是不是建立在证据之上
- 质量门禁到底是在拦真实风险, 还是在误杀

这也是为什么当前评测口径被明确拆成 `retrieval metrics` `answer metrics` `gate metrics` 三层.

如果不拆层, 会有两个很严重的问题.

- 归因不清. 一个 badcase 到底是 recall 不够, 还是 answer hallucination, 还是 gate 策略有问题, 很难看出来
- 容易自举偏差. 如果只看最终答案质量, retrieval 的问题会被 generation 掩盖, 反过来也一样

所以当前体系本质上是在做一套面向工程优化的评测闭环.

- 用 `qrels` 固定 retrieval truth
- 用 `citation` `sentence support` `RAGAS` 检查回答质量
- 用 `gate_labels` 检查门禁策略收益
- 用 `threshold gate` 和 `baseline regression` 管发布

当前项目里, 这套体系已经真实落在 `50` 题金融评测集上, 并且可以输出 fresh report 做版本对比.

## 7.2 参考了业界哪些成果

这套评估体系不是单一论文口径, 而是把几类成熟思路拼到一起.

### 1. 经典 Information Retrieval 评测

retrieval 部分明显借鉴了传统 search evaluation 的思路.

- `qrels`
- `Recall@K`
- `MRR`
- `nDCG@K`

这类指标来自 TREC 和后来的检索评测传统, 也是很多现代检索基准比如 BEIR 常用的口径. 它们的优点是.

- 不依赖生成模型
- 可以把 retrieval 单独拎出来优化
- 对召回和排序问题归因更直接

### 2. RAGAS

answer 侧明显参考了 RAGAS 的思路, 当前代码里已经集成了完整的 RAGAS 指标入口, 并优先使用.

- `faithfulness`
- `answer_relevancy`
- `context_precision_no_ref`
- `contradiction_score`
- 以及其他可选指标

这部分的价值在于, 它把 RAG 问题从传统 QA 评估往 `question + answer + contexts` 的 grounded 评估方向推进.

### 3. Grounded Generation 和 Citation Diagnostics

除了直接吃 RAGAS, 当前项目还保留了更可复核的 grounded diagnostics.

- `citation_coverage`
- `citation_precision`
- `sentence_support_rate`
- `unsupported_sentence_rate`

这部分不是完全照搬某一个公开框架, 更像是结合 grounded QA 和引用可验证性的工程化实现.

### 4. 风险控制式 Release Gate

最后一层 `threshold gate + baseline regression` 更像成熟工程系统和 ML 平台常见的发布治理方法.

- threshold 看有没有达到最低上线标准
- baseline regression 看有没有比上一版退化

它不是论文指标, 但在生产系统里非常重要.

## 7.3 三层评估结构

当前评估结构可以概括成下面这样.

### 第一层, Retrieval Metrics

目标是回答一个问题.

- gold evidence 有没有被召回

它只依赖 `qrels` 和 `retrieved_docs`, 不依赖最终答案写得怎么样.

### 第二层, Answer Metrics

目标是回答两个问题.

- 答案有没有引用
- 答案是不是忠于上下文, 而且真的在回答问题

它依赖 `answer` `citations` `contexts` 和可选的 `reference_answer`.

### 第三层, Gate Metrics

目标是回答.

- 质量门禁有没有拦住该拦的样本
- 有没有误杀不该拦的样本

它依赖 `gate_labels` 和运行时真实 `status / failure_reason`.

这 3 层一起工作以后, 才能形成比较完整的闭环.

- retrieval 差, 就优先改召回和排序
- answer 差, 就优先改上下文使用和生成
- gate 差, 就优先改门禁策略而不是乱改主链

## 7.4 具体指标与计算方式

下面只写当前项目里已经真实落地, 并且在代码中有明确实现的指标.

### A. Retrieval Metrics

#### 1. `retrieval_recall_at_k`

含义.

- 在 top `k` 检索结果里, 命中了多少个 gold qrels

计算方式.

```text
recall@k = topk 命中的 qrel 数 / 该题全部 qrel 数
```

当前实现不是只做文本模糊匹配, 而是优先使用结构化定位字段.

- 优先 `chunk_id` 硬匹配
- 其次在 `source / section_path / parent_id` 一致前提下允许文本覆盖匹配
- 只有明确的 text-only qrel 才退回纯文本匹配

优点.

- 最能直接反映召回是否够用

缺点.

- 非常依赖 qrels 质量
- chunk 重切和 locator 漂移会影响结果

#### 2. `retrieval_mrr`

含义.

- 第一个 relevant 文档出现得有多靠前

计算方式.

```text
MRR = 1 / first_relevant_rank
```

如果首个 relevant 文档没出现, 就记 `0`.

优点.

- 对 top1 到 top few 的排序质量很敏感

缺点.

- 只看第一个 relevant, 对多 relevant 的覆盖不充分

#### 3. `retrieval_ndcg_at_k`

含义.

- 既看 relevant 命中, 也看高相关证据是否被排在更前面

计算方式.

```text
DCG@k = Σ((2^relevance - 1) / log2(rank + 1))
nDCG@k = DCG@k / IDCG@k
```

当前实现会读取 qrel 里的 `relevance` 字段, 没给时默认按 `1` 处理.

优点.

- 比 recall 更能体现排序质量

缺点.

- 依赖 graded relevance 标注
- 标注质量一般时解释成本会更高

#### 4. `retrieval_dense_hit_rate` `retrieval_sparse_hit_rate` `retrieval_hybrid_gain_rate`

含义.

- 当前样本是否真的走到了 dense
- 是否真的走到了 sparse
- hybrid 是否形成了双路都参与的命中

这 3 个指标更偏诊断指标, 不是标准论文指标, 但对混合检索调参很有帮助.

#### 5. `retrieval_rerank_uplift`

含义.

- reranker 是否把 relevant 文档往前拉了

当前实现近似比较 relevant 文档在 `rrf_score` 和 `rerank_score` 下的最佳位置差.

```text
retrieval_rerank_uplift = rrf_best_rank - rerank_best_rank
```

值越大, 通常说明 rerank 越有帮助.

### B. Citation 和 Answer Metrics

#### 6. `citation_coverage`

含义.

- 有多少比例的样本至少给出了一个有效引用

计算方式.

```text
citation_coverage = 至少有 1 个有效 citation 的样本数 / 样本总数
```

当前 `valid citation` 的判定很保守.

- `source` 不能为空
- `chunk_id` 不能为空
- `source` 路径里必须落在 `corpus/` 下

优点.

- 非常便宜
- 对"是否真的给了引用"有强约束

缺点.

- 只看有没有引用, 不看引用对不对

#### 7. `citation_precision`

含义.

- 答案里的句子有多大比例被上下文支持

当前支持 3 种模式.

- `heuristic`
- `llm`
- `auto`

在 `heuristic` 模式下, 句子会先切分, 然后逐句检查是否被任一 context 支持. 当前近似规则是.

- 句子原文直接出现在 context 中, 通过
- 或者 token overlap 至少达到阈值, 通过

聚合后会得到.

```text
sentence_support_rate = supported_sentences / total_sentences
unsupported_sentence_rate = 1 - sentence_support_rate
```

优点.

- 能直接暴露 unsupported sentences
- 比只看最终一个分数更可调试

缺点.

- heuristic 版本对同义改写和长距离蕴含不够敏感
- llm 版本更强, 但成本更高且可复现性更差

#### 8. `faithfulness`

含义.

- 答案是否忠于提供的上下文

当前实现是分层退化的.

- 如果启用 RAGAS, 优先取 `ragas_faithfulness`
- 否则退回 `sentence_support_rate`

这点很重要. 当前仓库里 `faithfulness` 不是单一口径, 而是.

```text
faithfulness = ragas_faithfulness, 如果可用
faithfulness = sentence_support_rate, 如果 RAGAS 不可用
```

优点.

- 有 RAGAS 时语义更强
- 没有 RAGAS 时还能保留离线可复现 fallback

缺点.

- 双口径会带来解释复杂度
- 不同运行环境下结果可比性会变弱

#### 9. `answer_relevancy`

含义.

- 答案是否真的在回答问题

当前实现同样是分层退化的.

- 优先取 `ragas_answer_relevancy`
- 否则退回本地 heuristic overlap

fallback 近似公式是.

```text
question_overlap = overlap(question_tokens, answer_tokens)
reference_overlap = overlap(reference_answer_tokens, answer_tokens)
answer_relevancy = question_overlap
answer_relevancy = max(question_overlap, 0.6 * question_overlap + 0.4 * reference_overlap), 如果 reference_answer 存在
```

优点.

- 在没有在线 judge 的情况下还能稳定跑

缺点.

- heuristic overlap 容易高估表面相关, 低估语义等价

#### 10. `context_precision_no_ref`

含义.

- 在不依赖 reference answer 的前提下, 检索上下文里有多少是真正相关的

当前项目不是直接调用 RAGAS 原生指标, 而是在 `ragas_metrics.py` 里做了自定义 `compute_context_precision_no_ref`, 再把结果写成 `ragas_context_precision_no_ref` 并映射为标准报告指标.

优点.

- 很适合检查 context 里噪声是否过高

缺点.

- 依赖 LLM judge
- 成本较高

#### 11. `contradiction_score`

含义.

- 检索上下文或回答中是否出现相互矛盾的证据迹象

当前项目不是直接调用 RAGAS 原生指标, 而是在 `ragas_metrics.py` 里做了自定义 `compute_contradiction_detection`, 再把结果写成 `ragas_contradiction_score` 并在报告里作为 lower-is-better 指标处理.

优点.

- 能发现不是纯 hallucination, 而是 evidence conflict 的问题

缺点.

- 对 judge 质量很敏感

### C. Domain Metrics

#### 12. `numeric_consistency_score`

含义.

- 答案中的数字, 有多少比例能在 contexts 里找到支持

计算方式.

```text
numeric_consistency_score = matched_numbers / total_numbers_in_answer
```

当前实现会先从 answer 和 contexts 抽数字, 然后按下面两种条件匹配.

- 绝对误差 `<= tolerance`
- 或相对误差 `<= tolerance`

在 `evaluation.run` 的正式评测默认口径里, `tolerance` 默认是 `0.01`.

如果单独调用 `domain_consistency.py` 里的函数签名, 还能看到更宽松的局部默认值, 但评测主流程实际使用的是 `0.01`.

优点.

- 对金融数值题很有针对性

缺点.

- 还不理解单位, 表格位置, 公式链
- 把单一容忍度统一用于所有数值题仍然偏粗

#### 13. `glossary_consistency_score`

含义.

- 领域术语有没有出现明显错误或不合适的日常化解释

当前实现是 MVP 版本, 用一个禁用词表检查少量核心术语.

```text
glossary_consistency_score = (checked_terms - violations) / checked_terms
```

比如.

- `delta` 不应该被说成普通的 `difference`
- `gamma` 不应该被说成 `ray`

优点.

- 很便宜
- 对金融术语误译能起到第一层提醒

缺点.

- 词表很小
- 更像规则报警, 不是完整术语评估

#### 14. `domain_consistency_score`

含义.

- 把数值一致性和术语一致性合成一个领域稳定性指标

当前公式非常直接.

```text
domain_consistency_score = (numeric_consistency_score + glossary_consistency_score) / 2
```

优点.

- 便于做版本级总览

缺点.

- 两个分量同权只是工程假设
- 不同业务场景下未必合理

### D. Gate Metrics

#### 15. `gate_block_rate`

含义.

- 门禁拦下了多少比例的样本

```text
gate_block_rate = blocked_samples / total_samples
```

#### 16. `gate_block_benefit_rate`

含义.

- 在带 `gate_labels` 的样本里, 门禁拦住了多少本来就该拦的样本

```text
gate_block_benefit_rate = true_positive / labeled_total
```

#### 17. `gate_false_kill_rate`

含义.

- 在带标注样本里, 门禁误杀了多少本来不该拦的样本

```text
gate_false_kill_rate = false_positive / labeled_total
```

#### 18. `gate_miss_rate`

含义.

- 在带标注样本里, 本来该拦却没拦下来的比例

```text
gate_miss_rate = false_negative / labeled_total
```

这组指标的价值在于, 它把 gate 从"看起来合理"变成了"可量化收益和副作用".

## 7.5 Threshold Gate 与 Baseline Regression

这套体系最后还有两道版本级控制.

### 1. Threshold Gate

它检查当前报告的聚合指标是否达到最低阈值.

这一步不是每次评测默认都会执行, 而是只有显式传入 `--enforce-thresholds` 时才会真的作为发布门禁启用.

当前 answer eval 默认阈值包括.

- `citation_coverage >= 0.8`
- `faithfulness >= 0.75`
- `answer_relevancy >= 0.7`

除此之外, `config/eval_thresholds.json` 里还可以配置 retrieval 和其他指标的.

- `minimum`
- `maximum`
- `tolerance`
- `direction`

判定逻辑是.

- higher is better 的指标, 低于 `minimum - tolerance` 就失败
- lower is better 的指标, 高于 `maximum + tolerance` 就失败

### 2. Baseline Regression

它不是看绝对值, 而是看相对上一版有没有退化.

这层逻辑会根据指标方向自动判断.

- `retrieval_recall_at_k` `retrieval_ndcg_at_k` `faithfulness` 这类通常是 higher-is-better
- `contradiction_score` `false_kill_rate` `latency` 这类通常是 lower-is-better

这两层必须分开看.

- threshold failure 说明系统还没达到最低可发布标准
- baseline regression 说明系统可能退化了, 即使它仍然在阈值之上

## 7.6 这个体系的缺点

当前体系已经比只看一个总分强很多, 但还有明显短板.

### 1. qrels 仍然可能受到 chunk drift 影响

- 文档重切块后, `chunk_id` 容易漂移
- 当前虽然已经优先走结构化 locator 匹配, 但仍有边界误差

### 2. answer 指标存在双口径

- `faithfulness` 和 `answer_relevancy` 会优先吃 RAGAS
- 没有 RAGAS 时又会退化到 heuristic
- 这会影响不同环境下结果的严格可比性

### 3. citation precision 的 heuristic 还不够语义化

- 它更像 grounded overlap check
- 对同义改写, 隐式蕴含, 跨句支持仍然偏弱

### 4. gate_labels 样本还偏少

- `gate_block_benefit_rate`
- `gate_false_kill_rate`
- `gate_miss_rate`

这几个指标目前已经有价值, 但统计显著性还不够强

### 5. domain consistency 还是 MVP

- glossary 侧目前主要靠小词表
- numeric 侧也还不理解单位换算和公式链
- 这个分数有用, 但还不是最终形态

### 6. 还缺更强的成本视角

当前虽然已有 `reliability_cost_metrics`, 但主叙事还是质量导向. 后面还应该更系统地纳入.

- latency
- rerank pairs
- fanout
- token cost

### 7. release acceptance 仍然不是最硬的 fresh full eval

它已经能检查报告结构和门禁闭环, 但在没有外部 LLM key 时, 仍可能退回样例报告路径. 这意味着发布验收的严格度还有提升空间.

整体上看, 这套评估体系最大的价值不是"指标很多", 而是它把 retrieval, answer, gate, release decision 这几层拆开了. 这样每次指标波动时, 我们能更快知道应该改哪里, 也更能诚实地说明系统到底强在哪, 弱在哪.

## 7.7 系统 Evaluation 流程
```text
[tests/data/questions.json]
    | 问题 + tags
    v
[dataset loader]
    | 自动加载相邻 qrels.json 与 gate_labels.json
    | qrels = gold retrieval truth
    | text only qrel 只允许来自显式 gap allowlist
    | gate_labels = gate 标注样本
    v
[evaluation.run]
    | 始终复用统一主链
    | retrieval_pipeline = hybrid_query_intel_advanced_index
    | 若外部未设置 EMBEDDINGS_PROVIDER 则默认补成 hf
    | 若未显式设置 reranker_model 则补默认 cross-encoder
    | 若配置 reranker candidates 则按候选顺序离线尝试并记录实际命中的模型
    | stage 仅作为阶段性说明与报告标签
    v
[评测前准备]
    | 先执行 incremental_index
    | 然后 build_retriever
    | 这一步会真实依赖 embedding 模型
    | manifest 已存在也仍会先做增量索引检查
    v
[执行评测]
    | 对每个样本跑 LangGraph 主链
    | 输出 answer citations claims evidence_set decision_log
    | 保留 retrieved_docs contexts status failure_reason latency
    v
[指标计算]
    |
    +-> retrieval_metrics
    |    | 基于 qrels 计算 recall@k / MRR / nDCG@k
    |    | 输出 slice_metrics
    |
    +-> citation_precision
    |    | 支持 auto / llm / heuristic
    |    | 输出 supported_sentences / unsupported_sentences
    |
    +-> answer_eval
    |    | citation_coverage
    |    | faithfulness / answer_relevancy 优先吃 RAGAS 结果
    |    | 未启用 RAGAS 时走本地 answer_eval 口径
    |
    +-> domain_consistency
    |    | numeric_consistency_score
    |    | glossary_consistency_score
    |    | 失败明细 numeric_failures / glossary_violations
    |
    +-> gate_metrics
         | 基于 gate_labels 计算
         | gate benefit / false kill / miss rate
    v
[baseline compare]
    | comparisons + summary
    | 先和 baseline 做回归对比
    | threshold failure 与 baseline regression 分离展示
    v
[threshold gate]
    | 只有 enforce_thresholds 时才执行
    | appeal 不参与正式评测默认路径
    | 失败时返回 exit code 2
    v
[reporting]
    | 写 JSON report
    | 写 Markdown report
    | 写 dataset_version prompt_version retrieval_pipeline reranker_model git_commit
    | inputs 里同时记录 milvus_uri host port profile retrieval_ks
```

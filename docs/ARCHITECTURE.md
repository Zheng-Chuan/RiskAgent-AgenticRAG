# 系统 Query 流程
```text
[用户]
    | 发起 query
    v
[API / CLI 入口]
    | /v1/ask 或 /v1/chat
    | 生成 request_id
    | 校验输入 schema
    | chat 场景把多轮 history 收敛成最近几轮上下文
    v
[RiskAgentSystem.chat]
    | 检查索引 manifest 是否存在
    | 根据 persist_dir 初始化或复用 retriever
    | 主路径固定为纯 RAG
    | 不再进入 decide_tool_use / call_tool
    v
[LangGraph 工作流]
    |
    +-> [Step 1] rewrite
    |       | 用 LLM 把原始问题改写成更适合检索的 current_query
    |       | 记录 decision_log 与 trace
    |       v
    +-> [Step 2] retrieve_and_critique
    |       |
    |       +-> [2.1] 统一检索主链
    |       |       | HybridRetriever
    |       |       | -> QueryIntelligentRetriever
    |       |       | -> AdvancedIndexRetriever
    |       |       | 运行时不再切 mode
    |       |       v
    |       +-> [2.2] query intelligence 默认发生
    |       |       | a. keywordize: 压缩 query 保留高信息量 token
    |       |       | b. acronym expansion: 展开缩写
    |       |       | c. route 识别: compare / background / procedure / default
    |       |       | d. step back: 背景类和流程类问题补通用表述
    |       |       | e. decomposition: compare 类问题拆子问题
    |       |       | f. variant 去重后分别调用 hybrid retrieval
    |       |       | g. variant 结果再做一层 RRF 融合
    |       |       v
    |       +-> [2.3] hybrid retrieval 主体
    |       |       | dense 向量召回
    |       |       | sparse BM25 召回
    |       |       | 两路候选合并后做 coarse ranking
    |       |       | 再用 cross-encoder rerank
    |       |       | 最后做 diversity select 控同 source / section 重复
    |       |       v
    |       +-> [2.4] advanced index 默认发生
    |       |       | a. summary index 补主题级信号
    |       |       | b. HyDE index 补 query-doc 表达差异
    |       |       | c. parent expand 用 parent_id 找回更长上下文
    |       |       | d. base_score + summary_score + hyde_score 融合
    |       |       | e. 对 desk exposure / delta limit 问题
    |       |       |    追加轻量级风险工具输出作为结构化证据
    |       |       v
    |       +-> [2.5] critique
    |               | LLM 判断当前 docs 是否足够回答问题
    |               | Self-RAG doc grade 也会参与 stop / continue 判断
    |               | 产出 sufficient / critique_reason / improved_query
    |               | insufficient 时进入 revise_query 循环
    |       v
    +-> [Step 3] revise_query
    |       | 若检索结果不足则修正 query
    |       | 回到 Step 2
    |       | 受 max_rounds 限制 防止死循环
    |       v
    +-> [Step 4] synthesize_answer
    |       | 严格基于检索上下文生成答案
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
    |       |       | appeal 默认关闭
    |       |       | 只有显式设置 RISKAGENT_ENABLE_LLM_APPEAL=true 才会启用
    |       |       v
    |       +-> [5.2] 结构化结果
    |       |       | answer + citations + claims + evidence_set
    |       |       | decision_log + debug + failure_reason
    |       |       v
    |       +-> [5.3] 落盘 artifacts
    |               | 单文件 artifact
    |               | bundle 目录下 request response structured_response trace
    |               v
[API 返回]
    v
[用户]
```

# 系统 Index 流程
```text
[corpus]
    | md / pdf 等原始文档
    v
[source_loader]
    | 解析文档并保留 source page line metadata
    v
[ingestion]
    | build_parent_documents
    | split_documents
    | 形成 parent 和 chunk 两层语料
    v
[embeddings]
    | 正常运行默认 hf embeddings
    | 离线回归可切到 hash embeddings
    v
[incremental_index]
    |
    +-> 计算源文件 sha1
    |    与 manifest 比较 决定 indexed / skipped
    |
    +-> 写 Milvus Lite dense index
    |    collection 维度由 embeddings 实测决定
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
         记录 provider model dim 和每个 source 的索引摘要
```

# 系统 Evaluation 流程
```text
[tests/data/questions.json]
    | 问题 + tags
    v
[dataset loader]
    | 自动加载相邻 qrels.json 与 gate_labels.json
    | qrels = gold retrieval truth
    | gate_labels = gate 标注样本
    v
[evaluation.run]
    | 始终复用统一主链
    | retrieval_pipeline = hybrid_query_intel_advanced_index
    | stage 仅作为阶段性说明与报告标签
    v
[执行评测]
    | 对每个样本跑 LangGraph 主链
    | 输出 answer citations claims evidence_set decision_log
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
    |    | faithfulness
    |    | answer_relevancy
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
[threshold gate]
    | threshold failure 与 baseline regression 分离展示
    | appeal 不参与正式评测默认路径
    v
[reporting]
    | 写 JSON report
    | 写 Markdown report
    | 写 dataset_version prompt_version retrieval_pipeline reranker_model git_commit
    v
[baseline compare]
    | comparisons + summary
    | 可做离线回归与发布验收
```

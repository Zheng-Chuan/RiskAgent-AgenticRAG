# 系统 Query 流程
```text
[用户]
    | 发起 query
    v
[API/CLI 入口]
    | /v1/ask 或 /v1/chat
    | 生成 request_id, 组装 history, 校验输入 schema
    v
[RiskAgentSystem.chat]
    | 检查索引是否存在, 根据模式初始化 retriever
    | retriever_mode = step1 / step2 / step3 / step4
    | 主路径固定为纯 RAG, 不再进入 tool decision / call_tool 分支
    v
[LangGraph 工作流]
    |
    +-> [Step 1] rewrite_query
    |       | 用 LLM 把原始 query 改写成更适合检索的 current_query
    |       | 记录 decision_log 与 trace
    |       v
    +-> [Step 2] retrieve_and_critique
    |       |
    |       +-> [2.1] 查询构建
    |       |       | step1 = HybridRetriever
    |       |       |   dense + sparse + RRF + rerank + diversity
    |       |       | step2 = QueryIntelligentRetriever
    |       |       |   在 step1 外包一层 query intelligence
    |       |       | step3 = AdvancedIndexRetriever
    |       |       |   在 step1 外包一层 advanced index
    |       |       | step4 = step3 retriever + 编排层 Self-RAG 自检
    |       |       | 注: 当前代码里 step2 与 step3/step4 是两条不同增强线
    |       |       v
    |       +-> [2.1.1] step2 query intelligence 仅在 step2 发生
    |       |       | base query 先进入 generate_query_variants
    |       |       | a. keywordize: 去停用词, 保留高信息量 token
    |       |       | b. acronym expansion: 如 FRTB -> fundamental review...
    |       |       | c. route 识别: compare / background / procedure / default
    |       |       | d. step back: route 属于 background / procedure / compare 时触发
    |       |       | e. decomposition: route = compare 时触发, 拆成子问题
    |       |       | f. 去重并限制 max_variants
    |       |       | g. 每个 variant 都调用一次 step1 hybrid retrieval
    |       |       | h. 用 variant-level RRF 再融合结果
    |       |       v
    |       +-> [2.2] 多路召回
    |       |       | dense (embedding) 向量召回
    |       |       | sparse (BM25) 全文召回
    |       |       | 先并行取回 topK 候选, 再做 merge
    |       |       | 对每个 doc 写入 dense_rank / sparse_rank / retrieval_sources
    |       |       v
    |       +-> [2.3] 粗排与过滤
    |       |       | 过滤过短 chunk, 目录页和低信息量文本
    |       |       | 用 RRF 分数 + BM25 分数 + metadata_boost 得到 coarse_score
    |       |       | 取 candidate_k 进入粗排池
    |       |       v
    |       +-> [2.4] 精排（Fine Ranking）
    |       |       | Cross-Encoder 对 (query, chunk) 对打 rerank_score
    |       |       | 如果没有 reranker, 则退化到 coarse_score 排序
    |       |       | 然后做 diversity select, 限制同 source / section 过度重复
    |       |       v
    |       +-> [2.5] advanced index 补强 仅在 step3 / step4 发生
    |       |       | a. summary index: 用 parent 级摘要补宏观主题信号
    |       |       | b. HyDE index: 用假设性问题或假设性文档补 query-doc 表达差异
    |       |       | c. parent expand: 用 parent_id 找回大段上下文写入 expanded_text
    |       |       | d. 用 base_score + summary_weight * summary_score
    |       |       |                  + hyde_weight * hyde_score
    |       |       |    得到 advanced_index_score
    |       |       v
    |       +-> [2.6] Self-RAG 评估
    |       |       | 这一步主要在编排层发生, 是 step4 的关键补强
    |       |       | 对每个 chunk 判断:
    |       |       |   - 是否相关 (IS_RELEVANT / isrel)
    |       |       |   - 是否支持答案 (IS_SUPPORTED / issup)
    |       |       |   - 是否有帮助 (IS_USEFUL / isuse)
    |       |       | 聚合出 sufficient, top_isrel, avg_isrel
    |       |       v
    |       +-> [2.7] 批判评估
    |               | LLM 判断当前检索结果是否足够回答 query
    |               | 输出 critique_reason, improved_query
    |               | 并决定 should_continue 是否继续 revise query
    |       v
    +-> [Step 3] 条件判断: revise_query?
    |       | 依据 Step 2.7 的 critique 和 Self-RAG sufficient
    |       | YES -> revise_query -> 回到 Step 2, 最多循环 max_rounds
    |       | NO  -> 继续 Step 4
    |       v
    +-> [Step 4] synthesize_answer
    |       | 基于 Step 2 筛选后的 docs 生成答案
    |       | 这是纯 RAG 生成阶段, 只允许使用检索上下文
    |       | 从 docs 中抽取 citations, 再把 citations 挂到答案段落
    |       | 后续 validate_and_save 会基于 answer 构建 claims
    |       v
    +-> [Step 5] validate_and_save
            |
            +-> [5.1] Gate 校验
            |       | refusal gate: 检测是否需要拒答
            |       | evidence gate: 验证答案有足够证据
            |       | numeric gate: 检查数值类答案的准确性
            |       | 当前实现里失败后还可能进入 LLM appeal
            |       v
            +-> [5.2] 结构化输出
            |       | 按照 API schema 组装纯 RAG 输出
            |       | answer + citations + claims + evidence_set + decision_log + debug
            |       v
            +-> [5.3] 落盘 artifacts
                    | 写入 request / response / structured payload / trace
                    v
[API 返回]
    v
[用户]
```

# 系统 Index 流程


# 系统 Evaluation 流程

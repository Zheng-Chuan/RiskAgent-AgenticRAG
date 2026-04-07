# 系统核心流程
```text
[用户]
    | 发起 query
    v
[API/CLI 入口]
    | /v1/ask 或 /v1/chat
    v
[RiskAgentSystem.chat]
    | 组装 history (最近3轮) + query
    v
[LangGraph 工作流]
    |
    +-> [Step 1] rewrite_query
    |       | 用 LLM 把原始 query 改写成更适合检索的版本
    |       v
    +-> [Step 2] retrieve_and_critique
    |       |
    |       +-> [2.1] 查询构建
    |       |       | 根据模式选择检索策略 (step1/step2/step3/step4)
    |       |       | 如果是 step3/step4 会触发假设性文档 (HYDE)
    |       |       |   即先用 LLM 生成假设性回答, 用它来检索
    |       |       v
    |       +-> [2.2] 多路召回
    |       |       | dense (embedding) 向量召回
    |       |       | sparse (BM25) 全文召回
    |       |       | 可选 summary 摘要索引召回
    |       |       | 三路并行返回大量候选 chunk
    |       |       v
    |       +-> [2.3] 父子文档召回
    |       |       | 先召回细粒度 chunk, 再通过 chunk_id 找到对应的父 doc
    |       |       | 返回 (chunk, parent_doc) 对
    |       |       v
    |       +-> [2.4] 粗排（Coarse Ranking）
    |       |       | 用 RRF (Reciprocal Rank Fusion) 融合三路召回的排名分数
    |       |       | 按总分排序取前 50 个候选进入精排池
    |       |       v
    |       +-> [2.5] 精排（Fine Ranking）
    |       |       | 可选 cross-encoder 对粗排候选做(query, chunk)语义匹配打分
    |       |       | 按精排分数二次排序，取前 4 个高置信度候选
    |       |       v
    |       +-> [2.6] Self-RAG 评估
    |       |       | 对每个 chunk 判断:
    |       |       |   - 是否相关 (IS_RELEVANT)
    |       |       |   - 是否支持答案 (IS_SUPPORTED)
    |       |       |   - 是否有帮助 (IS_USEFUL)
    |       |       | 过滤低分 chunk, 只保留高置信度证据
    |       |       v
    |       +-> [2.7] 批判评估
    |               | LLM 判断当前检索结果是否足够回答 query
    |               | 输出 critique 结论: 足够 / 需要改写 / 需要工具
    |       v
    +-> [Step 3] 条件判断: revise_query?
    |       | 依据 Step 2.7 的 critique
    |       | YES -> 回到 Step 1 (最多循环3次)
    |       | NO  -> 继续 Step 4
    |       v
    +-> [Step 4] 条件判断: need_tool?
    |       | 依据 Step 2.7 的判断
    |       | YES -> 调用外部工具 (如计算器/数据库查询)
    |       |       | 工具返回后回到 synthesize 阶段
    |       | NO  -> 继续 Step 5
    |       v
    +-> [Step 5] synthesize_answer
    |       | 基于 Step 2 筛选后的 chunk + parent_doc 生成答案
    |       | 同时组织 citations (指向具体 chunk 和 parent doc)
    |       | 构建 claims (答案中的每个事实声明)
    |       v
    +-> [Step 6] validate_and_save
            |
            +-> [6.1] Gate 校验
            |       | refusal gate: 检测是否需要拒答
            |       | evidence gate: 验证答案有足够证据
            |       | numeric gate: 检查数值类答案的准确性
            |       v
            +-> [6.2] 结构化输出
            |       | 按照 API schema 组装
            |       | answer + citations + claims + decision_log + debug
            |       v
            +-> [6.3] 落盘 artifacts
                    | 写入磁盘或持久化存储
                    v
[API 返回]
    v
[用户]
```

# RFC-003 Contextual Retrieval

## 状态

Implemented (feature flag, 默认关闭) — 2026-08-20 定论

## 定论 (2026-08-20)

本 RFC 的直接目标 `retrieval_recall_at_5 >= 0.6` 已通过其他路径达成 (v10b: TARG 金融术语路由修复 + 远程 reranker + recall 主 gold 口径修正, recall@5=0.78), Contextual Retrieval 不再是当前 recall 的主路径.

实现与实验结论.

- 代码已实现: `indexer.py` 的 `_generate_context_briefs` 在索引期为每个 chunk 生成 LLM 上下文摘要, 存入 `context_brief` 字段, embedding 基于 `[brief]\n[chunk_text]` 拼接; 由 `settings.features.contextual_briefs` 开关控制
- 默认关闭, 原因: 实验发现 Qwen/Qwen3-Embedding-4B 配合 contextual briefs 时, 文档级摘要会稀释 chunk 自身的术语信号 (如 FRTB/Delta 等术语被摘要摊薄), 检索准确率反而下降; 该现象对弱 embedding 模型尤其明显
- 适用条件: 换用更强的 embedding 模型 (或 chunk 独立性极弱的语料) 时可重新开启评估, 开启会触发索引全量重建 (schema fingerprint 变化)

后续动作: 维持默认关闭, 在更换 embedding 模型的评测计划中作为对照项重新验证.

## 目标

在索引阶段为每个 chunk 注入文档级上下文摘要, 从根源上解决 chunk 脱离上下文后的语义歧义问题.  
直接目标是把 retrieval_recall_at_5 从 0.500 提升到 0.6 以上.

## 背景

### 问题

当前 recall_at_5=0.500, 12/50 题召回失败.  
根因之一是金融文档中的 chunk 脱离了文档上下文后, 语义高度模糊.

举例: chunk 内容是 "revenue grew 3% in Q4".  
这个 chunk 在没有上下文时, 和任何其他公司的 revenue chunk 无法区分.  
dense embedding 和 BM25 都无法区分.

### 业界方案

Anthropic 在 2024 年 9 月提出 Contextual Retrieval.  
核心思想: 在索引阶段, 用 LLM 为每个 chunk 生成一段上下文摘要, 拼在 chunk 前面再做 embedding 和 BM25 索引.

**Anthropic 官方数据**:
- 检索失败率降低 49% (仅 contextual embedding)
- 检索失败率降低 67% (contextual embedding + contextual BM25 + rerank)
- 成本约 $0.50/百万 chunk (配合 prompt caching)

**适用场景**: 金融/法律/医疗等文档中 chunk 独立性弱、上下文依赖强的领域.

## 提案

### 核心流程

```
原始 chunk
    │
    ▼
LLM 生成上下文摘要 (50-100 tokens)
    "本 chunk 来自 BCBS d457 文档, 讨论的是 FRTB 框架下
     的 delta 敏感度风险权重计算方法, 位于第三部分
     标准化计量方法章节"
    │
    ▼
拼接: [上下文摘要] + [原始 chunk]
    │
    ▼
分别用于:
  ├── dense embedding (text-embedding-3-small)
  └── BM25 倒排索引
    │
    ▼
检索时: query 直接和拼接后的文本做相似度匹配
```

### 实施范围

- 在 `indexer.py` 的 chunk 写入前增加 context 生成步骤
- 上下文摘要存储为 chunk 的 `context_brief` 字段
- dense embedding 和 BM25 索引都基于 `[context_brief]\n[chunk_text]` 拼接
- 检索结果返回时, `context_brief` 作为额外字段暴露给 reranker 和 synthesizer

### Prompt 设计

```
<document>
{WHOLE_DOCUMENT}
</document>
Here is the chunk we want to situate within the whole document:
<chunk>
{CHUNK_CONTENT}
</chunk>
Please give a short succinct context to situate this chunk within
the overall document for the purposes of improving search retrieval
of the chunk. Answer only with the succinct context and nothing else.
```

### 成本控制

- 使用 prompt caching: 文档整体作为 cache prefix, 每个 chunk 只发增量
- 使用低成本模型 (如 deepseek-chat) 生成上下文
- 预估成本: 1464 个 chunk × 约 500 tokens/chunk = ~732K tokens, 配合 prompt caching 约 $0.3-0.5
- 一次性成本, 索引重建时才需要重新生成

### 与现有索引的兼容

- 新增 `context_brief` 字段到 Milvus collection schema
- 索引 manifest 版本号 +1, 触发自动重建
- 旧索引不兼容, 需要全量重建
- 重建后 qrels 的 chunk_id 不变 (还是基于 source + chunk_index)

## 优先级

P0. 这是解决 recall_at_5=0.500 最直接最有效的手段.

## 预期收益

- retrieval_recall_at_5 从 0.500 提升到 0.65-0.75 (基于 Anthropic 数据推算)
- dense 检索命中率从 72% 提升到 85%+
- 金融术语消歧能力显著增强

## 预期风险

- 上下文摘要质量依赖 LLM, 质量差会引入噪声
- 索引重建耗时增加 (LLM 调用 1464 次)
- Milvus schema 变更需要全量重建
- prompt caching 依赖 OpenRouter 支持, 需验证

## 成功标志

- retrieval_recall_at_5 >= 0.6
- dense 命中率 >= 80%
- 12 个失败题目中至少 8 个转为命中
- threshold gate 通过

## 关联文档

- [RFC-001](./RFC-001-retrieval-hardening-roadmap.md) - 检索强化总纲, 本 RFC 是其 P0 子项
- [ARCHITECTURE.md](../ARCHITECTURE.md) - 索引架构
- [Anthropic Contextual Retrieval 原文](https://www.anthropic.com/news/contextual-retrieval)

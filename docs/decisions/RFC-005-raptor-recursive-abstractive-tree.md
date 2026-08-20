# RFC-005 RAPTOR 递归摘要树索引

## 状态

Proposed (长期规划, P3)

## 目标

构建多层级递归摘要索引树, 让检索能在不同抽象层级取信息.  
解决当前单层 Summary Index 无法回答宏观问题的局限.

## 背景

### 问题

当前项目的索引是扁平的:
- chunk 级: 原始文档切块 (512 tokens)
- summary 级: 每个 source 的单层摘要

无法回答这类问题:
- "BCBS d457 文档整体讲了什么?" (需要文档级摘要)
- "FRTB 框架的核心模块有哪些?" (需要跨 section 摘要)
- "Basel III 和 FRTB 的关系是什么?" (需要跨文档摘要)

### 业界方案

**RAPTOR (ICLR 2024)**:
- Recursive Abstractive Processing for Tree-Organized Retrieval
- 核心思想: 递归地聚类 -> 摘要 -> 再聚类 -> 再摘要, 构建一棵从底向上的树
- QuALITY benchmark 准确率提升 20%
- 能同时回答细节问题和宏观问题

**树结构示意**:

```
Level 3:  [Root Summary]                          ← 整个语料库摘要
             /        \
Level 2:  [Cluster A]  [Cluster B]               ← 主题级摘要
          /    \       /    \
Level 1: [S1]  [S2]  [S3]  [S4]                  ← 文档级摘要
         /|\   /|\   /|\   /|\
Level 0: chunks chunks chunks chunks              ← 原始 chunk
```

检索时可以从不同层级取信息:
- 细节问题: 检索 Level 0
- 文档级问题: 检索 Level 1
- 主题级问题: 检索 Level 2-3
- 混合问题: 跨层检索 + 融合

## 提案

### 实施范围

#### 索引构建

1. Level 0: 原始 chunk (已有)
2. Level 1: 按 source 分组, LLM 生成文档级摘要 (已有, 对标 Summary Index)
3. Level 2: 按 section_path 主题聚类, LLM 生成主题级摘要 (新增)
4. Level 3: 全语料库聚类, LLM 生成根摘要 (新增)

#### 聚类策略

- Level 0 -> Level 1: 按 source 字段分组 (已有)
- Level 1 -> Level 2: 按 embedding 语义聚类 (GMM / HDBSCAN)
- Level 2 -> Level 3: 人工分类或 LLM 分类

金融文档的天然主题分类:
- 监管框架 (FRTB / Basel III / SA-CCR)
- 风险类型 (市场风险 / 信用风险 / 操作风险)
- 文档类型 (BCBS 标准 / ISDA 行业报告 / FSB 政策)

#### 检索策略

```python
def raptor_retrieve(query, top_k=5):
    # 1. 在所有层级同时检索
    level_0_hits = dense_search(query, level=0, k=top_k)
    level_1_hits = dense_search(query, level=1, k=top_k//2)
    level_2_hits = dense_search(query, level=2, k=top_k//4)

    # 2. 跨层 RRF 融合
    merged = rrf_fuse([level_0_hits, level_1_hits, level_2_hits])

    # 3. 返回融合后的 top_k
    return merged[:top_k]
```

#### 与现有索引的兼容

- Level 0 = 原始 chunk 索引 (不变)
- Level 1 = 现有 Summary Index (升级为 RAPTOR Level 1)
- Level 2-3 = 新增, 存储到 Milvus 的新 collection 或同 collection 的不同 partition
- 检索时自动跨层融合

### 文件组织

```
src/riskagent_agenticrag/indexing/
    raptor.py           # RAPTOR 树构建和检索
    clustering.py       # 语义聚类 (GMM / HDBSCAN)
```

## 优先级

P3. 长期规划, 在 Contextual Retrieval 和 Agentic RAG 之后.

前置条件:
- P0: Contextual Retrieval ([RFC-003](./RFC-003-contextual-retrieval.md)) 落地
- P2: Agentic RAG ([RFC-004](./RFC-004-agentic-rag-paradigm.md)) 工具化检索落地

## 预期收益

- 能回答宏观问题 ("这个文档讲了什么")
- 多跳推理准确率提升 15-20% (基于 RAPTOR 论文数据)
- 跨文档关联查询能力增强

## 预期风险

- 摘要质量依赖 LLM, 低质量摘要会误导检索
- 索引构建时间和成本增加 (需要多次 LLM 调用)
- 聚类策略需要调参, 金融文档可能不适合通用 embedding 聚类
- 跨层融合的权重需要实验确定

## 成功标志

- 宏观问题 ("文档讲了什么") 召回率 >= 0.8
- 多跳推理准确率提升 10%+
- 新增的层级不会降低细节问题的召回率

## 关联文档

- [RFC-003](./RFC-003-contextual-retrieval.md) - Contextual Retrieval, 索引层前置条件
- [RFC-004](./RFC-004-agentic-rag-paradigm.md) - RAPTOR 可作为 Agentic RAG 的工具
- [ARCHITECTURE.md](../ARCHITECTURE.md) - 索引架构
- [RAPTOR 论文 (ICLR 2024)](https://openreview.net/attachment?id=GN921JHCRw&name=pdf)

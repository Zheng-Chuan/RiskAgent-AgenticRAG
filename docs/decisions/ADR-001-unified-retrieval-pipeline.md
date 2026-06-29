# ADR-001 Unified Retrieval Pipeline

## 状态

Accepted

## 背景

早期 RAG 项目常见问题是不断切换 retrieval mode.  
这会让运行时行为 文档口径 评测口径和发布口径越来越不一致.

## 决策

默认检索主链固定为:

`AdvancedIndexRetriever -> QueryIntelligentRetriever -> HybridRetriever`

运行时不再把 dense only hybrid only summary only 作为对外主模式.  
允许通过参数调节 `dense_k` `sparse_k` `candidate_k` `rerank_k` `summary_k` `hyde_k`.

## 后果

### 正面

- 对外口径更稳定
- 评测更容易做回归
- 发布门禁更清晰

### 代价

- 单条主链复杂度上升
- 需要更强的观测和配置治理

## 相关文件

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [retriever_factory.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_agenticrag/rag/retriever_factory.py)

# ARCHITECTURE

## 高层目标

- 面向企业内部软件工程师
- 使用 RAG 提供基于语料的解释
- answer 必须带 citations
- multi-agent 结构, 便于后续扩展
- LLM provider 可插拔

## 核心模块

- `riskagent_rag.rag`
  - ingest, chunk, index
  - retrieve
- `riskagent_rag.llm`
  - provider interface
  - openai compatible client
  - mock client
- `riskagent_rag.agents`
  - retrieval agent
  - explanation agent
  - coordinator

## 数据流

sources -> chunk -> embeddings -> chroma
query -> retrieve -> contexts -> multi-agent -> answer + citations

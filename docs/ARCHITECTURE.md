# ARCHITECTURE

## 高层目标

- 面向企业内部软件工程师
- 使用 RAG 提供基于语料的解释
- answer 必须带 citations
- multi-agent 结构, 便于后续扩展
- LLM provider 可插拔

## 开源大模型接入

原则: 不绑定单一厂商, 统一通过 OpenAI compatible 接口对接.

- 商业 API: 直接配置 `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`
- 开源模型: 在云端或本地用 vLLM, TGI, Ollama 等启动 OpenAI compatible server, 再通过 `LLM_BASE_URL` 接入

说明: Week 1 允许无 key 的 deterministic fallback, 先验证 RAG 链路与 citations. Week 2 会引入真实 LLM, 并将 LLM provider 切换为 OpenAI compatible server.

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

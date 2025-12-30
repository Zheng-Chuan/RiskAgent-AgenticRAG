# RiskAgent-RAG Docs

该项目用于将金融衍生品与风险管理相关资料, 以 RAG + multi-agent 的方式转化为面向企业内部软件工程师的通俗解释, 并在回答中提供可追溯 citations.

## 快速入口

- ROADMAP: `docs/ROADMAP.md`
- QUICKSTART: `docs/QUICKSTART.md`
- SETUP: `docs/SETUP.md`
- ARCHITECTURE: `docs/ARCHITECTURE.md`
- FEATURES: `docs/FEATURES.md`

## 技术栈

- UI: Gradio
- Multi-agent orchestration: LangGraph
- LLM provider: OpenAI compatible API via pluggable adapter layer
- RAG: TBD, LlamaIndex or LangChain
- Vector store: Chroma
- Observability: TBD, LangSmith or Arize Phoenix

## 文档与语料管理

- 语料默认放在 `docs/sources/`.
- 索引默认落地到 `.chroma/`.
- 建议每次语料变更后重新构建索引, 保证 citations 与内容一致.

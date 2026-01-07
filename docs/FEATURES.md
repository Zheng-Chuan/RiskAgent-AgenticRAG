# FEATURES

## 已规划功能

- RAG ingest 与本地向量索引
- citations 与可追溯来源
- 可插拔 LLM provider
- multi-agent 编排
- 简单漂亮的 Python UI

## 已实现(MVP)

- Gradio UI: `gradio_app.py`
- CLI demo: `demo_cli.py`
- e2e smoke test: `smoke_test.py`
- 离线可运行模式
  - embeddings 使用 FakeEmbeddings
  - 未配置 API key 时使用 deterministic fallback answer

## 近期优先级

- Phase 1 MVP, 先保证可复现闭环
- Phase 2 引入评测与质量控制

## 开源大模型接入计划

- Week 2 起接入真实 LLM, 推荐通过 OpenAI compatible server(vLLM, TGI, Ollama)对接.

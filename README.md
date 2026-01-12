# RiskAgent-RAG Docs

该项目用于将金融衍生品与风险管理相关资料, 以 RAG + multi-agent 的方式转化为面向企业内部软件工程师的通俗解释, 并在回答中提供可追溯 citations.

## 文档目录

- `docs/QUICKSTART.md`
  - 本地快速启动, 包含安装依赖, 准备语料, UI 和 CLI 运行方式, 以及测试
- `docs/ROADMAP.md`
  - 迭代计划与验收口径, 聚焦本地可运行 demo 的多 agent 主线
- `docs/ARCHITECTURE.md`
  - 高层目标与模块拆分, 以及 LLM provider 的接入原则
- `docs/INTERVIEW.md`
  - 50 道 MultiAgent RAG 面试题, 边做边补答案

## 快速入口

推荐使用 conda 环境 `LangChain`.

- UI

```bash
conda run -n LangChain python gradio_app.py
```

- CLI

```bash
conda run -n LangChain python demo_cli.py --rebuild-index --question "what is FRTB"
```

- 评测

```bash
conda run -n LangChain python -m unittest tests.test_week2_acceptance
```

## 技术栈

- UI: Gradio
- Multi-agent orchestration: LangGraph
- LLM provider: OpenAI compatible API via pluggable adapter layer
- RAG framework: LangChain
- Vector store: Chroma

## 文档与语料管理

- 语料默认放在 `docs/sources/`.
- 索引默认落地到 `.chroma/`.
- 建议每次语料变更后重新构建索引, 保证 citations 与内容一致.

## 开源大模型接入说明

这个项目会接入开源大模型, 但我们不把它写死成某一个具体厂商.

当前实现采用 OpenAI compatible 的方式对接 LLM. 这意味着你可以:

- 使用商业 API(例如 OpenAI compatible provider)
- 使用开源模型推理服务(例如 vLLM, TGI, Ollama), 只要它提供 OpenAI compatible endpoint

配置方式是通过环境变量:

- `LLM_API_KEY`(可选, 部分服务需要)
- `LLM_BASE_URL`(你的推理服务 base url)
- `LLM_MODEL`(模型名)

为了保证 Week 1 可复现, 没有配置 key 时会走 deterministic fallback, 先验证 RAG 链路与 citations.

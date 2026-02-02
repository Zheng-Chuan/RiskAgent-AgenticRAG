# RiskAgent-AgenticRAG Docs

这个项目想解决的是看资料很费劲这个问题
你把问题丢进来
它会用工程师更容易读的方式讲一遍
同时把引用贴出来
你随时可以回到原文核对

## 文档目录

- [QUICKSTART](docs/QUICKSTART.md)
  - 新手从这里开始 装依赖 准备语料 启动 UI 和 CLI 跑测试
- [ROADMAP](docs/ROADMAP.md)
  - 我们打算怎么做 每一阶段怎么验收
- [ARCHITECTURE](docs/ARCHITECTURE.md)
  - 代码怎么拆 数据怎么流 LLM 怎么接
- [DATA](docs/DATA.md)
  - 数据字典 关键中间数据结构与用途 例如 chunk citations evidence claims
- [EVALUATION](docs/EVALUATION.md)
  - 评测指南 RAGAS 与自定义指标 以及如何对比报告
- [TIMELINE_EXPLAINABILITY](docs/TIMELINE_EXPLAINABILITY.md)
  - 从 Week1 到 Week7 的可解释性与评估体系演进时间线
- [INTERVIEW](docs/INTERVIEW.md)
  - 50 道多智能体和 RAG 面试题 做项目时顺手把答案补全

## 快速入口

推荐使用 conda 环境 `LangChain`

### 1. 开发环境安装 (关键)

为了避免 import 报错 请务必以 editable 模式安装本项目

```bash
# 方式一：使用 Makefile (推荐)
make install

# 方式二：手动 pip
pip install -e .
```

### 2. 启动本地中间件


本项目用 Docker compose 启动本地中间件

```bash
docker compose -f deploy/dev/docker-compose.yml up -d
```

Docker Desktop 分组名 riskagent-agenticrag

- **Milvus**
  - 容器名 riskagent-agenticrag-milvus
  - 端口 19530

### 3. 启动 UI

```bash
conda run -n LangChain python gradio_app.py
```

### 4. 启动 CLI

```bash
conda run -n LangChain python demo_cli.py --rebuild-index --question "what is FRTB"
```

### 5. 运行评测

```bash
conda run -n LangChain python -m unittest tests.test_week2_rag_citation_quality
```

## 技术栈

- UI: Gradio
- Agent 编排: LangGraph
- LLM 接入: OpenAI compatible API
- RAG framework: LangChain
- Vector store: Milvus

## 文档与语料管理

- 语料默认放在 `corpus/`
- 索引默认落地到 `.milvus/` 这是 Milvus Lite 的单文件落盘
- 语料变了建议重新 build index 不然引用可能会对不上

如需使用 Docker Milvus 请设置环境变量 MILVUS_HOST=localhost MILVUS_PORT=19530

## 开源大模型接入说明

这个项目支持接入开源大模型
但不会把某一家厂商写死在代码里

当前实现走 OpenAI compatible 接口对接 LLM
所以你可以

- 使用商业 API(例如 OpenAI compatible provider)
- 使用开源模型推理服务(例如 vLLM, TGI, Ollama), 只要它提供 OpenAI compatible endpoint

配置方式走环境变量

- `LLM_API_KEY` 可选 部分服务需要
- `LLM_BASE_URL` 你的推理服务 base url
- `LLM_MODEL` 模型名

为了保证本地可复现
没有配置 key 时会走 deterministic fallback
先把检索链路和引用跑通

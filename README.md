# RiskAgent-AgenticRAG Docs

这个项目想解决的是看资料很费劲这个问题
你把问题丢进来
它会用工程师更容易读的方式讲一遍
同时把引用贴出来
你随时可以回到原文核对

## 文档目录

- [OVERVIEW](docs/OVERVIEW.md)
  - 一页读懂 当前架构和使用路径
- [QUICKSTART](docs/QUICKSTART.md)
  - 新手从这里开始 装依赖 准备语料 启动 UI 和 CLI 跑测试
- [ROADMAP](docs/ROADMAP.md)
  - 我们打算怎么做 每一阶段怎么验收
- [ARCHITECTURE](docs/ARCHITECTURE.md)
  - 代码怎么拆 数据怎么流 LLM 怎么接
- [API](docs/API.md)
  - HTTP API v1 用法 健康检查 指标与鉴权
- [TRACE](docs/TRACE.md)
  - trace.json 字段说明 如何用 trace 排障
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

### 4. 增量索引 (CLI)

```bash
conda run -n LangChain python -m riskagent_rag.cli.index --corpus-dir corpus --persist-dir .milvus
```

### 5. 启动 CLI

```bash
conda run -n LangChain python demo_cli.py --question "what is FRTB"
```

### 6. 运行评测

```bash
conda run -n LangChain python -m riskagent_rag.evaluation.run --stage step4 --label step4
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
- 索引构建为增量模式 会跳过未变化的文件 并对变更文件做重建

如需使用 Docker Milvus 请设置环境变量 MILVUS_HOST=localhost MILVUS_PORT=19530

## 开源大模型接入说明

这个项目支持接入开源大模型
但不会把某一家厂商写死在代码里

当前实现走 OpenAI compatible 接口对接 LLM
所以你可以

- 使用商业 API(例如 OpenAI compatible provider)
- 使用开源模型推理服务(例如 vLLM, TGI, Ollama), 只要它提供 OpenAI compatible endpoint

配置方式走环境变量

- `LLM_API_KEY` 或 `OPENAI_API_KEY` 必填
- `LLM_BASE_URL` 你的推理服务 base url
- `LLM_MODEL` 模型名

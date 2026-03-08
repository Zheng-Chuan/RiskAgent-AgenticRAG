# RiskAgent-AgenticRAG Docs

这是一个面向金融风险知识检索与解释的 Agentic RAG 项目。
核心目标是可验证回答：回答必须附带引用，可回放、可排障、可回归。

## 文档目录

- [DOCS](docs/README.md)
  - docs 统一导航入口
- [OVERVIEW](docs/OVERVIEW.md)
  - 一页读懂系统边界、主链路和阅读路径
- [QUICKSTART](docs/QUICKSTART.md)
  - 从安装到本地跑通 UI、CLI、API
- [ROADMAP](docs/ROADMAP.md)
  - 里程碑、交付项和验收口径
- [ARCHITECTURE](docs/ARCHITECTURE.md)
  - 模块边界、调用关系、数据流
- [API](docs/API.md)
  - HTTP API v1 契约和调用示例
- [TRACE](docs/TRACE.md)
  - trace.json 字段说明与排障路径
- [DATA](docs/DATA.md)
  - 关键数据结构说明
- [EVALUATION](docs/EVALUATION.md)
  - 指标定义、对比实验方案、历史实验数据、门禁策略
- [INTERVIEW](docs/INTERVIEW.md)
  - 面试问答和指标速答卡

## 三步跑通

1. 安装依赖

```bash
make install
```

2. 启动中间件

```bash
docker compose -f deploy/dev/docker-compose.yml up -d
```

3. CLI 跑通

```bash
conda run -n LangChain python -m riskagent_rag.cli index --corpus-dir corpus --persist-dir .milvus
conda run -n LangChain python -m riskagent_rag.cli ask --question "what is FRTB"
```

更多命令统一见 [QUICKSTART](docs/QUICKSTART.md)。

## 常用入口

- 增量索引

```bash
conda run -n LangChain python -m riskagent_rag.cli index --corpus-dir corpus --persist-dir .milvus
```

- CLI 提问

```bash
conda run -n LangChain python -m riskagent_rag.cli ask --question "what is FRTB"
```

- 运行评测

```bash
conda run -n LangChain python -m riskagent_rag.evaluation.run --stage step4 --label step4
```

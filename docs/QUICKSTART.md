# QUICKSTART

本项目默认在 conda 环境 `LangChain` 中运行，下面示例命令也默认使用 `conda run -n LangChain ...`。

## 1. 安装依赖

在项目根目录跑下面命令

推荐用 conda 环境 `LangChain`

```bash
conda run -n LangChain python -m pip install -r requirements.txt
```

也可以用 venv

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 启动本地中间件

本项目默认用 Docker compose 启动 Milvus

在项目根目录执行

```bash
docker compose -f deploy/dev/docker-compose.yml up -d
```

启动后你会在 Docker Desktop 里看到分组名 riskagent-rag
里面只有一个 Milvus 容器

- **Milvus**
  - 容器名 riskagent-rag-milvus
  - 端口 19530 和 9091

停止中间件

```bash
docker compose -f deploy/dev/docker-compose.yml down
```

## 3. 准备语料

把 markdown 放到 `corpus/`

建议先放 1 个文件 比如 `Background.md`
你也可以先只放这一份
先把链路跑通再慢慢加

## 4. 配置 LLM

如果你暂时没有 LLM API key, 也可以先用 deterministic 模式把链路跑通

可选环境变量:

- `OPENAI_API_KEY` 或 `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

说明

- 未配置 key 时, 系统会返回 deterministic 输出, 用于验证检索与 citations.
- 配置 key 后, 会使用 OpenAI compatible 接口生成回答.

## 5. 配置 embeddings

可选环境变量:

- `EMBEDDINGS_PROVIDER`: 默认 hf
- `EMBEDDINGS_MODEL`: 默认 sentence-transformers/all-MiniLM-L6-v2

可选环境变量

- `MILVUS_HOST`: 例如 localhost
- `MILVUS_PORT`: 例如 19530

## 6. 启动 UI

```bash
conda run -n LangChain python gradio_app.py
```

## 7. Demo 流程

- 在 UI 里点 build index
- 提一个问题 比如 what is FRTB
- 看看 answer 和 citations

## 8. CLI demo 与 smoke test

- CLI demo 输出会写到 logs/demo_result.json

```bash
conda run -n LangChain python demo_cli.py --rebuild-index --question "what is FRTB"
```

- e2e smoke test

```bash
conda run -n LangChain python -m unittest tests.test_week1_acceptance.Week1AcceptanceTest.test_week1_smoke_test_equivalent
```

## 9. 运行评测

评测会跑 20 个问题, 然后输出 coverage

```bash
conda run -n LangChain python -m unittest tests.test_week2_acceptance

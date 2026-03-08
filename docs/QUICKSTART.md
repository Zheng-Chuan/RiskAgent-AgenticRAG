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

启动后你会在 Docker Desktop 里看到分组名 riskagent-agenticrag
里面只有一个 Milvus 容器

- **Milvus**
  - 容器名 riskagent-agenticrag-milvus
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

必需环境变量:

- `OPENAI_API_KEY` 或 `LLM_API_KEY`
- 可选: `OPENROUTER_SITE_URL` `OPENROUTER_APP_NAME`

未配置或无法连接 LLM 时会直接报错

## 5. 配置 embeddings

可选环境变量:

- `EMBEDDINGS_PROVIDER`: 默认 hf
- `EMBEDDINGS_MODEL`: 默认 sentence-transformers/all-MiniLM-L6-v2

可选环境变量

- `MILVUS_HOST`: 例如 localhost
- `MILVUS_PORT`: 例如 19530

## 6. Demo 流程

- 先用 CLI 做增量索引

```bash
conda run -n LangChain python -m riskagent_rag.cli index --corpus-dir corpus --persist-dir .milvus
```

- 再提问 比如 what is FRTB
- 查看 answer citations decision_log

## 7. CLI demo 与 smoke test

- CLI demo 输出会写到 logs/demo_result.json

```bash
conda run -n LangChain python -m riskagent_rag.cli ask --question "what is FRTB" --out logs/demo_result.json
```

- e2e smoke test

```bash
conda run -n LangChain python -m unittest tests.test_index_incremental_acceptance
```

## 8. 运行评测

评测会跑数据集并落盘报告到 .artifacts/reports

```bash
conda run -n LangChain python -m riskagent_rag.evaluation.run --stage step4 --label step4
```

## 9. 启动 HTTP API

```bash
conda run -n LangChain python -m riskagent_rag.api.server
```

## 10. 用 API 提问并看 trace

```bash
curl -s http://localhost:8000/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"what is frtb"}'
```

返回里会带 debug.artifact_bundle_dir
你可以在这个目录里找到 trace.json
详细字段见 [TRACE.md](./TRACE.md)

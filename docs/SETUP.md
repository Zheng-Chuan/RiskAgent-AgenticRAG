# SETUP

## Python

建议 Python 3.11+.

## 目录约定

- `docs/sources/`: 语料
- `.chroma/`: 本地向量库
- `src/riskagent_rag/`: 核心代码

## 环境变量

- `LLM_PROVIDER`: `mock` 或 `openai_compatible`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

建议通过 `.env` 管理, 但不要提交到 Git.

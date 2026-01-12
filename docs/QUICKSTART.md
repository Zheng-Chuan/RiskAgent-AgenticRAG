# QUICKSTART

## 1. 安装依赖

在项目根目录执行:

推荐(使用 conda 环境 `LangChain`):

```bash
conda run -n LangChain python -m pip install -r requirements.txt
```

备选(使用 venv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 准备语料

把 markdown 放到 `docs/sources/`.

建议先放 1 个文件, 例如 `Background.md` 的拷贝.

## 3. 配置 LLM

如果你暂时没有可用的 LLM API key, 也可以先跑通本地 deterministic 模式.

可选环境变量:

- `OPENAI_API_KEY` 或 `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

说明:

- 未配置 key 时, 系统会返回 deterministic 输出, 用于验证检索与 citations.
- 配置 key 后, 会使用 OpenAI compatible 接口生成回答.

## 4. 配置 embeddings

可选环境变量:

- `EMBEDDINGS_PROVIDER`: 默认 hf
- `EMBEDDINGS_MODEL`: 默认 sentence-transformers/all-MiniLM-L6-v2

## 5. 启动 UI

```bash
conda run -n LangChain python gradio_app.py
```

## 6. Demo 流程

- 在 UI 里点击 build index
- 提一个问题, 例如 what is FRTB
- 观察 answer 和 citations

## 7. CLI demo 与 smoke test

- CLI demo(输出落盘到 logs/demo_result.json)

```bash
conda run -n LangChain python demo_cli.py --rebuild-index --question "what is FRTB"
```

- e2e smoke test(unittest 验收用例)

```bash
conda run -n LangChain python -m unittest tests.test_week1_acceptance.Week1AcceptanceTest.test_week1_smoke_test_equivalent
```

## 8. 运行评测

评测会跑 20 个问题, 并输出 coverage.

```bash
conda run -n LangChain python -m unittest tests.test_week2_acceptance

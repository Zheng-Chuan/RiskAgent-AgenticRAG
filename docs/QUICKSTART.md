# QUICKSTART

## 1. 安装依赖

在项目根目录执行:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 准备语料

把 markdown 或 pdf 放到 `docs/sources/`.

建议先放 1 个文件, 例如 `Background.md` 的拷贝.

## 3. 配置 LLM

如果你暂时没有可用的 LLM API, 也可以先使用 mock 模式跑通 UI.

可选环境变量:

- `LLM_PROVIDER`: `mock` 或 `openai_compatible`
- `LLM_API_KEY`: API key
- `LLM_BASE_URL`: OpenAI compatible base url
- `LLM_MODEL`: model name

## 4. 启动 UI

```bash
python gradio_app.py
```

## 5. Demo 流程

- 在 UI 里点击 build index
- 提一个问题, 例如 what is FRTB
- 观察 answer 和 citations

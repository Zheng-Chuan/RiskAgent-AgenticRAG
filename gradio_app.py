from __future__ import annotations

import pathlib
import sys
from typing import Any

import gradio as gr

# Gradio 入口文件.
# MVP 目标是 1 条命令启动 UI, 并跑通 build index -> ask -> answer + citations.
#
# 启动方式.
# - conda run -n LangChain python gradio_app.py
#
# 目录约定.
# - docs/sources: 放置 markdown 语料.
# - .chroma: Chroma 持久化目录.

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    # 让用户可以直接 python gradio_app.py 启动, 不依赖安装 editable package.
    # 后续如果引入 pyproject.toml, 可以去掉该 hack.
    sys.path.insert(0, str(SRC_DIR))

from riskagent_rag.graph.workflow import build_rag_graph
from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index


SOURCES_DIR = PROJECT_ROOT / "docs" / "sources"
PERSIST_DIR = PROJECT_ROOT / ".chroma"

_graph = None


def _ensure_graph() -> Any:
    # graph 缓存.
    # build index 后会重置缓存, 重新加载最新向量库.
    # 技术难点: UI 交互是有状态的, 但向量库在磁盘上可能被重建.
    # - 如果不重置缓存, 用户会看到旧索引的检索结果, citations 会失真.
    global _graph
    if _graph is not None:
        return _graph

    # 从本地持久化目录加载向量库, 并构建 retriever.
    vectorstore = load_index(PERSIST_DIR)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    # 业务不清晰点: k 值和检索策略未来如何定义.
    # - Week 2 会基于种子问题集做调参, 并把策略固化.
    # 编排最小 LangGraph: retrieve -> answer.
    _graph = build_rag_graph(retriever)
    return _graph


def on_build_index() -> str:
    # UI 按钮回调.
    # 从 docs/sources 构建向量库, 落地到 .chroma.
    # 技术难点: ingest 必须稳定, 否则 Week 2 的引用覆盖率无法对比.
    result = build_index(sources_dir=SOURCES_DIR, persist_dir=PERSIST_DIR)

    global _graph
    # 索引更新后重置 graph 缓存, 确保后续问题使用新索引.
    _graph = None

    return (
        "Index ready. "
        f"sources={result.source_count}, chunks={result.chunk_count}, persist_dir={result.persist_dir}"
    )


def chat(user_text: str, history: list[tuple[str, str]]):
    # ChatInterface 回调.
    # history 当前未用, 先保持参数以满足 Gradio 的签名要求.
    # 业务不清晰点: 是否需要多轮对话记忆.
    # - 多轮会引入更复杂的 context 管理与成本控制.
    # - MVP 先做单轮问答, Week 3 再扩展为多角色多轮.
    if not user_text:
        return ""

    if not PERSIST_DIR.exists():
        return "Index not found. Click 'Build index' first."

    graph = _ensure_graph()
    # graph.invoke 会返回最终 state, 其中包含 docs 和 answer.
    out = graph.invoke({"question": user_text})

    answer = out.get("answer", "")
    docs = out.get("docs", [])
    citations = extract_citations(docs)

    citations_md = "\n".join(
        [f"- source={c['source']} chunk_id={c['chunk_id']}" for c in citations]
    )

    # MVP 先用 markdown 文本展示 citations.
    # 后续可以改成更结构化的 UI, 例如 DataFrame 或可点击链接.
    # 技术难点: citations 一旦对外展示就是 contract, 后续字段扩展要考虑兼容.

    return f"{answer}\n\nCitations:\n{citations_md}"


def main() -> None:
    with gr.Blocks(title="RiskAgent-RAG") as demo:
        gr.Markdown("# RiskAgent-RAG\nMVP: Gradio + LangChain + Chroma + LangGraph")

        with gr.Row():
            build_btn = gr.Button("Build index", variant="primary")
            status = gr.Textbox(label="Status", interactive=False)

        chat_ui = gr.ChatInterface(
            fn=chat,
        )

        # 事件绑定.
        # 点击 build 按钮后, status 会显示本次 ingest 的统计信息.

        build_btn.click(fn=on_build_index, inputs=None, outputs=status)

    demo.launch()


if __name__ == "__main__":
    main()

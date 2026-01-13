from __future__ import annotations

import json
import os
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

from riskagent_rag.config.langsmith import get_langsmith_status, setup_langsmith
from riskagent_rag.graph.workflow import build_rag_graph
from riskagent_rag.orchestration.langgraph_runner import (
    run_langgraph_agentic_chat,
    visualize_graph_mermaid,
)
from riskagent_rag.rag.agentic_loop import run_agentic_chat
from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index


SOURCES_DIR = PROJECT_ROOT / "docs" / "sources"
PERSIST_DIR = PROJECT_ROOT / ".chroma"

_graph = None
_retriever = None


_COOL_CSS = """
.gradio-container * {
  transition: background-color 120ms ease, border-color 120ms ease, box-shadow 150ms ease,
              transform 120ms ease, opacity 120ms ease;
}

.gradio-container {
  --ig-border: rgba(219, 219, 219, 1);
  --ig-border-light: rgba(239, 239, 239, 1);
  --ig-blue: rgba(0, 149, 246, 1);
  --ig-blue-hover: rgba(0, 149, 246, 0.08);
  --ig-text: rgba(38, 38, 38, 1);
  --ig-text-light: rgba(142, 142, 142, 1);
  --ig-bg: rgba(255, 255, 255, 1);
  --ig-bg-secondary: rgba(255, 255, 255, 1);
}

.gradio-container {
  background: #ffffff;
}

.ra-header {
  padding: 20px;
  border: 1px solid var(--ig-border);
  border-radius: 16px;
  background: var(--ig-bg);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.ra-title {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.3px;
  color: var(--ig-text);
  margin: 0;
}

.ra-subtitle {
  margin: 8px 0 0 0;
  color: var(--ig-text-light);
  font-size: 14px;
  font-weight: 400;
}

.ra-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  margin-top: 12px;
  border-radius: 8px;
  border: 1px solid var(--ig-border-light);
  background: var(--ig-bg-secondary);
  color: var(--ig-text-light);
  font-size: 12px;
  font-weight: 500;
}

.ra-panel {
  border: 1px solid var(--ig-border);
  border-radius: 16px;
  background: var(--ig-bg);
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.ra-panel:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.ra-panel h3 {
  margin: 0 0 12px 0;
  color: var(--ig-text);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.1px;
  background: var(--ig-bg) !important;
}

.ra-hint {
  color: var(--ig-text-light);
  font-size: 12px;
  line-height: 1.5;
}

.ra-chat {
  border: 1px solid var(--ig-border);
  border-radius: 16px;
  background: var(--ig-bg);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.ra-inspector {
  border: 1px solid var(--ig-border);
  border-radius: 16px;
  background: var(--ig-bg);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.ra-inspector:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

button, .gr-button {
  border-radius: 8px !important;
  font-weight: 600 !important;
}

button:hover, .gr-button:hover {
  background: var(--ig-blue-hover) !important;
}

button[variant="primary"], .gr-button[variant="primary"] {
  background: var(--ig-blue) !important;
  border-color: var(--ig-blue) !important;
}

button[variant="primary"]:hover, .gr-button[variant="primary"]:hover {
  background: rgba(0, 149, 246, 0.92) !important;
}

input:focus, textarea:focus, .gr-textbox:focus-within {
  border-color: var(--ig-text-light) !important;
  box-shadow: none !important;
}

@media (prefers-reduced-motion: reduce) {
  .gradio-container * {
    transition: none !important;
  }
}

code, pre {
  background: var(--ig-bg-secondary) !important;
  border: 1px solid var(--ig-border-light) !important;
  border-radius: 6px !important;
  font-size: 13px !important;
}

.ra-panel .block, .ra-panel .prose, .ra-panel .svelte-16ln60g {
  background: var(--ig-bg) !important;
}

.gr-group {
  background: var(--ig-bg) !important;
}
"""


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


def _ensure_retriever() -> Any:
    # 中文注释: Week3 agentic loop 需要直接使用 retriever.
    global _retriever
    if _retriever is not None:
        return _retriever

    vectorstore = load_index(PERSIST_DIR)
    _retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    return _retriever


def on_build_index() -> str:
    # UI 按钮回调.
    # 从 docs/sources 构建向量库, 落地到 .chroma.
    # 技术难点: ingest 必须稳定, 否则 Week 2 的引用覆盖率无法对比.
    result = build_index(sources_dir=SOURCES_DIR, persist_dir=PERSIST_DIR)

    global _graph
    # 索引更新后重置 graph 缓存, 确保后续问题使用新索引.
    _graph = None

    global _retriever
    _retriever = None

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

    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider == "ollama":
        retriever = _ensure_retriever()
        out = run_agentic_chat(question=user_text, retriever=retriever, max_rounds=2)
        answer = str(out.get("answer", ""))
        citations = out.get("citations", [])
        decision_log = out.get("decision_log", [])
        tool_traces = out.get("tool_traces", [])
        debug = out.get("debug", {})

        citations_md = "\n".join(
            [f"- source={c.get('source','')} chunk_id={c.get('chunk_id','')}" for c in citations]
        )
        decision_md = json.dumps(decision_log, ensure_ascii=False, indent=2)
        tool_md = json.dumps(tool_traces, ensure_ascii=False, indent=2)
        debug_md = json.dumps(debug, ensure_ascii=False, indent=2)

        return (
            f"{answer}\n\n"
            f"Citations:\n{citations_md}\n\n"
            "Decision log:\n"
            f"```json\n{decision_md}\n```\n\n"
            "Tool traces:\n"
            f"```json\n{tool_md}\n```\n\n"
            "Debug:\n"
            f"```json\n{debug_md}\n```"
        )

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


def _env_badge_text() -> str:
    provider = os.getenv("LLM_PROVIDER", "").lower().strip() or "fallback"
    use_langgraph = os.getenv("USE_LANGGRAPH", "").lower().strip() in ("true", "1", "yes")
    langsmith_status = get_langsmith_status()
    
    lines = []
    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "") or "unknown"
        base_url = os.getenv("OLLAMA_BASE_URL", "") or "http://localhost:11434"
        lines.append(f"provider=ollama, model={model}")
        lines.append(f"base_url={base_url}")
    else:
        lines.append(f"provider={provider}")
    
    lines.append(f"langgraph={'enabled' if use_langgraph else 'disabled'}")
    
    if langsmith_status["enabled"] == "true":
        lines.append(f"langsmith=enabled, project={langsmith_status['project']}")
        if langsmith_status["url"]:
            lines.append(f"追踪: {langsmith_status['url']}")
    else:
        lines.append("langsmith=disabled")
    
    return "\n".join(lines)


def chat_v2(
    user_text: str,
    history: list[list[str]],
    max_rounds: int,
) -> tuple[list[list[str]], list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    # 中文注释: v2 UI 回调, 输出 chat history + inspector.
    if not user_text:
        return history, [], [], [], {}

    if not PERSIST_DIR.exists():
        answer = "Index not found. Click 'Build index' first."
        history = history + [[user_text, answer]]
        return history, [], [], [], {"error": "index_missing"}

    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider == "ollama":
        retriever = _ensure_retriever()
        
        use_langgraph = os.getenv("USE_LANGGRAPH", "").lower().strip() in ("true", "1", "yes")
        
        if use_langgraph:
            out = run_langgraph_agentic_chat(question=user_text, retriever=retriever, max_rounds=max_rounds)
        else:
            out = run_agentic_chat(question=user_text, retriever=retriever, max_rounds=max_rounds)
        
        answer = str(out.get("answer", ""))
        citations = out.get("citations", [])
        decision_log = out.get("decision_log", [])
        tool_traces = out.get("tool_traces", [])
        debug = out.get("debug", {})
        status_val = out.get("status", "ok")
        failure_reason = out.get("failure_reason")
        
        if use_langgraph:
            debug["runner"] = "langgraph"
        else:
            debug["runner"] = "pure_function"
        
        if status_val == "failed" and failure_reason:
            answer = f"⚠️ Validation failed: {failure_reason.get('message', '')}\n\n{answer}"
            debug["validation_status"] = status_val
            debug["failure_reason"] = failure_reason
        
        history = history + [[user_text, answer]]
        return history, list(citations), list(decision_log), list(tool_traces), dict(debug)

    graph = _ensure_graph()
    out = graph.invoke({"question": user_text})
    answer = str(out.get("answer", ""))
    docs = out.get("docs", [])
    citations = extract_citations(docs)
    history = history + [[user_text, answer]]
    return history, list(citations), [], [], {"note": "non-ollama provider, agentic loop disabled"}


def main() -> None:
    # 中文注释: 启动时自动配置 LangSmith 追踪
    setup_langsmith(project_name="RiskAgent-RAG")
    
    with gr.Blocks(title="RiskAgent-RAG") as demo:
        gr.HTML(
            """
            <div class="ra-header">
              <h1 class="ra-title">RiskAgent-RAG</h1>
              <p class="ra-subtitle">Cold-theme local demo. Agentic RAG loop with citations, tool traces, and inspector.</p>
              <div class="ra-pill">UI: Gradio. RAG: LangChain + Chroma. Orchestration: LangGraph. Local LLM: Ollama.</div>
            </div>
            """
        )

        with gr.Row(equal_height=True):
            with gr.Column(scale=1, min_width=320):
                with gr.Group(elem_classes=["ra-panel"]):
                    gr.Markdown("### Control Panel")
                    build_btn = gr.Button("Build index", variant="primary")
                    status = gr.Textbox(label="Status", interactive=False)

                with gr.Group(elem_classes=["ra-panel"]):
                    gr.Markdown("### Runtime")
                    env_badge = gr.Textbox(
                        label="Active provider",
                        value=_env_badge_text(),
                        interactive=False,
                    )
                    max_rounds = gr.Slider(
                        minimum=0,
                        maximum=3,
                        value=2,
                        step=1,
                        label="max_rounds",
                        info="0 means no re-retrieve.",
                    )


            with gr.Column(scale=2, min_width=520):
                chatbot = gr.Chatbot(
                    label="Chat",
                    height=520,
                    elem_classes=["ra-chat"],
                )
                user_text = gr.Textbox(
                    label="Message",
                    placeholder="Ask a question...",
                )
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear")

                with gr.Accordion("Inspector", open=False, elem_classes=["ra-inspector"]):
                    with gr.Tab("Citations"):
                        citations_json = gr.JSON(label="citations")
                    with gr.Tab("Decision log"):
                        decision_json = gr.JSON(label="decision_log")
                    with gr.Tab("Tool traces"):
                        tool_json = gr.JSON(label="tool_traces")
                    with gr.Tab("Debug"):
                        debug_json = gr.JSON(label="debug")
                    with gr.Tab("Graph"):
                        gr.Markdown("### LangGraph 结构可视化")
                        gr.Markdown("当前 agentic loop 的执行流程图 (需要设置 USE_LANGGRAPH=true 启用)")
                        graph_viz = gr.Textbox(
                            value=visualize_graph_mermaid(),
                            label="Mermaid 流程图代码",
                            lines=20,
                            max_lines=30,
                            interactive=False,
                        )
                        gr.Markdown("""
                        **查看方式**:
                        1. 复制上面的 Mermaid 代码到 [Mermaid Live Editor](https://mermaid.live/) 查看
                        2. 在支持 Mermaid 的 Markdown 编辑器中查看
                        3. 查看 `docs/ARCHITECTURE.md` 文件
                        """)

        state = gr.State([])

        def _on_send(message: str, history: list[list[str]], rounds: int):
            new_history, citations, decisions, tools, debug = chat_v2(message, history, rounds)
            return new_history, new_history, citations, decisions, tools, debug

        def _on_clear():
            return [], [], [], [], [], {}

        # 事件绑定.
        build_btn.click(fn=on_build_index, inputs=None, outputs=status)
        build_btn.click(fn=_env_badge_text, inputs=None, outputs=env_badge)

        send_btn.click(
            fn=_on_send,
            inputs=[user_text, state, max_rounds],
            outputs=[state, chatbot, citations_json, decision_json, tool_json, debug_json],
        )
        user_text.submit(
            fn=_on_send,
            inputs=[user_text, state, max_rounds],
            outputs=[state, chatbot, citations_json, decision_json, tool_json, debug_json],
        )
        clear_btn.click(
            fn=_on_clear,
            inputs=None,
            outputs=[state, chatbot, citations_json, decision_json, tool_json, debug_json],
        )

    demo.launch(css=_COOL_CSS)


if __name__ == "__main__":
    main()

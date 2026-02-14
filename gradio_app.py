from __future__ import annotations

import gradio as gr
from typing import Any

from riskagent_rag.app import system

# Gradio 入口文件.
# MVP 目标是 1 条命令启动 UI, 并跑通 build index -> ask -> answer + citations.
#
# 启动方式.
# - conda run -n LangChain python gradio_app.py

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


def _env_badge_text() -> str:
    """UI 状态展示"""
    return system.get_status()


def chat_v2(
    user_text: str,
    history: list[list[str]],
    _max_rounds: int,
) -> tuple[list[list[str]], list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """处理用户对话"""
    if not user_text:
        return history, [], [], [], {}

    # 调用核心系统
    history_pairs: list[tuple[str, str]] = []
    for pair in history or []:
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        history_pairs.append((str(pair[0] or ""), str(pair[1] or "")))
    out = system.chat(question=user_text, history=history_pairs, max_rounds=int(_max_rounds))

    # 结果解析
    answer = str(out.get("answer", ""))
    citations = out.get("citations", [])
    decision_log = out.get("decision_log", [])
    tool_traces = out.get("tool_traces", [])
    debug = out.get("debug", {})
    status_val = out.get("status", "ok")
    failure_reason = out.get("failure_reason")

    if status_val == "failed" and failure_reason:
        answer = f"Validation failed: {failure_reason.get('message', '')}\n\n{answer}"
        debug["validation_status"] = status_val
        debug["failure_reason"] = failure_reason

    # 如果发生系统错误
    if "message" in out and out.get("status") == "error":
        answer = f"System Error: {out['message']}"

    history = history + [[user_text, answer]]
    return history, list(citations), list(decision_log), list(tool_traces), dict(debug)


def main() -> None:
    # pylint: disable=no-member
    with gr.Blocks(title="RiskAgent-AgenticRAG", css=_COOL_CSS) as demo:
        gr.HTML(
            """
            <div class="ra-header">
              <h1 class="ra-title">RiskAgent-AgenticRAG</h1>
              <p class="ra-subtitle">Cold-theme local demo. Agentic RAG loop with citations, tool traces, and inspector.</p>
              <div class="ra-pill">UI: Gradio. RAG: LangChain + Milvus. Orchestration: LangGraph. Local LLM: Ollama.</div>
            </div>
            """
        )

        with gr.Row(equal_height=True):
            with gr.Column(scale=1, min_width=320):
                with gr.Group(elem_classes=["ra-panel"]):
                    gr.Markdown("### Control Panel")
                    gr.Markdown(
                        "索引构建请使用 CLI:\n\n"
                        "```bash\n"
                        "python -m riskagent_rag.cli.index --corpus-dir corpus --persist-dir .milvus\n"
                        "```\n"
                    )

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
                        gr.Textbox(
                            value=system.get_graph_visualization(),
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

        env_badge.change(fn=_env_badge_text, inputs=None, outputs=env_badge)

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

    # pylint: disable=no-member
    # Gradio events are dynamically added, Pylint cannot detect them correctly.
    demo.launch()


if __name__ == "__main__":
    main()

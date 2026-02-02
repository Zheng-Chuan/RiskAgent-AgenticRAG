"""RiskAgent System App.

Facade 模式，封装 RAG 系统的核心业务逻辑，供 UI 和 CLI 调用。
"""
from __future__ import annotations

from typing import Any

from riskagent_rag.config.langsmith import setup_langsmith
from riskagent_rag.config.settings import settings
from riskagent_rag.indexing.indexer import MANIFEST_FILENAME
from riskagent_rag.orchestration.langgraph_runner import (
    run_langgraph_agentic_chat,
    visualize_graph_mermaid,
)
from riskagent_rag.rag.pipeline import extract_citations
from riskagent_rag.rag.retriever_factory import build_retriever


class RiskAgentSystem:
    """RiskAgent RAG 系统核心类"""

    def __init__(self):
        self._retriever = None
        # 初始化时配置 LangSmith
        setup_langsmith(project_name=settings.project_name)

    def get_status(self) -> str:
        """获取当前系统状态描述"""
        provider = settings.llm.provider
        model = settings.llm.model or "default"
        return f"Provider: {provider} | Model: {model} | Mode: LangGraph"

    def _ensure_resources(self) -> Any:
        """确保 Retriever 和 Graph 已初始化"""
        if self._retriever:
            return self._retriever

        persist_dir = settings.paths.milvus_lite_dir
        self._retriever = build_retriever(persist_dir=persist_dir, final_k=4)
        return self._retriever

    def chat(self, question: str, *, history: list[tuple[str, str]] | None = None) -> dict[str, Any]:
        """处理用户提问"""
        persist_dir = settings.paths.milvus_lite_dir
        if not (persist_dir.exists() and (persist_dir / MANIFEST_FILENAME).exists()):
            return {
                "status": "error",
                "message": "Index not found. Run: python -m riskagent_rag.cli.index --corpus-dir corpus --persist-dir .milvus",
            }

        retriever = self._ensure_resources()
        question_with_history = self._merge_history(question=question, history=history)

        out = run_langgraph_agentic_chat(question=question_with_history, retriever=retriever)
        out["runner"] = "langgraph"

        # 统一补充 citations
        if "citations" not in out and "docs" in out:
            out["citations"] = extract_citations(out["docs"])

        return out

    def _merge_history(self, *, question: str, history: list[tuple[str, str]] | None) -> str:
        if not history:
            return question
        pairs = []
        for u, a in history[-3:]:
            u1 = str(u or "").strip()
            a1 = str(a or "").strip()
            if not u1 and not a1:
                continue
            pairs.append(f"User: {u1}\nAssistant: {a1}")
        if not pairs:
            return question
        return "Conversation so far:\n" + "\n\n".join(pairs) + "\n\nCurrent question:\n" + str(question or "")

    def get_graph_visualization(self) -> str:
        """获取 Mermaid 流程图"""
        return visualize_graph_mermaid()

# 单例实例供简单场景使用
system = RiskAgentSystem()

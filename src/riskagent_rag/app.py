"""RiskAgent System App.

Facade 模式，封装 RAG 系统的核心业务逻辑，供 UI 和 CLI 调用。
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Any

from riskagent_rag.config.langsmith import setup_langsmith
from riskagent_rag.config.settings import settings
from riskagent_rag.graph.workflow import build_rag_graph
from riskagent_rag.orchestration.langgraph_runner import (
    run_langgraph_agentic_chat,
    visualize_graph_mermaid,
)
from riskagent_rag.rag.agentic_loop import run_agentic_chat
from riskagent_rag.rag.ingestion import split_documents
from riskagent_rag.rag.pipeline import extract_citations
from riskagent_rag.rag.source_loader import load_markdown_sources
from riskagent_rag.rag.vectorstore import build_milvus_vectorstore, load_milvus_vectorstore


@dataclass
class IndexResult:
    """索引构建结果"""
    source_count: int
    chunk_count: int
    persist_dir: str


class RiskAgentSystem:
    """RiskAgent RAG 系统核心类"""

    def __init__(self):
        self._graph = None
        self._retriever = None
        # 初始化时配置 LangSmith
        setup_langsmith(project_name=settings.project_name)

    def get_status(self) -> str:
        """获取当前系统状态描述"""
        provider = settings.llm.provider
        model = settings.llm.model or "default"
        mode = "LangGraph" if settings.features.use_langgraph else "AgenticLoop"
        return f"Provider: {provider} | Model: {model} | Mode: {mode}"

    def build_index(self) -> IndexResult:
        """重建知识库索引"""
        sources_dir = settings.paths.corpus_dir
        persist_dir = settings.paths.milvus_lite_dir

        if persist_dir.exists():
            shutil.rmtree(persist_dir)

        sources = load_markdown_sources(sources_dir)
        chunks = split_documents(sources)
        build_milvus_vectorstore(chunks, persist_dir)

        # 索引重建后，重置缓存
        self._graph = None
        self._retriever = None

        return IndexResult(
            source_count=len(sources),
            chunk_count=len(chunks),
            persist_dir=str(persist_dir),
        )

    def _ensure_resources(self) -> tuple[Any, Any]:
        """确保 Retriever 和 Graph 已初始化"""
        if self._graph and self._retriever:
            return self._graph, self._retriever

        persist_dir = settings.paths.milvus_lite_dir
        vectorstore = load_milvus_vectorstore(persist_dir)
        # 默认 k=4
        self._retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        self._graph = build_rag_graph(self._retriever)
        return self._graph, self._retriever

    def chat(self, question: str) -> dict[str, Any]:
        """处理用户提问"""
        if not settings.paths.milvus_lite_dir.exists():
            return {"status": "error", "message": "Index not found. Please build index first."}

        _graph, retriever = self._ensure_resources()
        use_langgraph = settings.features.use_langgraph

        if use_langgraph:
            # LangGraph 模式
            out = run_langgraph_agentic_chat(question=question, retriever=retriever)
            out["runner"] = "langgraph"
        else:
            # 简单 Agentic Loop 模式
            out = run_agentic_chat(question=question, retriever=retriever)
            out["runner"] = "agentic_loop"
        
        # 统一补充 citations
        if "citations" not in out and "docs" in out:
            out["citations"] = extract_citations(out["docs"])

        return out

    def get_graph_visualization(self) -> str:
        """获取 Mermaid 流程图"""
        return visualize_graph_mermaid()

# 单例实例供简单场景使用
system = RiskAgentSystem()

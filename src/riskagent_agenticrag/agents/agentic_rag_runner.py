"""Agentic RAG runner (RFC-004 阶段一).

基于 LLM tool calling 实现 Agentic RAG, 模型自主决定检索策略.
流程:
1. 把 4 个检索工具绑定到 LLM
2. LLM 决定调用哪个工具 -> 执行 -> 返回结果给 LLM
3. LLM 基于检索结果生成答案
4. 最多 max_tool_calls 次工具调用, 防止无限检索

输出 schema 和 run_langgraph_agentic_chat 保持一致, 方便在 app.py 中无缝切换.
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from langchain_core.documents import Document

from riskagent_agenticrag.agents.retrieval_tools import (
    chunk_read,
    keyword_search,
    semantic_search,
    set_retriever_context,
    structured_lookup,
)
from riskagent_agenticrag.config.settings import settings
from riskagent_agenticrag.rag.agentic_primitives import (
    build_claims_from_answer,
    build_evidence_set_from_docs,
)
from riskagent_agenticrag.rag.pipeline import extract_citations

logger = logging.getLogger(__name__)


def _build_system_prompt() -> str:
    """构建 Agentic RAG 的系统 prompt, 指导模型选择工具和检索策略."""
    return """You are a financial risk knowledge assistant. You have access to retrieval tools to find relevant information from a financial document corpus.

Available tools:
- semantic_search: Best for conceptual queries (e.g., "what is FRTB delta risk")
- keyword_search: Best for exact terms, acronyms, numbers (e.g., "BCBS d457", "CVA formula")
- structured_lookup: Best for finding specific sections (e.g., source="frtb.pdf", section="delta risk")
- chunk_read: Best for reading full context of a specific chunk

Strategy:
1. For simple definition queries, one semantic_search is usually enough
2. For comparison queries, use semantic_search then chunk_read on top results
3. For numeric/formula queries, use keyword_search first
4. Stop searching when you have enough evidence to answer confidently
5. Always cite sources in your answer

Answer in the same language as the question. Be concise and cite chunk_ids."""


def _build_llm() -> Any:
    """构建用于 Agentic RAG 的 ChatOpenAI 实例.

    复用 settings 中的 LLM 配置, temperature=0 保证输出稳定.
    """
    from langchain_openai import ChatOpenAI

    api_key = settings.llm.resolved_api_key.get_secret_value()
    # OpenRouter 等兼容服务可能需要额外 header
    headers: dict[str, str] = {}
    referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
    title = os.getenv("OPENROUTER_APP_NAME", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title

    timeout_total = int(settings.llm_governance.timeout_total)
    return ChatOpenAI(
        model=settings.llm.model,
        api_key=api_key,
        base_url=settings.llm.base_url,
        temperature=0.0,
        timeout=float(timeout_total),
        default_headers=headers or None,
    )


def _execute_tool(tool_call: dict[str, Any], tools: list[Any]) -> Any:
    """执行单个 tool_call, 返回工具结果.

    Args:
        tool_call: LLM 返回的 tool call, 包含 name/args/id
        tools: 可用工具列表

    Returns:
        工具执行结果 (list 或 dict)

    Raises:
        ValueError: 工具名未知时抛出
    """
    tool_name = str(tool_call.get("name", "")).strip()
    tool_args = tool_call.get("args") or {}
    for t in tools:
        if t.name == tool_name:
            return t.invoke(tool_args)
    raise ValueError(f"Unknown tool: {tool_name}")


def _result_to_docs(result: Any) -> list[Document]:
    """把工具结果转回 Document 列表, 用于后续 citations 和 evidence_set 构建."""
    if not isinstance(result, list):
        return []
    docs: list[Document] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "") or "")
        meta: dict[str, Any] = {
            "chunk_id": str(item.get("chunk_id", "")),
            "source": str(item.get("source", "")),
        }
        if item.get("section_path"):
            meta["section_path"] = str(item.get("section_path"))
        if item.get("parent_id"):
            meta["parent_id"] = str(item.get("parent_id"))
        if item.get("context_brief"):
            meta["context_brief"] = str(item.get("context_brief"))
        if item.get("score") is not None:
            try:
                meta["agentic_score"] = float(item.get("score"))
            except (TypeError, ValueError):
                pass
        docs.append(Document(page_content=text, metadata=meta))
    return docs


def _extract_token_usage(response: Any) -> dict[str, int]:
    """从 LLM response 中提取 token usage."""
    usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
    resp_meta = getattr(response, "response_metadata", None) or {}
    token_usage = resp_meta.get("token_usage") or resp_meta.get("usage", {})
    if token_usage:
        usage["prompt_tokens"] = int(token_usage.get("prompt_tokens", 0))
        usage["completion_tokens"] = int(token_usage.get("completion_tokens", 0))
    return usage


def run_agentic_rag(*, question: str, retriever: Any, max_tool_calls: int = 5) -> dict[str, Any]:
    """运行 Agentic RAG, 模型自主决定检索策略.

    Args:
        question: 用户问题
        retriever: 已构建的检索器实例 (AdvancedIndexRetriever)
        max_tool_calls: 最大工具调用次数

    Returns:
        与 run_langgraph_agentic_chat 相同的输出 schema:
        request_id / answer / docs / citations / claims / evidence_set /
        decision_log / status / failure_reason / debug / total_token_usage
    """
    request_id = f"agentic-{uuid.uuid4().hex[:12]}"

    # 注入 retriever 到 contextvar, 供工具函数访问
    set_retriever_context(retriever)

    # 构建 LLM 并绑定工具
    llm = _build_llm()
    tools = [semantic_search, keyword_search, structured_lookup, chunk_read]
    llm_with_tools = llm.bind_tools(tools)

    messages: list[Any] = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": str(question or "")},
    ]

    collected_docs: list[Document] = []
    decision_log: list[dict[str, Any]] = []
    tool_calls_made = 0
    total_token_usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
    final_answer = ""
    failure_reason: dict[str, Any] | None = None

    # Agent loop: 模型自主决定调用工具, 最多 max_tool_calls 次
    for step in range(max_tool_calls):
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as exc:
            logger.exception("Agentic RAG LLM invoke failed at step %s", step)
            failure_reason = {
                "stage": "agent_loop",
                "step": step,
                "error": str(exc),
            }
            break

        messages.append(response)
        total_token_usage["prompt_tokens"] += _extract_token_usage(response)["prompt_tokens"]
        total_token_usage["completion_tokens"] += _extract_token_usage(response)["completion_tokens"]

        # 模型决定停止检索, 当前 response 即为最终答案
        if not response.tool_calls:
            final_answer = str(getattr(response, "content", "") or "")
            decision_log.append({
                "step": step,
                "action": "stop",
                "reason": "model decided no more retrieval needed",
            })
            break

        # 执行模型请求的工具调用
        for tc in response.tool_calls:
            if tool_calls_made >= max_tool_calls:
                break
            tool_name = str(tc.get("name", ""))
            tool_args = tc.get("args") or {}
            try:
                result = _execute_tool(tc, tools)
                # 收集检索到的文档
                collected_docs.extend(_result_to_docs(result))
                decision_log.append({
                    "step": step,
                    "action": "tool_call",
                    "tool": tool_name,
                    "args": tool_args,
                    "status": "ok",
                })
            except Exception as exc:
                # 单个工具失败不阻塞整个 agent
                logger.warning("Tool %s failed: %s", tool_name, exc)
                result = {"error": f"{type(exc).__name__}: {exc}"}
                decision_log.append({
                    "step": step,
                    "action": "tool_call",
                    "tool": tool_name,
                    "args": tool_args,
                    "status": "error",
                    "error": str(exc),
                })

            # 把工具结果返回给 LLM
            messages.append({
                "role": "tool",
                "content": str(result),
                "tool_call_id": str(tc.get("id", "")),
            })
            tool_calls_made += 1

        # 如果已达到工具调用上限, 跳出循环
        if tool_calls_made >= max_tool_calls:
            decision_log.append({
                "step": step,
                "action": "budget_exhausted",
                "reason": f"reached max_tool_calls={max_tool_calls}",
            })
            break

    # 如果循环结束时还没有最终答案 (达到上限或异常), 再 invoke 一次生成答案
    if not final_answer:
        try:
            final_response = llm.invoke(messages)
            final_answer = str(getattr(final_response, "content", "") or "")
            total_token_usage["prompt_tokens"] += _extract_token_usage(final_response)["prompt_tokens"]
            total_token_usage["completion_tokens"] += _extract_token_usage(final_response)["completion_tokens"]
        except Exception as exc:
            logger.exception("Agentic RAG final answer generation failed")
            final_answer = ""
            if failure_reason is None:
                failure_reason = {
                    "stage": "final_answer",
                    "error": str(exc),
                }

    # 对收集到的 docs 去重 (按 chunk_id)
    seen_chunk_ids: set[str] = set()
    deduped_docs: list[Document] = []
    for d in collected_docs:
        cid = str((d.metadata or {}).get("chunk_id", "")).strip()
        if cid and cid in seen_chunk_ids:
            continue
        if cid:
            seen_chunk_ids.add(cid)
        deduped_docs.append(d)

    # 构建 citations 和 evidence_set, 复用现有 pipeline
    citations = extract_citations(deduped_docs)
    evidence_set = build_evidence_set_from_docs(deduped_docs, include_text=False)
    claims = build_claims_from_answer(final_answer, evidence_set=evidence_set)

    status = "ok" if final_answer else "error"

    return {
        "request_id": request_id,
        "answer": final_answer,
        "docs": deduped_docs,
        "citations": citations,
        "claims": claims,
        "evidence_set": evidence_set,
        "decision_log": decision_log,
        "status": status,
        "failure_reason": failure_reason,
        "debug": {
            "runner": "agentic",
            "tool_calls": tool_calls_made,
            "max_tool_calls": max_tool_calls,
            "collected_docs": len(deduped_docs),
        },
        "total_token_usage": total_token_usage,
    }

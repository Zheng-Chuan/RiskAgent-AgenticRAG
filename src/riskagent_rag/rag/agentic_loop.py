"""Agentic loop.

中文注释 单 agent 的 agentic RAG loop
- rewrite 将用户问题改写为更适合检索的 query
- critique 判断当前 retrieval 是否足够 不足则给出改进 query
- re-retrieve 最多重试 max_rounds
- final answer 用 LLM 基于 docs 输出最终回答

注意 citations 必须来自 retriever 返回 docs 的 metadata 不能依赖模型自造
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from langchain_core.documents import Document  # type: ignore[import-not-found]

from riskagent_rag.agents.data_agent import run_data_agent
from riskagent_rag.artifacts.storage import save_artifact
from riskagent_rag.contracts.structured import StructuredRequest
from riskagent_rag.rag import agentic_primitives
from riskagent_rag.rag.pipeline import extract_citations
from riskagent_rag.validators.gates import validate_response


def _try_parse_json(text: str) -> Optional[dict[str, Any]]:
    # 中文注释: LLM 输出不一定严格 JSON, 这里做最小容错.
    return agentic_primitives.try_parse_json(text)


def _call_ollama(prompt: str) -> str:
    # 中文注释: 复用 generate.py 内部的 Ollama 调用.
    # 注意: 这是开发期快速接入, 后续可以抽象为公开的 LLM client.
    return agentic_primitives.call_ollama_json(prompt)


def _utc_today_date() -> str:
    # 中文注释 tool use 的默认 as_of
    return agentic_primitives.utc_today_date()


def _rewrite_query(question: str) -> str:
    return agentic_primitives.rewrite_query(question)


def _critique_retrieval(question: str, docs: list[Document]) -> tuple[bool, str, str]:
    return agentic_primitives.critique_retrieval(question, docs)


def _decide_tool_use(question: str) -> tuple[bool, dict[str, Any], str]:
    # 中文注释: 在 Ollama 模式下, 让 LLM 输出结构化 JSON 决策是否需要调用 tool.
    return agentic_primitives.decide_tool_use(question)


def _synthesize_answer_with_tool(
    *,
    question: str,
    docs: list[Document],
    tool_output: dict[str, Any] | None,
) -> str:
    return agentic_primitives.synthesize_answer_with_tool(
        question=question,
        docs=docs,
        tool_output=tool_output,
    )


def _attach_citations_to_each_paragraph(answer: str, citations: list[dict[str, str]]) -> str:
    return agentic_primitives.attach_citations_to_each_paragraph(answer, citations)


def run_agentic_chat(
    *,
    question: str,
    retriever: Any,
    max_rounds: int = 2,
) -> dict[str, Any]:
    # 中文注释: 返回结构与现有 gradio_app.py 兼容.
    decision_log: list[dict[str, Any]] = []
    tool_traces: list[dict[str, Any]] = []
    tool_output: dict[str, Any] | None = None

    rewritten = _rewrite_query(question)
    decision_log.append(
        {
            "step_id": "rewrite",
            "agent": "AgenticLoop",
            "rationale": "rewrite user question for retrieval",
            "chosen": rewritten,
            "alternatives": [question],
        }
    )

    current_query = rewritten
    docs: list[Document] = []
    critique_reason = ""

    for round_idx in range(max_rounds):
        docs = retriever.invoke(current_query)

        sufficient, improved_query, reason = _critique_retrieval(question, docs)
        critique_reason = reason
        decision_log.append(
            {
                "step_id": f"critique_round_{round_idx + 1}",
                "agent": "AgenticLoop",
                "rationale": reason or "critique retrieval",
                "chosen": "sufficient" if sufficient else "insufficient",
                "alternatives": [current_query],
            }
        )

        if sufficient:
            break

        if improved_query:
            current_query = improved_query
        else:
            current_query = question

        decision_log.append(
            {
                "step_id": f"rewrite_round_{round_idx + 1}",
                "agent": "AgenticLoop",
                "rationale": "revise query based on critique",
                "chosen": current_query,
                "alternatives": [rewritten],
            }
        )

    should_call_tool, tool_args, tool_reason = _decide_tool_use(question)
    decision_log.append(
        {
            "step_id": "tool_decision",
            "agent": "AgenticLoop",
            "rationale": tool_reason or "decide tool use",
            "chosen": "call" if should_call_tool else "skip",
            "alternatives": [json.dumps(tool_args, ensure_ascii=False)],
        }
    )

    if should_call_tool:
        desk = str(tool_args.get("desk", "")).strip()
        as_of = str(tool_args.get("as_of", "")).strip() or _utc_today_date()
        abs_delta_limit_raw = tool_args.get("abs_delta_limit", 1000000)
        try:
            abs_delta_limit = float(abs_delta_limit_raw)
        except Exception:
            abs_delta_limit = 1000000.0

        if desk:
            request = StructuredRequest(
                request_id=str(uuid.uuid4()),
                query=question,
                as_of=as_of,
                desk=desk,
                abs_delta_limit=abs_delta_limit,
            )
            tool_output, trace, _failure = run_data_agent(request)
            if hasattr(trace, "model_dump"):
                tool_traces.append(trace.model_dump())  # type: ignore[attr-defined]
            else:
                tool_traces.append(trace.dict())
        else:
            decision_log.append(
                {
                    "step_id": "tool_skip_missing_desk",
                    "agent": "AgenticLoop",
                    "rationale": "tool args missing desk",
                    "chosen": "skip",
                    "alternatives": [json.dumps(tool_args, ensure_ascii=False)],
                }
            )

    answer = _synthesize_answer_with_tool(question=question, docs=docs, tool_output=tool_output)
    citations = extract_citations(docs)
    answer_with_citations = _attach_citations_to_each_paragraph(answer, citations)

    evidence_set = agentic_primitives.build_evidence_set_from_docs(docs, include_text=True)
    claims = agentic_primitives.build_claims_from_answer(
        answer_with_citations,
        evidence_set=evidence_set,
    )

    failure_reason = validate_response(
        report=answer_with_citations,
        claims=claims,
        evidence_set=evidence_set,
        tool_traces=tool_traces,
        docs=docs,
    )

    status = "ok" if failure_reason is None else "failed"

    request_id = str(uuid.uuid4())
    request_data = {
        "question": question,
        "max_rounds": max_rounds,
    }
    
    debug_info: dict[str, Any] = {
        "final_query": current_query,
        "critique_reason": critique_reason,
        "tool_args": tool_args,
        "tool_should_call": should_call_tool,
    }
    
    response_data: dict[str, Any] = {
        "answer": answer_with_citations,
        "citations": citations,
        "claims": claims,
        "evidence_set": evidence_set,
        "decision_log": decision_log,
        "tool_traces": tool_traces,
        "status": status,
        "failure_reason": failure_reason,
        "debug": debug_info,
    }

    breaches: list[dict[str, Any]] = []
    if isinstance(tool_output, dict):
        raw_breaches = tool_output.get("breaches")
        if isinstance(raw_breaches, list):
            breaches = raw_breaches

    structured_evidence_set = agentic_primitives.build_evidence_set_from_docs(docs, include_text=False)

    structured_payload: dict[str, Any] = {
        "request_id": request_id,
        "report": answer_with_citations,
        "breaches": breaches,
        "evidence_set": structured_evidence_set,
        "claims": claims,
        "tool_traces": tool_traces,
        "decision_log": decision_log,
        "status": status,
        "failure_reason": failure_reason,
    }

    try:
        artifact_path = save_artifact(
            request_id,
            request_data,
            response_data,
            structured_response_data=structured_payload,
        )
        debug_info["artifact_path"] = artifact_path
    except Exception as e:
        debug_info["artifact_error"] = str(e)

    return {
        "answer": answer_with_citations,
        "docs": docs,
        "citations": citations,
        "claims": claims,
        "evidence_set": structured_evidence_set,
        "decision_log": decision_log,
        "tool_traces": tool_traces,
        "status": status,
        "failure_reason": failure_reason,
        "debug": response_data["debug"],
    }

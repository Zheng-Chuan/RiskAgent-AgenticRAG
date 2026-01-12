"""Week3 agentic loop.

中文注释: 单 agent 的 agentic RAG loop.
- rewrite: 将用户问题改写为更适合检索的 query
- critique: 判断当前 retrieval 是否足够, 不足则给出改进 query
- re-retrieve: 最多重试 max_rounds
- final answer: 用 LLM 基于 docs 输出最终回答

注意: citations 必须来自 retriever 返回 docs 的 metadata, 不能依赖模型自造.
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from typing import Any, Optional

from langchain_core.documents import Document  # type: ignore[import-not-found]

from riskagent_rag.agents.data_agent import run_data_agent
from riskagent_rag.contracts.week3 import Week3Request
from riskagent_rag.llm.generate import generate_answer
from riskagent_rag.rag.pipeline import extract_citations


def _try_parse_json(text: str) -> Optional[dict[str, Any]]:
    # 中文注释: LLM 输出不一定严格 JSON, 这里做最小容错.
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        snippet = raw[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            return None
    return None


def _call_ollama(prompt: str) -> str:
    # 中文注释: 复用 generate.py 内部的 Ollama 调用.
    # 注意: 这是开发期快速接入, 后续可以抽象为公开的 LLM client.
    from riskagent_rag.llm import generate as llm_generate

    return llm_generate._call_ollama_generate(
        prompt,
        response_format="json",
        options={
            # 中文注释: 尽量降低随机性, 让 rewrite 和 critique 稳定输出.
            "temperature": 0,
        },
    )  # type: ignore[attr-defined]


def _utc_today_date() -> str:
    # 中文注释: Week3 tool use 的默认 as_of.
    return datetime.datetime.utcnow().date().isoformat()


def _rewrite_query(question: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider != "ollama":
        return question

    prompt = (
        "You are a retrieval query rewriting assistant for finance risk and derivatives. "
        "Rewrite the user question into a short, keyword-rich search query optimized for embedding search. "
        "Do not answer the question. Do not include citations. "
        "Return JSON only.\n"
        "Schema: {\"query\": \"...\"}\n\n"
        "Rules:\n"
        "- Prefer noun phrases and domain terms (FRTB, delta, desk exposure, limit breach).\n"
        "- Keep it under 20 tokens if possible.\n\n"
        f"User question: {question}\n"
    )
    text = _call_ollama(prompt)
    data = _try_parse_json(text)
    if not data:
        return question

    query = str(data.get("query", "")).strip()
    return query or question


def _critique_retrieval(question: str, docs: list[Document]) -> tuple[bool, str, str]:
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider != "ollama":
        # 中文注释: 非 ollama 场景先不做 critique, 直接认为 sufficient.
        return True, "", "critique skipped: non-ollama provider"

    if not docs:
        return False, question, "retrieval returned empty docs"

    context = "\n\n".join([(d.page_content or "")[:500] for d in docs[:4]])
    prompt = (
        "You are a strict RAG retrieval critic. "
        "Given the question and retrieved context, decide if the context is sufficient. "
        "If insufficient, propose an improved search query. "
        "Return JSON only.\n"
        "Schema: {\"sufficient\": true|false, \"improved_query\": \"...\", \"reason\": \"...\"}\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}\n"
    )
    text = _call_ollama(prompt)
    data = _try_parse_json(text) or {}

    sufficient = bool(data.get("sufficient", False))
    improved_query = str(data.get("improved_query", "")).strip()
    reason = str(data.get("reason", "")).strip()
    return sufficient, improved_query, reason


def _decide_tool_use(question: str) -> tuple[bool, dict[str, Any], str]:
    # 中文注释: 在 Ollama 模式下, 让 LLM 输出结构化 JSON 决策是否需要调用 tool.
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider != "ollama":
        return False, {}, "tool decision skipped: non-ollama provider"

    prompt = (
        "You are a strict tool-use planner for a risk monitoring assistant. "
        "Decide whether to call the desk exposure monitoring tool. "
        "Only call the tool when the user asks about desk exposure, delta limit, breach, or intraday monitoring. "
        "Return JSON only.\n"
        "Schema: {\"should_call_tool\": true|false, \"args\": {\"desk\": \"...\", \"as_of\": \"YYYY-MM-DD\", \"abs_delta_limit\": 1000000}, \"reason\": \"...\"}\n\n"
        "Rules:\n"
        "- desk is required when should_call_tool is true\n"
        "- as_of defaults to today's UTC date if missing\n"
        "- abs_delta_limit defaults to 1000000 if missing\n\n"
        f"User question: {question}\n"
    )
    text = _call_ollama(prompt)
    data = _try_parse_json(text) or {}

    should_call = bool(data.get("should_call_tool", False))
    raw_args = data.get("args")
    args: dict[str, Any] = {}
    if isinstance(raw_args, dict):
        for k, v in raw_args.items():
            args[str(k)] = v
    reason = str(data.get("reason", "")).strip()
    return should_call, args, reason


def _synthesize_answer_with_tool(
    *,
    question: str,
    docs: list[Document],
    tool_output: dict[str, Any] | None,
) -> str:
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider != "ollama" or not tool_output:
        return generate_answer(question, docs)

    from riskagent_rag.llm import generate as llm_generate

    context = llm_generate._format_context(docs)
    tool_json = json.dumps(tool_output, ensure_ascii=False, indent=2)
    prompt = (
        "You are a helpful risk monitoring assistant for software engineers. "
        "Answer using only the provided retrieval context and the tool output. "
        "If information is insufficient, say you do not know and propose next actions. "
        "Do not invent numbers.\n\n"
        f"Question: {question}\n\n"
        f"Retrieval context:\n{context}\n\n"
        f"Tool output JSON:\n{tool_json}\n"
    )
    return llm_generate._call_ollama_generate(
        prompt,
        options={
            # 中文注释: 最终回答也尽量稳定, 便于回归.
            "temperature": 0,
        },
    )


def _attach_citations_to_each_paragraph(answer: str, citations: list[dict[str, str]]) -> str:
    # 中文注释: Week3 B 口径, 每段关键结论必须可回指 citations.
    # 这里先用最小实现: 给每个段落追加同一组 citations.
    if not answer.strip():
        return answer

    if not citations:
        return answer

    citations_md = " ".join(
        [
            f"[source={c.get('source','')} chunk_id={c.get('chunk_id','')}]"
            for c in citations
        ]
    )

    paragraphs = [p.strip() for p in answer.split("\n\n") if p.strip()]
    augmented: list[str] = []
    for p in paragraphs:
        augmented.append(f"{p}\n\nCitations: {citations_md}")
    return "\n\n".join(augmented)


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
            request = Week3Request(
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

    return {
        "answer": answer_with_citations,
        "docs": docs,
        "citations": citations,
        "decision_log": decision_log,
        "tool_traces": tool_traces,
        "debug": {
            "final_query": current_query,
            "critique_reason": critique_reason,
            "tool_args": tool_args,
            "tool_should_call": should_call_tool,
        },
    }

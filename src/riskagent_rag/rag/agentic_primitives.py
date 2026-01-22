"""Agentic loop primitives.

中文注释: 这个模块承载 agentic loop 与 LangGraph runner 共享的纯函数逻辑.
设计目标
- 复用核心步骤实现, 避免跨模块 import 私有函数
- 保持行为确定, 便于测试与回归
"""

from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any, Optional

from langchain_core.documents import Document  # type: ignore[import-not-found]

from riskagent_rag.llm.generate import generate_answer


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for ch in (text or "").lower():
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))

    stop = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "with",
        "is",
        "are",
        "was",
        "were",
        "what",
        "why",
        "how",
        "when",
        "where",
        "who",
        "explain",
        "define",
        "give",
        "list",
    }
    filtered = [t for t in tokens if len(t) >= 3 and t not in stop]
    return filtered


def heuristic_retrieval_sufficient(question: str, docs: list[Document]) -> tuple[bool, float]:
    q_tokens = set(_tokenize(question))
    if not q_tokens:
        return True, 1.0
    if not docs:
        return False, 0.0

    best = 0.0
    for d in docs[:4]:
        content = getattr(d, "page_content", "") or ""
        d_tokens = set(_tokenize(content[:2000]))
        if not d_tokens:
            continue
        overlap = len(q_tokens.intersection(d_tokens)) / max(1, len(q_tokens))
        if overlap > best:
            best = overlap

    return best >= 0.2, best


def build_refusal_report(question: str) -> str:
    q = (question or "").strip()
    return (
        "Could not find evidence in corpus.\n\n"
        f"Question: {q}\n\n"
        "Next actions:\n"
        "- Add relevant documents into corpus and rebuild index\n"
        "- Rephrase the question with finance risk and derivatives keywords\n"
        "- If you can share the exact source or document, I can cite and explain it\n"
    )


def try_parse_json(text: str) -> Optional[dict[str, Any]]:
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


def call_ollama_json(prompt: str) -> str:
    # 中文注释: 复用 generate.py 内部的 Ollama 调用.
    # 注意: 这是开发期快速接入, 后续可以抽象为公开的 LLM client.
    from riskagent_rag.llm import generate as llm_generate

    return llm_generate._call_ollama_generate(  # type: ignore[attr-defined]
        prompt,
        response_format="json",
        options={
            # 中文注释: 尽量降低随机性, 让 rewrite 和 critique 稳定输出.
            "temperature": 0,
        },
    )


def utc_today_date() -> str:
    # 中文注释: tool use 的默认 as_of
    return datetime.datetime.utcnow().date().isoformat()


def rewrite_query(question: str) -> str:
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
    text = call_ollama_json(prompt)
    data = try_parse_json(text)
    if not data:
        return question

    query = str(data.get("query", "")).strip()
    return query or question


def critique_retrieval(question: str, docs: list[Document]) -> tuple[bool, str, str]:
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider != "ollama":
        sufficient, score = heuristic_retrieval_sufficient(question, docs)
        if sufficient:
            return True, "", f"heuristic critique ok overlap={score:.3f}"
        return False, question, f"heuristic critique insufficient overlap={score:.3f}"

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
    text = call_ollama_json(prompt)
    data = try_parse_json(text) or {}

    sufficient = bool(data.get("sufficient", False))
    improved_query = str(data.get("improved_query", "")).strip()
    reason = str(data.get("reason", "")).strip()
    return sufficient, improved_query, reason


def decide_tool_use(question: str) -> tuple[bool, dict[str, Any], str]:
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
    text = call_ollama_json(prompt)
    data = try_parse_json(text) or {}

    should_call = bool(data.get("should_call_tool", False))
    raw_args = data.get("args")
    args: dict[str, Any] = {}
    if isinstance(raw_args, dict):
        for k, v in raw_args.items():
            args[str(k)] = v
    reason = str(data.get("reason", "")).strip()
    return should_call, args, reason


def synthesize_answer_with_tool(
    *,
    question: str,
    docs: list[Document],
    tool_output: dict[str, Any] | None,
) -> str:
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider != "ollama" or not tool_output:
        return generate_answer(question, docs)

    from riskagent_rag.llm import generate as llm_generate

    context = llm_generate._format_context(docs)  # type: ignore[attr-defined]
    tool_json = json.dumps(tool_output, ensure_ascii=False, indent=2)
    template = (
        "Use the following markdown structure:\n"
        "1) TLDR (2-4 bullets)\n"
        "2) Concept\n"
        "3) Why it matters\n"
        "4) Data flow / fields\n"
        "5) Example\n"
        "6) Citations (do not fabricate; citations will be attached separately)\n"
    )
    compliance = (
        "Compliance:\n"
        "- Do not output secrets, credentials, or personal data.\n"
        "- Do not provide trading or investment advice.\n"
        "- If information is insufficient, say you do not know and propose next actions.\n"
        "- Do not invent numbers.\n"
    )
    prompt = (
        "You are a helpful risk monitoring assistant for software engineers. "
        "Answer using only the provided retrieval context and the tool output. "
        "If information is insufficient, say you do not know and propose next actions.\n\n"
        f"{compliance}\n{template}\n"
        f"Question: {question}\n\n"
        f"Retrieval context:\n{context}\n\n"
        f"Tool output JSON:\n{tool_json}\n"
    )
    return llm_generate._call_ollama_generate(  # type: ignore[attr-defined]
        prompt,
        options={
            # 中文注释: 最终回答也尽量稳定, 便于回归.
            "temperature": 0,
        },
    )


def attach_citations_to_each_paragraph(answer: str, citations: list[dict[str, str]]) -> str:
    # 中文注释: 每段关键结论必须可回指 citations
    # 这里先用最小实现, 给每个段落追加同一组 citations
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


def build_evidence_set_from_docs(
    docs: list[Document],
    *,
    include_text: bool,
) -> list[dict[str, Any]]:
    # 中文注释: 从 docs 构建 evidence_set, 用于 validator gate.
    evidence_set: list[dict[str, Any]] = []
    for idx, doc in enumerate(docs):
        evidence_id = f"ev_{idx}"
        start_index_raw = doc.metadata.get("start_index", 0)
        try:
            start_index = int(start_index_raw)
        except Exception:
            start_index = 0

        item: dict[str, Any] = {
            "evidence_id": evidence_id,
            "source": str(doc.metadata.get("source", "")),
            "chunk_id": str(doc.metadata.get("chunk_id", "")),
            "start_index": start_index,
            "snippet": (doc.page_content or "")[:200],
        }
        if doc.metadata.get("section_path"):
            item["section_path"] = str(doc.metadata.get("section_path"))
        if doc.metadata.get("start_line") is not None:
            try:
                item["start_line"] = int(doc.metadata.get("start_line"))
            except Exception:
                pass
        if doc.metadata.get("end_line") is not None:
            try:
                item["end_line"] = int(doc.metadata.get("end_line"))
            except Exception:
                pass
        if doc.metadata.get("page") is not None:
            try:
                item["page"] = int(doc.metadata.get("page"))
            except Exception:
                pass
        if include_text:
            item["text"] = (doc.page_content or "")[:200]
        evidence_set.append(item)
    return evidence_set


def build_claims_from_answer(
    answer: str,
    *,
    evidence_set: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    # 中文注释: MVP 阶段用确定性规则把 answer 切成 claims.
    # 设计目标: claims 必须携带 evidence_ids, 让 evidence_gate 可执行.
    evidence_by_chunk_id: dict[str, str] = {}
    evidence_ids: list[str] = []
    evidence_texts: dict[str, str] = {}
    for e in evidence_set:
        if not isinstance(e, dict):
            continue
        eid = str(e.get("evidence_id") or "").strip()
        if not eid:
            continue
        evidence_ids.append(eid)
        chunk_id = str(e.get("chunk_id") or "").strip()
        if chunk_id:
            evidence_by_chunk_id[chunk_id] = eid
        evidence_texts[eid] = str(e.get("snippet") or e.get("text") or "")
    if not evidence_ids:
        return []

    citations_re = re.compile(r"chunk_id=([^\]\s]+)")
    paragraphs = [p.strip() for p in (answer or "").split("\n\n") if p.strip()]
    claims: list[dict[str, Any]] = []
    for idx, p in enumerate(paragraphs):
        lines = [ln.strip() for ln in p.splitlines()]
        kept = [ln for ln in lines if ln and not ln.lower().startswith("citations:")]
        statement = "\n".join(kept).strip()
        if not statement:
            continue

        matched_eids: list[str] = []
        for m in citations_re.finditer(p):
            cid = m.group(1).strip()
            eid = evidence_by_chunk_id.get(cid)
            if eid and eid not in matched_eids:
                matched_eids.append(eid)

        if not matched_eids:
            stoks = set(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", statement.lower()))
            best_eid = evidence_ids[0]
            best_score = -1
            for eid in evidence_ids:
                et = evidence_texts.get(eid, "").lower()
                etoks = set(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", et))
                score = len(stoks & etoks)
                if score > best_score:
                    best_score = score
                    best_eid = eid
            matched_eids = [best_eid]

        claims.append({"claim_id": f"cl_{idx}", "statement": statement[:300], "evidence_ids": matched_eids})
    return claims

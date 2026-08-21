"""Agentic loop primitives.

中文注释: 这个模块承载 agentic loop 与 LangGraph runner 共享的纯函数逻辑.
设计目标
- 复用核心步骤实现, 避免跨模块 import 私有函数
- 保持行为确定, 便于测试与回归
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.documents import Document

from riskagent_agenticrag.llm.generate import call_llm_json, call_llm_text, generate_answer
from riskagent_agenticrag.rag.utils import tokenize as _raw_tokenize

_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
    "is", "are", "was", "were", "what", "why", "how", "when", "where", "who",
    "explain", "define", "give", "list",
})


def _tokenize(text: str) -> list[str]:
    """分词并过滤停用词, 用于 query-doc token 重叠计算."""
    return [t for t in _raw_tokenize(text) if len(t) >= 3 and t not in _STOP_WORDS]


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
    from riskagent_agenticrag.llm import generate as llm_generate

    prompt = (
        "You are a strict RAG assistant. There is no usable retrieval context. "
        "You must refuse to answer and propose next actions. "
        "Return plain markdown only.\n\n"
        f"Question: {q}\n\n"
        "Constraints:\n"
        "- Do not answer the question.\n"
        "- Mention that no evidence was found in the indexed corpus.\n"
        "- Provide 3-5 concrete next actions.\n"
    )
    return llm_generate.call_llm_text(prompt, temperature=0.0)


def try_parse_json(text: str) -> dict[str, Any] | None:
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


def rewrite_query(question: str) -> str:
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
    try:
        data = call_llm_json(prompt, temperature=0.0)
    except Exception:
        return question
    query = str(data.get("query", "")).strip()
    return query or question


def revise_query(question: str, previous_query: str) -> str:
    """基于上一轮查询改写新查询, 用于 CRAG insufficient 档位降级.

    与 rewrite_query 不同, revise_query 额外参考 previous_query,
    让 LLM 针对上一轮检索不足的部分做针对性改写 (换同义词或调整宽窄).
    LLM 调用失败时回退为 previous_query, 保证主流程不中断.
    """
    prev = str(previous_query or "").strip() or str(question or "").strip()
    prompt = (
        "You are a retrieval query revising assistant for finance risk and derivatives. "
        "The previous search query did not retrieve sufficient evidence. "
        "Revise it into a better keyword-rich search query optimized for embedding search. "
        "Do not answer the question. Do not include citations. "
        "Return JSON only.\n"
        "Schema: {\"query\": \"...\"}\n\n"
        "Rules:\n"
        "- Prefer noun phrases and domain terms (FRTB, delta, desk exposure, limit breach).\n"
        "- Keep it under 20 tokens if possible.\n"
        "- Avoid simply repeating the previous query; try synonyms or broader/narrower terms.\n\n"
        f"Original question: {question}\n"
        f"Previous query: {prev}\n"
    )
    try:
        data = call_llm_json(prompt, temperature=0.0)
    except Exception:
        return prev
    query = str(data.get("query", "")).strip()
    return query or prev


def critique_retrieval(question: str, docs: list[Document]) -> tuple[bool, str, str]:
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
    try:
        data = call_llm_json(prompt, temperature=0.0)
        sufficient = bool(data.get("sufficient", False))
        improved_query = str(data.get("improved_query", "")).strip()
        reason = str(data.get("reason", "")).strip()
        return sufficient, improved_query, reason
    except Exception:
        sufficient, score = heuristic_retrieval_sufficient(question, docs)
        if sufficient:
            return True, "", f"json_parse_fallback_heuristic_sufficient overlap={score:.3f}"
        return False, question, f"json_parse_fallback_heuristic_insufficient overlap={score:.3f}"


def synthesize_answer(*, question: str, docs: list[Document]) -> str:
    if not docs:
        return build_refusal_report(question)
    if not any(
        (str(getattr(d, "page_content", "") or "").strip() or str((getattr(d, "metadata", {}) or {}).get("expanded_text") or "").strip())
        for d in docs
    ):
        return build_refusal_report(question)
    return generate_answer(question, docs)


def synthesize_answer_from_model_knowledge(question: str) -> str:
    """无检索上下文时, 使用 LLM 自身知识直接回答 (TARG simple 查询直答路径).

    与 synthesize_answer 不同: 后者在 docs 为空时会生成拒答报告,
    而本函数允许 LLM 用自身知识回答, 适用于 TARG 判定为 simple 的查询.
    """
    q = str(question or "").strip()
    prompt = (
        "You are a precise assistant explaining financial derivatives and risk concepts. "
        "Answer the question using your own knowledge. "
        "Keep the answer concise and factual. Return plain markdown only.\n\n"
        f"Question: {q}\n"
    )
    return call_llm_text(prompt, temperature=0.0)


def _paragraph_tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", text.lower()))


def attach_citations_to_each_paragraph(answer: str, citations: list[dict[str, str]]) -> str:
    # 按段落匹配最相关的 citations, 而非全局附加
    if not answer.strip():
        return answer
    if not citations:
        return answer

    # 预计算每个 citation 的 token 集合
    cite_tokens: list[tuple[dict[str, str], set[str]]] = []
    for c in citations:
        snippet = str(c.get("snippet") or c.get("text") or c.get("source") or "")
        cite_tokens.append((c, _paragraph_tokens(snippet)))

    paragraphs = [p.strip() for p in answer.split("\n\n") if p.strip()]
    augmented: list[str] = []

    for p in paragraphs:
        p_tokens = _paragraph_tokens(p)
        if not p_tokens:
            augmented.append(p)
            continue

        # 计算每个 citation 与段落的 overlap, 取 top-k
        scored: list[tuple[int, dict[str, str]]] = []
        for c, ct in cite_tokens:
            overlap = len(p_tokens & ct)
            if overlap >= 2:
                scored.append((overlap, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [c for _, c in scored[:3]]

        # 如果没有匹配, 不附加 citation
        if not top:
            augmented.append(p)
            continue

        citations_md = " ".join(
            f"[source={c.get('source','')} chunk_id={c.get('chunk_id','')}]"
            for c in top
        )
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

        snippet_text = str(doc.metadata.get("expanded_text") or doc.page_content or "")
        snippet_text = snippet_text.strip()

        item: dict[str, Any] = {
            "evidence_id": evidence_id,
            "source": str(doc.metadata.get("source", "")),
            "chunk_id": str(doc.metadata.get("chunk_id", "")),
            "start_index": start_index,
            "snippet": snippet_text[:600],
        }
        if doc.metadata.get("tool_name"):
            item["tool_name"] = str(doc.metadata.get("tool_name"))
        if doc.metadata.get("evidence_kind"):
            item["evidence_kind"] = str(doc.metadata.get("evidence_kind"))
        if doc.metadata.get("numeric_payload") is not None:
            item["numeric_payload"] = doc.metadata.get("numeric_payload")
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
            item["text"] = snippet_text[:1200]
        evidence_set.append(item)
    return evidence_set


def _extract_chunk_ids_from_text(text: str) -> list[str]:
    citations_re = re.compile(r"chunk_id=([^\]\s]+)")
    chunk_ids: list[str] = []
    for m in citations_re.finditer(str(text or "")):
        cid = m.group(1).strip()
        if cid and cid not in chunk_ids:
            chunk_ids.append(cid)
    return chunk_ids


def _split_claim_statements(block: str) -> list[str]:
    statements: list[str] = []
    for raw_line in str(block or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("citations:"):
            continue
        if re.fullmatch(r"\d+\)\s*.*", line):
            continue
        line = re.sub(r"^[-*]\s+", "", line).strip()
        if not line:
            continue
        statements.append(line[:300])
    if statements:
        return statements
    cleaned = str(block or "").strip()
    if cleaned:
        return [cleaned[:300]]
    return []


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

    paragraphs = [p.strip() for p in (answer or "").split("\n\n") if p.strip()]
    claims: list[dict[str, Any]] = []
    claim_idx = 0
    for idx, p in enumerate(paragraphs):
        if p.lower().startswith("citations:"):
            continue

        matched_eids: list[str] = []
        citation_texts = [p]
        if idx + 1 < len(paragraphs) and paragraphs[idx + 1].lower().startswith("citations:"):
            citation_texts.append(paragraphs[idx + 1])
        for citation_text in citation_texts:
            for cid in _extract_chunk_ids_from_text(citation_text):
                eid = evidence_by_chunk_id.get(cid)
                if eid and eid not in matched_eids:
                    matched_eids.append(eid)

        for statement in _split_claim_statements(p):
            local_eids = list(matched_eids)
            if not local_eids:
                stoks = set(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", statement.lower()))
                scored_eids: list[tuple[int, str]] = []
                for eid in evidence_ids:
                    et = evidence_texts.get(eid, "").lower()
                    etoks = set(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", et))
                    score = len(stoks & etoks)
                    if score > 0:
                        scored_eids.append((score, eid))
                scored_eids.sort(key=lambda item: item[0], reverse=True)
                local_eids = [eid for _, eid in scored_eids[:3]] or [evidence_ids[0]]

            claims.append(
                {
                    "claim_id": f"cl_{claim_idx}",
                    "statement": statement,
                    "evidence_ids": local_eids,
                }
            )
            claim_idx += 1
    return claims

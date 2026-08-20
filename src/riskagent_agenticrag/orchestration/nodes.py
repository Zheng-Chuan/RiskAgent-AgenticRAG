"""Agentic loop 节点 -- 每个函数对应 LangGraph 中的一个 node."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Literal

from riskagent_agenticrag.agents.data_agent import extract_structured_request, run_data_agent, tool_output_to_document
from riskagent_agenticrag.artifacts.storage import save_artifact
from riskagent_agenticrag.config.settings import settings
from riskagent_agenticrag.llm.generate import get_last_token_usage
from riskagent_agenticrag.observability.persistence import cleanup_traces, save_trace
from riskagent_agenticrag.orchestration.state import AgenticState
from riskagent_agenticrag.orchestration.trace import (
    _doc_trace_row,
    _ensure_trace,
    _trace_node_end,
    _trace_node_start,
    _trace_retrieval_diag,
)
from riskagent_agenticrag.rag import agentic_primitives
from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget
from riskagent_agenticrag.rag.pipeline import extract_citations
from riskagent_agenticrag.rag.query_router import assess_query_complexity
from riskagent_agenticrag.rag.self_rag import grade_docs_crag, grade_generation, should_require_numeric_backing
from riskagent_agenticrag.validators.gates import validate_response


def _extract_doc_score(doc: Any) -> tuple[float, str]:
    """从 Document metadata 提取相关性分数与来源标记.

    分数优先级 (RFC-001 FR-12): rerank_score > rrf_score > coarse_score > 0.0
    来源标记: rerank / hybrid / coarse / unknown (tool 产出或无分数时为 unknown)
    """
    meta = getattr(doc, "metadata", None) or {}
    try:
        if "rerank_score" in meta:
            return float(meta.get("rerank_score") or 0.0), "rerank"
        if "rrf_score" in meta:
            return float(meta.get("rrf_score") or 0.0), "hybrid"
        if "coarse_score" in meta:
            return float(meta.get("coarse_score") or 0.0), "coarse"
    except (TypeError, ValueError):
        pass
    return 0.0, "unknown"


def _seal_rag_capacity() -> int:
    """读取 SEAL-RAG 证据集容量配置, 异常时回退到默认 5."""
    try:
        return int(getattr(settings.features, "seal_rag_budget", 5) or 5)
    except Exception:  # noqa: BLE001
        return 5


def _infer_retriever_k(retriever: Any) -> int:
    """从 retriever 链路的 config 推断当前 top_k, 用于 CRAG expand_topk 翻倍基数.

    优先取最外层 config 的 final_k / k / dense_k, 找不到则递归 _base.
    推断失败回退到默认 8.
    """
    try:
        config = getattr(retriever, "_config", None)
        if config is not None:
            for attr in ("final_k", "k", "dense_k"):
                value = getattr(config, attr, None)
                if isinstance(value, int) and value > 0:
                    return int(value)
        base = getattr(retriever, "_base", None)
        if base is not None:
            return _infer_retriever_k(base)
    except Exception:  # noqa: BLE001
        pass
    return 8


# ---------------------------------------------------------------------------
# TARG 辅助: 跳过 query variants fanout 的单次 dense+sparse 检索
# ---------------------------------------------------------------------------

def _invoke_without_fanout(retriever: Any, query: str) -> list[Any]:
    """跳过 query variants fanout, 直接调用底层 dense+sparse 检索器.

    检索器包装链: AdvancedIndexRetriever -> QueryIntelligentRetriever -> HybridRetriever.
    fanout 发生在 QueryIntelligentRetriever 层 (生成多个 query 变体做 RRF 融合).
    这里下钻到 HybridRetriever 做单次 dense+sparse 检索, 减少 50%+ 的不必要检索调用.
    无法下钻时 (如测试 mock 检索器不可迭代) 兜底退回原检索器.
    """
    try:
        # AdvancedIndexRetriever._base = QueryIntelligentRetriever
        query_intel = getattr(retriever, "_base", None)
        # QueryIntelligentRetriever._base = HybridRetriever (dense + sparse)
        hybrid = getattr(query_intel, "_base", None)
        if hybrid is not None and hasattr(hybrid, "invoke"):
            return list(hybrid.invoke(query))
    except Exception:  # noqa: BLE001
        pass  # 下钻失败 (例如 mock 检索器不可迭代) 时退回原检索器
    return list(retriever.invoke(query))


# ---------------------------------------------------------------------------
# Node: rewrite
# ---------------------------------------------------------------------------

def node_rewrite(state: AgenticState) -> AgenticState:
    """Node: rewrite query for better retrieval (TARG 门控)."""
    start_ms = _trace_node_start(state, "rewrite", {"question": state.get("question", "")})
    question = state["question"]

    # TARG 门控 (FR-11): 评估查询复杂性, 决定 rewrite / retrieval / fanout 是否必要
    complexity = assess_query_complexity(question=question)
    state["query_complexity"] = {
        "level": complexity.level,
        "needs_retrieval": complexity.needs_retrieval,
        "needs_rewrite": complexity.needs_rewrite,
        "needs_fanout": complexity.needs_fanout,
        "confidence": complexity.confidence,
        "reason": complexity.reason,
    }
    # 中等/简单查询不需要 fanout, 标记供 retrieve 节点读取
    if not complexity.needs_fanout:
        state["skip_fanout"] = True

    if complexity.needs_rewrite:
        rewritten = agentic_primitives.rewrite_query(question)
        token_usage = get_last_token_usage()
        rationale = "rewrite user question for retrieval"
    else:
        # 简单查询跳过 rewrite, 直接用原始 question 作为 current_query
        rewritten = question
        token_usage = get_last_token_usage()
        rationale = f"targ_skip_rewrite:{complexity.reason}"

    state["current_query"] = rewritten
    state["improved_query"] = ""
    state["current_round"] = 0
    state["decision_log"] = state.get("decision_log", [])
    state["decision_log"].append({
        "step_id": "rewrite",
        "agent": "AgenticLoop",
        "rationale": rationale,
        "chosen": rewritten,
        "alternatives": [question],
    })

    _trace_node_end(state, "rewrite", start_ms, {"current_query": rewritten}, token_usage=token_usage)
    return state


# ---------------------------------------------------------------------------
# Node: retrieve_and_critique (含 Self-RAG 文档评分)
# ---------------------------------------------------------------------------

def node_retrieve_and_critique(state: AgenticState) -> AgenticState:
    """Node: retrieve docs and critique quality."""
    start_ms = _trace_node_start(
        state,
        "retrieve_and_critique",
        {
            "round": int(state.get("current_round", 0) + 1),
            "current_query": state.get("current_query", ""),
        },
    )
    retriever = state["retriever"]
    current_query = state["current_query"]
    question = state["question"]
    max_rounds = state["max_rounds"]
    current_round = state.get("current_round", 0)

    # TARG (FR-11): 中等查询不需要 fanout, 只做单次 dense+sparse 检索, 跳过 query variants 融合
    if bool(state.get("skip_fanout")):
        docs = _invoke_without_fanout(retriever, current_query)
    else:
        docs = retriever.invoke(current_query)

    # 检索诊断埋点: 从 retriever 的 debug_stats 提取诊断信息写入 trace
    try:
        if hasattr(retriever, "debug_stats"):
            debug_stats = retriever.debug_stats()
            if isinstance(debug_stats, dict):
                _trace_retrieval_diag(state, debug_stats)
                # 实际生效的 reranker 模型透传到 state, 供最终节点写 retriever_version
                # (环境变量名在远程 fallback 场景下与实际模型不符, 不能作为唯一来源)
                active_model = str(debug_stats.get("active_reranker_model") or "").strip()
                if active_model:
                    state["active_reranker_model"] = active_model
                if debug_stats.get("reranker_status"):
                    state["reranker_status"] = str(debug_stats.get("reranker_status"))
    except Exception:
        pass  # 检索诊断采集失败不影响主流程

    tool_traces = list(state.get("tool_traces") or [])
    tool_request = extract_structured_request(
        question=question,
        request_id=str(state.get("request_id") or state.get("run_id") or str(uuid.uuid4())),
    )
    if tool_request is not None:
        tool_output, tool_trace, tool_failure = run_data_agent(tool_request)
        tool_traces.append(tool_trace.model_dump() if hasattr(tool_trace, "model_dump") else tool_trace.dict())
        if tool_failure is None:
            docs = list(docs) + [tool_output_to_document(tool_output=tool_output, tool_trace=tool_trace)]
        debug = state.get("debug") or {}
        debug["numeric_tool"] = {
            "invoked": True,
            "request": tool_request.model_dump() if hasattr(tool_request, "model_dump") else tool_request.dict(),
            "failure": (
                tool_failure.model_dump() if hasattr(tool_failure, "model_dump") else tool_failure.dict()
            ) if tool_failure is not None else None,
        }
        state["debug"] = debug
        decision_log = state.get("decision_log", [])
        decision_log.append(
            {
                "step_id": f"numeric_tool_round_{int(current_round + 1)}",
                "agent": "RiskTool",
                "rationale": "numeric risk question matched structured desk exposure pattern",
                "chosen": str(getattr(tool_trace, "tool_name", "monitor_desk_exposure")),
                "alternatives": [str(tool_request.desk)],
            }
        )
        state["decision_log"] = decision_log
    state["tool_traces"] = tool_traces

    self_rag_enabled = os.getenv("RISKAGENT_SELF_RAG", "true").lower().strip() in {"true", "1", "yes"}
    self_sufficient = False
    if self_rag_enabled:
        g = grade_docs_crag(question=question, docs=docs)
        self_sufficient = bool(g.sufficient)
        debug = state.get("debug") or {}
        self_rag = debug.get("self_rag")
        if not isinstance(self_rag, dict):
            self_rag = {"enabled": True, "rounds": []}
        rounds = self_rag.get("rounds")
        if not isinstance(rounds, list):
            rounds = []
        rounds.append(
            {
                "round": int(current_round + 1),
                "query": str(current_query),
                "grade": {
                    "sufficient": bool(g.sufficient),
                    "reason": str(g.reason),
                    "top_isrel": float(g.top_isrel),
                    "avg_isrel": float(g.avg_isrel),
                    "question_type": str(getattr(g, "question_type", "default")),
                    "query_coverage": float(getattr(g, "query_coverage", 0.0)),
                    "claim_coverage": float(getattr(g, "claim_coverage", 0.0)),
                    "crag_tier": str(getattr(g, "crag_tier", "sufficient")),
                    "source_diversity": int(getattr(g, "source_diversity", 0)),
                    "parent_diversity": int(getattr(g, "parent_diversity", 0)),
                    "numeric_evidence": bool(getattr(g, "numeric_evidence", False)),
                    "docs": [gd.__dict__ for gd in g.grades],
                },
            }
        )
        self_rag["rounds"] = rounds
        debug["self_rag"] = self_rag
        state["debug"] = debug

        decision_log = state.get("decision_log", [])
        decision_log.append(
            {
                "step_id": f"self_rag_grade_docs_round_{int(current_round + 1)}",
                "agent": "SelfRAG",
                "rationale": str(g.reason),
                "chosen": str(getattr(g, "crag_tier", "sufficient" if g.sufficient else "insufficient")),
                "alternatives": [
                    f"top_isrel={g.top_isrel:.3f}",
                    f"claim_coverage={float(getattr(g, 'claim_coverage', 0.0)):.3f}",
                    f"coverage={float(getattr(g, 'query_coverage', 0.0)):.3f}",
                    f"type={str(getattr(g, 'question_type', 'default'))}",
                ],
            }
        )
        state["decision_log"] = decision_log

    critique_sufficient, improved_query, critique_reason = agentic_primitives.critique_retrieval(question, docs)

    # 收集 token 用量 (critique_retrieval 内部调用了 LLM)
    token_usage = get_last_token_usage()

    next_round = current_round + 1

    # CRAG 三档决策 (FR-10): 根据 crag_tier 设置 should_continue 和 failure_reason.
    # - sufficient: 停止循环进入合成
    # - insufficient: 触发重写查询再检索 (rewrite_and_retrieve)
    # - irrelevant: 触发扩大 top_k 降级 (expand_topk)
    # self_rag 关闭时保持原有二档逻辑 (仅用 LLM critique), 不设置 CRAG failure_reason.
    crag_failure_reason: dict[str, Any] | None = None
    if self_rag_enabled:
        crag_tier = str(getattr(g, "crag_tier", "sufficient"))
        if crag_tier == "sufficient":
            # sufficient 档: 停止循环进入合成 (CRAG 判定优先于 LLM critique)
            should_continue = False
        elif crag_tier == "irrelevant":
            # irrelevant 档: 扩大 top_k 放宽过滤, 仍受 max_rounds 约束避免死循环
            should_continue = (next_round < max_rounds)
            crag_failure_reason = {"reason": "crag_irrelevant", "action": "expand_topk"}
        else:
            # insufficient 档: 重写查询再检索, 仍受 max_rounds 约束
            should_continue = (next_round < max_rounds)
            crag_failure_reason = {"reason": "crag_insufficient", "action": "rewrite_and_retrieve"}
    else:
        # self_rag 关闭: 保持原有二档逻辑
        retrieval_sufficient = bool(critique_sufficient)
        should_continue = (not retrieval_sufficient) and (next_round < max_rounds)

    # SEAL-RAG (RFC-001 FR-12): 固定容量证据集, 新证据替换最弱的, 抑制 context dilution.
    # 每轮检索的 docs 不再直接覆盖 state["docs"], 而是合并进 budget, 跨轮次保留高分证据.
    # try/except 保护: 任何异常都回退到直接使用本轮 docs, 不破坏主流程.
    seal_replacements = 0
    seal_stats: dict[str, Any] = {}
    seal_error: str | None = None
    try:
        budget = state.get("evidence_budget")
        if budget is None:
            # 第一轮 (current_round == 0) 创建 budget, 后续轮次复用并 merge
            budget = EvidenceBudget(capacity=_seal_rag_capacity())
            state["evidence_budget"] = budget
        # 逐个 add 以保留每个 doc 的真实来源 (同批 docs 可能含 tool 产出的 unknown 来源)
        for d in docs:
            score, src = _extract_doc_score(d)
            if budget.add(d, score, next_round, src):
                seal_replacements += 1
        state["docs"] = budget.get_docs()
        seal_stats = budget.stats()
    except Exception as seal_exc:  # noqa: BLE001
        # 回退到非 SEAL 模式: 直接用本轮检索结果
        state["docs"] = docs
        seal_error = str(seal_exc)
        seal_stats = {"error": seal_error, "capacity": _seal_rag_capacity()}

    # 记录 SEAL 替换情况到 debug, 便于观测与评测
    debug = state.get("debug") or {}
    if not isinstance(debug, dict):
        debug = {}
    debug["seal_replacements"] = seal_replacements
    debug["seal_budget_stats"] = seal_stats
    if seal_error is not None:
        debug["seal_error"] = seal_error
    state["debug"] = debug

    state["critique_reason"] = critique_reason
    state["improved_query"] = improved_query
    state["should_continue"] = should_continue
    state["current_round"] = next_round
    # failure_reason 携带 CRAG action, 供 node_revise_query 选择降级策略
    state["failure_reason"] = crag_failure_reason

    decision_log = state.get("decision_log", [])
    decision_log.append({
        "step_id": f"retrieve_round_{next_round}",
        "agent": "AgenticLoop",
        "rationale": critique_reason or "retrieval done",
        "chosen": "continue" if should_continue else "stop",
        "alternatives": [f"docs_count={len(docs)}"],
    })
    state["decision_log"] = decision_log

    snippet_chars = int(os.getenv("RISKAGENT_TRACE_SNIPPET_CHARS", "240"))
    doc_refs: list[dict[str, Any]] = []
    for d in docs[:8]:
        doc_refs.append(_doc_trace_row(d, snippet_chars=snippet_chars))
    _trace_node_end(
        state,
        "retrieve_and_critique",
        start_ms,
        {
            "docs_count": len(docs),
            "seal_replacements": seal_replacements,
            "seal_final_docs_count": len(state["docs"]),
            "should_continue": bool(should_continue),
            "critique_reason": str(critique_reason),
            "improved_query": str(improved_query),
            "docs": doc_refs,
        },
        token_usage=token_usage,
    )
    return state


# ---------------------------------------------------------------------------
# Node: revise_query
# ---------------------------------------------------------------------------

def node_revise_query(state: AgenticState) -> AgenticState:
    """Node: revise query based on critique."""
    start_ms = _trace_node_start(
        state,
        "revise_query",
        {"current_query": state.get("current_query", ""), "improved_query": state.get("improved_query", "")},
    )

    # SEAL-RAG (FR-12): 确保 evidence_budget 已初始化 (兜底).
    # 实际的 merge 发生在 retrieve_and_critique 节点; 这里只在缺失时创建空 budget,
    # 保证后续轮次 retrieve_and_critique 一定能拿到一个可用的 budget 实例.
    if state.get("evidence_budget") is None:
        state["evidence_budget"] = EvidenceBudget(capacity=_seal_rag_capacity())

    question = state["question"]
    current_query = state["current_query"]
    improved_query = str(state.get("improved_query", "")).strip()
    retriever = state.get("retriever")

    # CRAG (FR-10): 读取 failure_reason 中的 action, 选择对应的降级策略.
    # - expand_topk: irrelevant 档, 扩大 top_k 放宽过滤重新检索
    # - rewrite_and_retrieve: insufficient 档, 重写查询再检索
    # 其它情况 (含 failure_reason 为 None) 走普通 revise: 用 improved_query 或 question.
    # 所有 CRAG 分支都用 try/except 包裹, 失败回退到普通 revise.
    failure_reason = state.get("failure_reason")
    action = ""
    if isinstance(failure_reason, dict):
        action = str(failure_reason.get("action") or "")

    next_query = improved_query or question
    crag_action_taken = "plain_revise"  # 记录实际执行的 action, 便于 decision_log 追溯

    if action == "expand_topk" and retriever is not None:
        # irrelevant 档降级: 扩大 top_k 重新检索
        try:
            from riskagent_agenticrag.rag.crag_strategies import expand_retrieval
            current_k = _infer_retriever_k(retriever)
            expanded_docs = expand_retrieval(
                retriever=retriever,
                query=current_query,
                current_k=current_k,
            )
            # 保持原 query (只是扩大了 k), 下一轮 retrieve_and_critique 会用调大后的 k 重新检索
            next_query = current_query
            if expanded_docs:
                state["docs"] = expanded_docs
            crag_action_taken = "expand_topk"
        except Exception:  # noqa: BLE001
            # 降级失败, 回退到普通 revise
            next_query = improved_query or question
            crag_action_taken = "expand_topk_fallback"
    elif action == "rewrite_and_retrieve" and retriever is not None:
        # insufficient 档降级: 重写查询再检索
        try:
            from riskagent_agenticrag.rag.crag_strategies import rewrite_and_retrieve
            new_query, new_docs = rewrite_and_retrieve(
                retriever=retriever,
                question=question,
                previous_query=current_query,
                docs_count=len(state.get("docs") or []),
            )
            next_query = new_query
            if new_docs:
                state["docs"] = new_docs
            crag_action_taken = "rewrite_and_retrieve"
        except Exception:  # noqa: BLE001
            # 降级失败, 回退到普通 revise
            next_query = improved_query or question
            crag_action_taken = "rewrite_and_retrieve_fallback"

    state["current_query"] = next_query

    decision_log = state.get("decision_log", [])
    decision_log.append({
        "step_id": "revise_query",
        "agent": "AgenticLoop",
        "rationale": f"revise query based on critique (crag_action={crag_action_taken})",
        "chosen": next_query,
        "alternatives": [current_query],
    })
    state["decision_log"] = decision_log

    _trace_node_end(state, "revise_query", start_ms, {"next_query": next_query, "crag_action": crag_action_taken})
    return state


# ---------------------------------------------------------------------------
# Node: synthesize_answer
# ---------------------------------------------------------------------------

def node_synthesize_answer(state: AgenticState) -> AgenticState:
    """Node: synthesize final pure-RAG answer with citations."""
    start_ms = _trace_node_start(state, "synthesize_answer", {"docs_count": len(state.get("docs") or [])})
    question = state["question"]
    docs = state["docs"]

    # TARG (FR-11): simple 查询跳过检索时 docs 为空, 用 LLM 自身知识直接回答.
    # 非 simple 查询仍走检索 grounded 合成 (docs 为空时 synthesize_answer 会生成拒答报告).
    qc = state.get("query_complexity") or {}
    if qc.get("level") == "simple" and not docs:
        answer = agentic_primitives.synthesize_answer_from_model_knowledge(question=question)
    else:
        answer = agentic_primitives.synthesize_answer(
            question=question,
            docs=docs,
        )

    # 收集 token 用量 (synthesize_answer 内部调用了 LLM)
    token_usage = get_last_token_usage()

    citations = extract_citations(docs)
    answer_with_citations = agentic_primitives.attach_citations_to_each_paragraph(answer, citations)

    state["answer"] = answer_with_citations
    state["citations"] = citations

    _trace_node_end(
        state,
        "synthesize_answer",
        start_ms,
        {"answer_len": len(answer_with_citations), "citations_count": len(citations)},
        token_usage=token_usage,
    )
    return state


# ---------------------------------------------------------------------------
# LLM 申诉机制 (validate_and_save 的辅助函数)
# ---------------------------------------------------------------------------

def _llm_appeal_failure(
    question: str,
    answer: str,
    failure_reason: dict[str, Any],
    evidence_set: list[dict[str, Any]],
) -> dict[str, Any]:
    """LLM 申诉机制: 判断 gate 失败是否属于误判."""
    from riskagent_agenticrag.llm.generate import call_llm_json

    appeal_prompt = f"""你是一个质量控制审核员。请判断以下验证失败是否属于"误判"(false positive)。

原始问题: {question}

生成的回答: {answer[:800]}

验证失败的类别: {failure_reason.get('category', 'unknown')}
失败详情: {failure_reason.get('message', 'N/A')}

证据片段数量: {len(evidence_set)}

请分析:
1. 这个失败类别是否合理?
2. 回答是否真的存在所述问题?
3. 这是否可能是验证规则的过度敏感导致的误判?

以JSON格式返回:
{{
  "is_false_positive": true/false,
  "reason": "你的判断理由，1-2句话",
  "suggested_fix": "如果确实存在问题，建议如何修正（如适用）"
}}"""

    try:
        result = call_llm_json(appeal_prompt, temperature=0.0)
        return {
            "is_false_positive": result.get("is_false_positive", False),
            "reason": result.get("reason", "No reason provided"),
            "suggested_fix": result.get("suggested_fix"),
        }
    except Exception:
        return {"is_false_positive": False, "reason": "LLM appeal failed", "suggested_fix": None}


def _appeal_enabled() -> bool:
    # 中文注释: 正式评测默认关闭 appeal, 只允许显式配置开启.
    return os.getenv("RISKAGENT_ENABLE_LLM_APPEAL", "false").lower().strip() in {"true", "1", "yes"}


# ---------------------------------------------------------------------------
# Node: validate_and_save (含 LLM 申诉 + Self-RAG 生成评分 + artifact 落盘)
# ---------------------------------------------------------------------------

def node_validate_and_save(state: AgenticState) -> AgenticState:
    """Node: validate response and save artifact (with LLM appeal mechanism)."""
    start_ms = _trace_node_start(state, "validate_and_save", {"request_id": state.get("request_id", "")})
    answer = state["answer"]
    docs = state["docs"]

    evidence_set = agentic_primitives.build_evidence_set_from_docs(docs, include_text=True)
    claims = agentic_primitives.build_claims_from_answer(
        answer,
        evidence_set=evidence_set,
    )

    failure_reason = validate_response(
        report=answer,
        claims=claims,
        evidence_set=evidence_set,
        tool_traces=list(state.get("tool_traces") or []),
        docs=docs,
        require_numeric_backing=should_require_numeric_backing(
            question=state.get("question", ""),
        ),
    )

    appeal_enabled = _appeal_enabled()

    # 初始化 token 用量
    token_usage: dict[str, int] | None = None

    # 中文注释: 只有显式开启时才允许 appeal 修改 gate 结果.
    if failure_reason is not None and appeal_enabled:
        appeal_result = _llm_appeal_failure(
            question=state.get("question", ""),
            answer=answer,
            failure_reason=failure_reason,
            evidence_set=evidence_set,
        )

        # 收集 token 用量 (LLM 申诉内部调用了 LLM)
        token_usage = get_last_token_usage()

        if appeal_result.get("is_false_positive", False):
            failure_reason["appealed"] = True
            failure_reason["appeal_reason"] = appeal_result.get("reason", "")
            failure_reason["category"] = f"appealed_{failure_reason.get('category', 'unknown')}"
            failure_reason = None
        else:
            failure_reason["appealed"] = False
            failure_reason["appeal_reason"] = appeal_result.get("reason", "")
            if appeal_result.get("suggested_fix"):
                failure_reason["suggested_fix"] = appeal_result.get("suggested_fix")

    status = "ok" if failure_reason is None else "failed"
    state["status"] = status
    state["failure_reason"] = failure_reason
    state["claims"] = claims
    state["evidence_set"] = evidence_set

    prior_debug = state.get("debug") or {}
    if not isinstance(prior_debug, dict):
        prior_debug = {}
    debug_info: dict[str, Any] = {
        **prior_debug,
        "final_query": state["current_query"],
        "critique_reason": state.get("critique_reason", ""),
        "pipeline_mode": "rag_with_risk_tools",
        "llm_appeal_enabled": appeal_enabled,
        "tool_traces_count": len(state.get("tool_traces") or []),
    }
    self_rag_enabled = os.getenv("RISKAGENT_SELF_RAG", "true").lower().strip() in {"true", "1", "yes"}
    if self_rag_enabled:
        gen = grade_generation(failure_reason=failure_reason)
        self_rag = (state.get("debug") or {}).get("self_rag")
        if not isinstance(self_rag, dict):
            self_rag = {"enabled": True, "rounds": []}
        self_rag["generation"] = gen
        debug_info["self_rag"] = self_rag
        decision_log = state.get("decision_log", [])
        decision_log.append(
            {
                "step_id": "self_rag_grade_generation",
                "agent": "SelfRAG",
                "rationale": str(gen.get("message") or ""),
                "chosen": "ok" if bool(gen.get("ok")) else "fail",
                "alternatives": [str(gen.get("category") or "")],
            }
        )
        state["decision_log"] = decision_log

    request_id = str(state.get("request_id") or str(uuid.uuid4()))
    state["request_id"] = request_id
    request_data = {
        "question": state["question"],
        "max_rounds": state["max_rounds"],
    }
    response_data: dict[str, Any] = {
        "answer": answer,
        "citations": state["citations"],
        "claims": claims,
        "evidence_set": evidence_set,
        "decision_log": state.get("decision_log", []),
        "status": status,
        "failure_reason": failure_reason,
        "debug": debug_info,
    }

    structured_evidence_set = agentic_primitives.build_evidence_set_from_docs(docs, include_text=False)

    structured_payload: dict[str, Any] = {
        "request_id": request_id,
        "report": answer,
        "evidence_set": structured_evidence_set,
        "claims": claims,
        "tool_traces": list(state.get("tool_traces") or []),
        "decision_log": state.get("decision_log", []),
        "status": status,
        "failure_reason": failure_reason,
    }

    try:
        # reranker_model 优先记实际生效模型 (远程 fallback 时环境变量名会误导),
        # 检索节点已将 active_reranker_model 透传到 state, 未检索 (simple 直答) 时回退环境变量
        retriever_version = {
            "pipeline": "hybrid_query_intel_advanced_index",
            "reranker_model": str(
                state.get("active_reranker_model") or os.getenv("RISKAGENT_RERANKER_MODEL", "")
            ),
            "reranker_status": str(state.get("reranker_status") or ""),
            "dense_k": os.getenv("RISKAGENT_DENSE_K", ""),
            "sparse_k": os.getenv("RISKAGENT_SPARSE_K", ""),
            "rerank_k": os.getenv("RISKAGENT_RERANK_K", ""),
            "persist_dir": str(settings.paths.milvus_lite_dir),
        }
        trace = _ensure_trace(state)
        trace["request_id"] = str(request_id)
        trace["run_id"] = str(state.get("run_id", ""))
        trace["model_id"] = str(settings.llm.model or "")
        trace["prompt_version"] = str(os.getenv("RISKAGENT_PROMPT_VERSION", "v1"))
        trace["retriever_version"] = retriever_version
        trace["final"] = {"status": status, "failure_reason": failure_reason}
        artifact_path = save_artifact(
            request_id,
            request_data,
            response_data,
            structured_response_data=structured_payload,
            trace_data=trace,
        )
        debug_info["artifact_path"] = artifact_path
        debug_info["artifact_bundle_dir"] = str(Path(str(artifact_path)).with_suffix(""))
        debug_info["retriever_version"] = retriever_version

        # 持久化 trace 到独立文件
        artifacts_dir = os.getenv("RISKAGENT_ARTIFACTS_DIR", ".artifacts").strip()
        trace_path = save_trace(trace, artifacts_dir)
        if trace_path:
            debug_info["trace_path"] = trace_path

        # 清理过期 trace 文件 (保留最近 7 天)
        try:
            deleted = cleanup_traces(artifacts_dir, retention_days=7)
            if deleted > 0:
                debug_info.setdefault("trace_cleanup", {})["deleted"] = deleted
        except Exception:
            pass  # 清理失败不影响主流程
    except Exception as e:
        debug_info["artifact_error"] = str(e)

    debug_info["request_id"] = str(request_id)
    debug_info["run_id"] = str(state.get("run_id", ""))
    debug_info["model_id"] = str(settings.llm.model or "")
    debug_info["prompt_version"] = str(os.getenv("RISKAGENT_PROMPT_VERSION", "v1"))
    state["debug"] = debug_info

    _trace_node_end(
        state,
        "validate_and_save",
        start_ms,
        {"status": status, "failure_reason": failure_reason, "claims_count": len(claims), "evidence_count": len(evidence_set)},
        token_usage=token_usage,
    )
    return state


# ---------------------------------------------------------------------------
# 条件边 (conditional edges)
# ---------------------------------------------------------------------------

def route_after_rewrite(state: AgenticState) -> Literal["synthesize_answer", "retrieve_and_critique"]:
    """Conditional edge (TARG): rewrite 后, simple 查询跳过检索直接合成, 否则进入检索.

    simple 查询 (needs_retrieval=False) 直接路由到 synthesize_answer,
    跳过 retrieve_and_critique 节点, 避免对简单查询执行过重的检索链路.
    """
    qc = state.get("query_complexity") or {}
    if qc.get("level") == "simple" and not qc.get("needs_retrieval", True):
        return "synthesize_answer"
    return "retrieve_and_critique"


def should_continue_retrieval(state: AgenticState) -> Literal["revise_query", "synthesize_answer"]:
    """Conditional edge: should continue retrieval or directly synthesize answer."""
    # TARG 防御: 若 simple 查询误入检索节点, 直接转合成, 避免无谓的 revise 循环
    qc = state.get("query_complexity") or {}
    if qc.get("level") == "simple" and not qc.get("needs_retrieval", True):
        return "synthesize_answer"
    if state.get("should_continue", False):
        return "revise_query"
    return "synthesize_answer"

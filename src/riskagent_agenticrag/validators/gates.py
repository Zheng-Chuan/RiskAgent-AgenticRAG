# 中文注释: validator gates 实现, 确定性规则校验
# 用途: 在 LLM 输出后进行结构化校验, fail fast, 避免下游错误

import re
from typing import Any, Optional


def _extract_numbers(text: str) -> list[float]:
    matches = re.findall(r"-?\d+(?:\.\d+)?%?", str(text or ""))
    out: list[float] = []
    for m in matches:
        try:
            is_pct = m.endswith("%")
            raw = m[:-1] if is_pct else m
            v = float(raw)
            out.append(v / 100.0 if is_pct else v)
        except Exception:
            continue
    return out


def _collect_numbers(obj: Any) -> list[float]:
    nums: list[float] = []
    if obj is None:
        return nums
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, str):
        return _extract_numbers(obj)
    if isinstance(obj, dict):
        for v in obj.values():
            nums.extend(_collect_numbers(v))
        return nums
    if isinstance(obj, list):
        for v in obj:
            nums.extend(_collect_numbers(v))
        return nums
    return nums


def _token_overlap(a: str, b: str) -> int:
    at = set(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", str(a or "").lower()))
    bt = set(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", str(b or "").lower()))
    return len(at & bt)


def evidence_gate(
    claims: list[dict[str, Any]],
    evidence_set: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """
    Evidence gate: 检查每条 claim 的 evidence_ids 是否有效.

    规则:
        1. 每条 claim 的 evidence_ids 必须非空
        2. evidence_id 必须能在 evidence_set 找到
        3. 引用粒度必须到 chunk_id + start_index

    参数:
        claims: claim 列表
        evidence_set: evidence 列表

    返回:
        如果校验失败, 返回 FailureReason dict; 否则返回 None
    """
    if not claims:
        return None

    evidence_ids = {e.get("evidence_id") for e in evidence_set if e.get("evidence_id")}
    evidence_text_by_id: dict[str, str] = {}
    for e in evidence_set:
        if not isinstance(e, dict):
            continue
        eid = e.get("evidence_id")
        if not eid:
            continue
        evidence_text_by_id[str(eid)] = str(e.get("snippet") or e.get("text") or "")

    for evidence in evidence_set:
        if not evidence.get("chunk_id"):
            return {
                "category": "evidence_incomplete",
                "message": "Evidence missing chunk_id",
                "details": {"evidence_id": evidence.get("evidence_id")},
            }

    for claim in claims:
        claim_evidence_ids = claim.get("evidence_ids", [])

        if not claim_evidence_ids:
            return {
                "category": "evidence_missing",
                "message": f"Claim '{claim.get('statement', '')}' has no evidence_ids",
                "details": {"claim_id": claim.get("claim_id")},
            }

        for eid in claim_evidence_ids:
            if eid not in evidence_ids:
                return {
                    "category": "evidence_not_found",
                    "message": f"Evidence ID '{eid}' not found in evidence_set",
                    "details": {"claim_id": claim.get("claim_id"), "evidence_id": eid},
                }

        statement = str(claim.get("statement", "")).strip()
        if statement and claim_evidence_ids:
            best = 0
            for eid in claim_evidence_ids:
                text = evidence_text_by_id.get(str(eid), "")
                best = max(best, _token_overlap(statement, text))
            if best < 2:
                return {
                    "category": "evidence_not_supporting",
                    "message": "Claim does not appear supported by linked evidence snippets",
                    "details": {"claim_id": claim.get("claim_id"), "best_token_overlap": best},
                }

    return None


def _classify_number_context(text: str, num: float) -> str:
    """
    根据数字周围的上下文，判断是"计算型"还是"陈述型"数字。
    
    计算型数字特征：经过运算、推导、计算得出的结果
    陈述型数字特征：直接从原文引用、陈述的事实数据
    """
    # 计算型关键词
    calc_keywords = [
        "计算", "等于", "结果是", "得出", "总计", "sum", "total", "calculate",
        "equals", "results in", "derived", "computed", "approximately", "约"
    ]
    
    # 在数字前后50个字符内查找关键词
    text_lower = text.lower()
    num_str = str(int(num)) if num == int(num) else str(num)
    
    # 找到数字位置
    idx = text_lower.find(num_str)
    if idx == -1:
        return "unknown"
    
    # 提取上下文
    context_start = max(0, idx - 50)
    context_end = min(len(text_lower), idx + 50)
    context = text_lower[context_start:context_end]
    
    # 检查是否有计算型关键词
    for keyword in calc_keywords:
        if keyword in context:
            return "calculated"
    
    # 检查是否有引用标记（表示来自原文）
    citation_patterns = ["[source=", "[ctx", "citation", "引用"]
    for pattern in citation_patterns:
        if pattern in context:
            return "stated"
    
    # 默认分类为陈述型（保守策略）
    return "stated"


def numeric_consistency_gate(
    report: str,
    claims: list[dict[str, Any]],
    tool_traces: list[dict[str, Any]],
    evidence_set: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """
    Numeric consistency gate: 数字一致性检查.

    核心原则: 区分 "有工具链路" 和 "纯检索链路" 两种场景.
    - 有 tool_traces: 计算型数字必须与工具输出匹配
    - 无 tool_traces: 数字视为来自检索文档的陈述, 只要有 evidence 即通过
    - 无数字: 直接通过

    参数:
        report: 对话式回答
        claims: claim 列表
        tool_traces: 工具调用记录
        evidence_set: evidence 列表

    返回:
        如果校验失败, 返回 FailureReason dict; 否则返回 None
    """
    report_numbers = _extract_numbers(report)
    claim_numbers: list[float] = []
    for claim in claims:
        claim_numbers.extend(_extract_numbers(str(claim.get("statement", ""))))

    all_numbers = list(set(report_numbers + claim_numbers))
    if not all_numbers:
        return None

    # 纯检索链路: 没有 tool_traces, 数字来自检索文档
    # 只要有 evidence_set 就信任, 具体数字准确性由 faithfulness 指标检查
    if not tool_traces:
        if not evidence_set:
            return {
                "category": "numeric_stated_without_evidence",
                "message": "Answer contains numbers but no evidence to support them",
                "details": {"number_count": len(all_numbers), "has_evidence": False},
            }
        return None

    # 有 tool_traces: 分类数字, 计算型必须与工具输出匹配
    calculated_nums: list[float] = []
    stated_nums: list[float] = []

    for num in all_numbers:
        classification = _classify_number_context(report, num)
        if classification == "calculated":
            calculated_nums.append(num)
        else:
            stated_nums.append(num)

    if not calculated_nums:
        return None

    tool_numbers: list[float] = []
    for t in tool_traces:
        if not isinstance(t, dict):
            continue
        tool_numbers.extend(_collect_numbers(t.get("tool_output")))
        tool_numbers.extend(_collect_numbers(t.get("output")))

    if not tool_numbers:
        return None

    def _matches_any(x: float, *, tol_abs: float = 1e-6, tol_rel: float = 0.01) -> bool:
        for y in tool_numbers:
            if abs(x - y) <= tol_abs:
                return True
            if abs(y) > 1e-9 and abs((x - y) / y) <= tol_rel:
                return True
        return False

    unmatched: list[float] = [float(n) for n in calculated_nums if not _matches_any(n)]
    if unmatched:
        return {
            "category": "numeric_calculated_mismatch",
            "message": "Calculated numbers do not match tool outputs",
            "details": {"unmatched": unmatched[:5]},
        }

    return None


def refusal_gate(
    docs: list[Any],
    evidence_set: list[dict[str, Any]],
    report: str,
) -> Optional[dict[str, Any]]:
    """
    Refusal gate: 检查是否应该拒答.

    规则:
        - retrieval empty 或 evidence empty 时必须拒答并给 next_actions
        - 拒答时 report 必须包含明确的拒答理由和建议

    参数:
        docs: 检索到的文档列表
        evidence_set: evidence 列表
        report: 对话式回答

    返回:
        如果校验失败, 返回 FailureReason dict; 否则返回 None
    """
    has_docs = bool(docs)
    has_evidence = bool(evidence_set)
    if not has_docs or not has_evidence:
        if not report or len(report) < 20:
            return {
                "category": "refusal_incomplete",
                "message": "Should refuse with clear reason and next_actions when docs or evidence is empty",
                "details": {"docs_count": len(docs), "evidence_count": len(evidence_set)},
            }

        refusal_keywords = ["不知道", "不清楚", "无法", "不足", "补充", "添加", "do not know", "not sure", "insufficient", "add more"]
        next_action_keywords = ["next", "建议", "可以", "please", "add", "rebuild", "provide", "补充", "添加"]

        lower = report.lower()
        has_refusal = any(keyword in lower for keyword in refusal_keywords)
        has_next_actions = any(keyword in lower for keyword in next_action_keywords)

        if not has_refusal:
            if not has_docs:
                return {
                    "category": "retrieval_empty",
                    "message": "Retrieval returned empty docs and the report did not refuse",
                    "details": {"docs_count": len(docs), "evidence_count": len(evidence_set)},
                }
            return {
                "category": "no_evidence",
                "message": "Evidence is missing and the report did not refuse",
                "details": {"docs_count": len(docs), "evidence_count": len(evidence_set)},
            }

        if not has_next_actions:
            return {
                "category": "refusal_unclear",
                "message": "Refusal should include next actions suggestions",
                "details": {"docs_count": len(docs), "evidence_count": len(evidence_set)},
            }

    return None


def validate_response(
    report: str,
    claims: list[dict[str, Any]],
    evidence_set: list[dict[str, Any]],
    tool_traces: list[dict[str, Any]],
    docs: list[Any],
    *,
    require_numeric_backing: bool = True,
) -> Optional[dict[str, Any]]:
    """
    统一入口: 依次执行所有 gate, 返回第一个失败的 FailureReason.

    参数:
        report: 对话式回答
        claims: claim 列表
        evidence_set: evidence 列表
        tool_traces: 工具调用记录
        docs: 检索到的文档列表

    返回:
        如果任一 gate 失败, 返回 FailureReason dict; 否则返回 None
    """
    failure = refusal_gate(docs, evidence_set, report)
    if failure:
        return failure

    failure = evidence_gate(claims, evidence_set)
    if failure:
        return failure

    if bool(require_numeric_backing):
        failure = numeric_consistency_gate(report, claims, tool_traces, evidence_set)
        if failure:
            return failure

    return None

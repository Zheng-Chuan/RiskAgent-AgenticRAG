"""DataAgent.

中文注释: DataAgent 只负责调用工具获取结构化数据, 不写业务结论.
它的主要产出是 tool_traces, 为后续 Validator 的 numeric consistency 提供依据.
"""

from __future__ import annotations

import datetime
import re
from typing import Any, Optional

from langchain_core.documents import Document

from riskagent_agenticrag.contracts.structured import (
    FailureReason,
    StructuredRequest,
    ToolTrace,
    build_tool_trace,
)
from riskagent_agenticrag.tools.mock_risk_tool import monitor_desk_exposure


def _utc_now_iso() -> str:
    # 中文注释: 与 contract 文件保持一致的格式.
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_float(raw: str) -> Optional[float]:
    text = str(raw or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def extract_structured_request(*, question: str, request_id: str) -> Optional[StructuredRequest]:
    q = str(question or "").strip()
    if not q:
        return None

    lowered = q.lower()
    risk_keywords = ("desk", "delta", "exposure", "limit", "breach")
    if not any(k in lowered for k in risk_keywords):
        return None

    desk_match = re.search(r"\bdesk\s+([A-Za-z][A-Za-z0-9_\-/]*)", q, flags=re.IGNORECASE)
    limit_match = re.search(
        r"(?:abs\s+delta\s+limit|delta\s+limit|limit)\s*(?:=|is|of|:)?\s*([0-9][0-9,]*(?:\.\d+)?)",
        q,
        flags=re.IGNORECASE,
    )
    date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", q)

    desk = str(desk_match.group(1)).strip().upper() if desk_match else ""
    abs_delta_limit = _parse_float(limit_match.group(1)) if limit_match else None
    as_of = str(date_match.group(1)).strip() if date_match else ""

    if not desk or abs_delta_limit is None:
        return None

    return StructuredRequest(
        request_id=str(request_id or "risk-tool"),
        query=q,
        as_of=as_of or _utc_now_iso()[:10],
        desk=desk,
        abs_delta_limit=float(abs_delta_limit),
    )


def tool_output_to_document(*, tool_output: dict[str, Any], tool_trace: ToolTrace) -> Document:
    exposure = tool_output.get("exposure") or {}
    total_delta = float(exposure.get("total_delta", 0.0) or 0.0)
    breaches = tool_output.get("breaches") or []
    breach = bool(breaches)
    limit_value = 0.0
    if breach and isinstance(breaches, list) and isinstance(breaches[0], dict):
        limit_value = float(breaches[0].get("limit", 0.0) or 0.0)
    else:
        tool_input = tool_trace.tool_input if hasattr(tool_trace, "tool_input") else {}
        if isinstance(tool_input, dict):
            limit_value = float(tool_input.get("abs_delta_limit", 0.0) or 0.0)

    tool_name = str(getattr(tool_trace, "tool_name", "monitor_desk_exposure") or "monitor_desk_exposure")
    desk = str(tool_output.get("desk") or "")
    as_of = str(tool_output.get("as_of") or "")
    chunk_id = f"tool:{tool_name}:{desk}:{as_of}".strip(":")
    text = (
        f"Tool result for desk {desk} as of {as_of}. "
        f"Total delta is {total_delta:.2f}. "
        f"Absolute delta limit is {limit_value:.2f}. "
        f"Limit breach is {'yes' if breach else 'no'}."
    )
    return Document(
        page_content=text,
        metadata={
            "source": f"tool://{tool_name}",
            "chunk_id": chunk_id,
            "start_index": 0,
            "tool_name": tool_name,
            "evidence_kind": "tool_output",
            "desk": desk,
            "as_of": as_of,
            "numeric_payload": {
                "total_delta": total_delta,
                "abs_delta_limit": limit_value,
                "breach": breach,
            },
        },
    )


def run_data_agent(
    request: StructuredRequest,
    *,
    as_of: Optional[str] = None,
) -> tuple[dict[str, Any], ToolTrace, Optional[FailureReason]]:
    # 中文注释: 返回 tool_output, tool_trace, failure_reason.
    tool_name = "monitor_desk_exposure"
    tool_input = {
        "desk": request.desk,
        "as_of": as_of or request.as_of,
        "abs_delta_limit": request.abs_delta_limit,
        "market_snapshot_url": None,
    }

    started_at = _utc_now_iso()
    try:
        as_of_value = tool_input.get("as_of")
        as_of_str = str(as_of_value) if as_of_value is not None else None
        tool_output = monitor_desk_exposure(
            desk=request.desk,
            as_of=as_of_str,
            abs_delta_limit=request.abs_delta_limit,
            market_snapshot_url=None,
        )
        finished_at = _utc_now_iso()
        trace = build_tool_trace(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            started_at=started_at,
            finished_at=finished_at,
            error=None,
        )
        return tool_output, trace, None
    except Exception as exc:  # pragma: no cover
        finished_at = _utc_now_iso()
        trace = build_tool_trace(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output={},
            started_at=started_at,
            finished_at=finished_at,
            error=str(exc),
        )
        failure = FailureReason(
            category="tool_error",
            message="tool invocation failed",
            details={
                "tool_name": tool_name,
            },
        )
        return {}, trace, failure

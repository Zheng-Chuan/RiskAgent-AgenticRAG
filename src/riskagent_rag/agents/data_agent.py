"""DataAgent.

中文注释: DataAgent 只负责调用工具获取结构化数据, 不写业务结论.
它的主要产出是 tool_traces, 为后续 Validator 的 numeric consistency 提供依据.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

from riskagent_rag.contracts.structured import (
    FailureReason,
    StructuredRequest,
    ToolTrace,
    build_tool_trace,
)
from riskagent_rag.tools.mock_risk_tool import monitor_desk_exposure


def _utc_now_iso() -> str:
    # 中文注释: 与 contract 文件保持一致的格式.
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


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

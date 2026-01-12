"""Week3 scenario runner.

中文注释: Week3 先实现最小闭环.
- 用 DataAgent 调用本地 mock tool.
- 将 tool_traces 固化为 contract.
- 先返回结构化输出, report 先留空或 TODO.

后续会在此基础上引入 RAGAgent, AnalysisAgent, ValidatorAgent, ReportAgent.
"""

from __future__ import annotations

from typing import Any

from riskagent_rag.agents.data_agent import run_data_agent
from riskagent_rag.contracts.week3 import FailureReason, Week3Request, Week3Response


def run_week3(request: Week3Request) -> dict[str, Any]:
    # 中文注释: 先返回 dict, 便于 CLI 或 UI 落盘.
    tool_output, tool_trace, failure = run_data_agent(request)

    breaches = list(tool_output.get("breaches", [])) if tool_output else []

    status = "ok"
    failure_reason: FailureReason | None = None
    if failure is not None:
        status = "failed"
        failure_reason = failure

    response = Week3Response(
        request_id=request.request_id,
        report="TODO Week3 report",
        breaches=breaches,
        evidence_set=[],
        claims=[],
        tool_traces=[tool_trace],
        decision_log=[],
        status=status,
        failure_reason=failure_reason,
    )
    if hasattr(response, "model_dump"):
        return response.model_dump()  # type: ignore[attr-defined]
    return response.dict()

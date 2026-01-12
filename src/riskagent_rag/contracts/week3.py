"""Week3 contract models.

中文注释: 该文件落地 docs/ROADMAP.md Week3 contract v1.
目标是让输出结构可验证, 可回归, 可用于后续 Validator 和评测.
"""

from __future__ import annotations

import datetime
from typing import Any, Literal, Optional

try:
    # 中文注释: pydantic v2.
    from pydantic import ConfigDict  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    ConfigDict = None

from pydantic import BaseModel, Field  # type: ignore[import-not-found]

FailureCategory = Literal[
    "no_evidence",
    "retrieval_empty",
    "tool_error",
    "numeric_inconsistent",
    "evidence_not_supporting",
    "parse_error",
]

RunStatus = Literal["ok", "failed"]

ClaimConfidence = Literal["low", "medium", "high"]

ClaimStatus = Literal["supported", "unsupported", "needs_more_info"]


def _utc_now_iso() -> str:
    # 中文注释: 统一时间戳格式, 便于 logs 和 artifacts 对齐.
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class _StrictBaseModel(BaseModel):
    # 中文注释: extra=forbid 保证 contract 不被 silently 扩展.
    if ConfigDict is not None:
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover

        class Config:
            extra = "forbid"


class FailureReason(_StrictBaseModel):
    category: FailureCategory
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class Evidence(_StrictBaseModel):
    evidence_id: str
    source: str
    chunk_id: str
    start_index: int
    snippet: str


class Claim(_StrictBaseModel):
    claim_id: str
    statement: str
    evidence_ids: list[str]
    confidence: ClaimConfidence
    status: ClaimStatus
    failure_reason: Optional[FailureReason] = None


class ToolTrace(_StrictBaseModel):
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: dict[str, Any]
    started_at: str
    finished_at: str
    error: Optional[str] = None


class Decision(_StrictBaseModel):
    step_id: str
    agent: str
    rationale: str
    chosen: str
    alternatives: list[str] = Field(default_factory=list)


class Week3Request(_StrictBaseModel):
    # 中文注释: Week3 场景输入.
    request_id: str
    query: str
    as_of: str
    desk: str
    abs_delta_limit: float


class Week3Response(_StrictBaseModel):
    # 中文注释: Week3 场景输出.
    request_id: str
    report: str
    breaches: list[dict[str, Any]]
    evidence_set: list[Evidence]
    claims: list[Claim]
    tool_traces: list[ToolTrace]
    decision_log: list[Decision]
    status: RunStatus
    failure_reason: Optional[FailureReason] = None


def parse_week3_response(data: dict[str, Any]) -> Week3Response:
    # 中文注释: 兼容 pydantic v1 和 v2 的解析入口.
    if hasattr(Week3Response, "model_validate"):
        return Week3Response.model_validate(data)  # type: ignore[attr-defined]
    return Week3Response.parse_obj(data)


def build_tool_trace(
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: dict[str, Any],
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    error: Optional[str] = None,
) -> ToolTrace:
    # 中文注释: 统一构建 trace, 降低各 agent 重复代码.
    start = started_at or _utc_now_iso()
    end = finished_at or _utc_now_iso()
    return ToolTrace(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        started_at=start,
        finished_at=end,
        error=error,
    )

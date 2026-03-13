from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    error_code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    request_id: Optional[str] = None
    max_rounds: int = Field(default=2, ge=1, le=5)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    request_id: Optional[str] = None
    max_rounds: int = Field(default=2, ge=1, le=5)


class AskResponse(BaseModel):
    request_id: str
    status: Literal["ok", "failed", "error"]
    answer: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    evidence_set: list[dict[str, Any]] = Field(default_factory=list)
    decision_log: list[dict[str, Any]] = Field(default_factory=list)
    tool_traces: list[dict[str, Any]] = Field(default_factory=list)
    failure_reason: Optional[dict[str, Any]] = None
    debug: dict[str, Any] = Field(default_factory=dict)
    error: Optional[ApiError] = None


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    details: dict[str, Any] = Field(default_factory=dict)


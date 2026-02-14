from __future__ import annotations

import os
import json
import time
import uuid
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from riskagent_rag.api.schemas import (
    ApiError,
    AskRequest,
    AskResponse,
    ChatRequest,
    HealthResponse,
    ReadyResponse,
)
from riskagent_rag.app import RiskAgentSystem
from riskagent_rag.config.settings import settings
from riskagent_rag.indexing.indexer import MANIFEST_FILENAME
from riskagent_rag.indexing.milvus_store import build_milvus_client
from riskagent_rag.rag.embeddings import build_embeddings


_REQ_TOTAL = Counter("riskagent_http_requests_total", "Total HTTP requests", ["path", "method", "status"])
_REQ_LAT_MS = Histogram("riskagent_http_request_latency_ms", "HTTP request latency ms", ["path", "method"])


def _now_ms() -> float:
    return time.time() * 1000.0


def _require_api_key(x_api_key: Optional[str], authorization: Optional[str]) -> None:
    expected = os.getenv("RISKAGENT_API_KEY", "").strip()
    if not expected:
        return
    provided = ""
    if x_api_key:
        provided = str(x_api_key).strip()
    if not provided and authorization:
        auth = str(authorization).strip()
        if auth.lower().startswith("bearer "):
            provided = auth.split(" ", 1)[1].strip()
    if provided != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


def auth_dep(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> None:
    _require_api_key(x_api_key, authorization)


def _error_from_exc(exc: Exception) -> ApiError:
    msg = str(exc)
    if "Missing LLM API key" in msg:
        return ApiError(error_code="llm_missing_key", message=msg, retryable=False)
    if "Index not found" in msg or "Index not ready" in msg:
        return ApiError(error_code="index_not_ready", message=msg, retryable=False)
    if "Ollama call failed" in msg:
        return ApiError(error_code="llm_unreachable", message=msg, retryable=True)
    return ApiError(error_code="internal_error", message=msg, retryable=True)

def _error_from_http(*, code: int, detail: Any) -> ApiError:
    if code == status.HTTP_401_UNAUTHORIZED:
        return ApiError(error_code="unauthorized", message=str(detail), retryable=False)
    if code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        return ApiError(error_code="invalid_request", message="invalid request", retryable=False, details={"detail": detail})
    if code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return ApiError(error_code="not_ready", message="service not ready", retryable=True, details={"detail": detail})
    return ApiError(error_code="http_error", message=str(detail), retryable=False, details={"status_code": code})


def _make_response(*, request_id: str, out: dict[str, Any]) -> AskResponse:
    return AskResponse(
        request_id=str(request_id),
        status=str(out.get("status") or "ok"),
        answer=str(out.get("answer") or ""),
        citations=list(out.get("citations") or []),
        claims=list(out.get("claims") or []),
        evidence_set=list(out.get("evidence_set") or []),
        decision_log=list(out.get("decision_log") or []),
        tool_traces=list(out.get("tool_traces") or []),
        failure_reason=out.get("failure_reason"),
        debug=dict(out.get("debug") or {}),
        error=None,
    )


def _make_error_response(*, request_id: str, exc: Exception, http_status: int) -> AskResponse:
    return AskResponse(
        request_id=str(request_id),
        status="error",
        answer="",
        citations=[],
        claims=[],
        evidence_set=[],
        decision_log=[],
        tool_traces=[],
        failure_reason=None,
        debug={},
        error=_error_from_exc(exc),
    )


def _ready_details() -> tuple[bool, dict[str, Any]]:
    details: dict[str, Any] = {}

    persist_dir = settings.paths.milvus_lite_dir
    manifest_ok = bool(persist_dir.exists() and (persist_dir / MANIFEST_FILENAME).exists())
    details["index_manifest"] = {"ok": manifest_ok, "persist_dir": str(persist_dir)}

    llm_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    details["llm_key"] = {"ok": bool(llm_key)}

    emb_ok = False
    try:
        e = build_embeddings()
        _ = e.embed_query("ready_probe")
        emb_ok = True
    except Exception as exc:
        details["embeddings_error"] = str(exc)
    details["embeddings"] = {"ok": emb_ok}

    milvus_ok = False
    try:
        client = build_milvus_client(persist_dir=persist_dir)
        milvus_ok = True
        details["milvus"] = {"ok": True, "uri": os.getenv("MILVUS_URI") or str(persist_dir)}
        _ = client.list_collections()
    except Exception as exc:
        details["milvus"] = {"ok": False, "error": str(exc)}

    ok = bool(manifest_ok and details["llm_key"]["ok"] and emb_ok and milvus_ok)
    return ok, details


system = RiskAgentSystem()
app = FastAPI(title="RiskAgent API", version="v1")

@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    if str(request.url.path).startswith("/v1/"):
        rid = str(uuid.uuid4())
        body = AskResponse(
            request_id=rid,
            status="error",
            answer="",
            citations=[],
            claims=[],
            evidence_set=[],
            decision_log=[],
            tool_traces=[],
            failure_reason=None,
            debug={},
            error=_error_from_http(code=int(exc.status_code), detail=exc.detail),
        )
        return JSONResponse(status_code=int(exc.status_code), content=body.model_dump())
    return JSONResponse(status_code=int(exc.status_code), content={"detail": exc.detail})

@app.exception_handler(RequestValidationError)
def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    if str(request.url.path).startswith("/v1/"):
        rid = str(uuid.uuid4())
        body = AskResponse(
            request_id=rid,
            status="error",
            answer="",
            citations=[],
            claims=[],
            evidence_set=[],
            decision_log=[],
            tool_traces=[],
            failure_reason=None,
            debug={},
            error=_error_from_http(code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()),
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body.model_dump())
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/readyz", response_model=ReadyResponse)
def readyz(response: Response) -> ReadyResponse:
    ok, details = _ready_details()
    if ok:
        return ReadyResponse(status="ready", details=details)
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(status="not_ready", details=details)


@app.get("/metrics")
def metrics() -> Response:
    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/ask", response_model=AskResponse, dependencies=[Depends(auth_dep)])
def v1_ask(req: AskRequest, response: Response) -> AskResponse:
    request_id = req.request_id or str(uuid.uuid4())
    start = _now_ms()
    path = "/v1/ask"
    method = "POST"
    try:
        out = system.chat(question=req.question, history=None, max_rounds=int(req.max_rounds), request_id=request_id)
        res = _make_response(request_id=request_id, out=out)
        code = 200
        return res
    except HTTPException:
        raise
    except Exception as exc:
        res = _make_error_response(request_id=request_id, exc=exc, http_status=500)
        code = 500
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return res
    finally:
        dur = _now_ms() - start
        _REQ_TOTAL.labels(path=path, method=method, status=str(code)).inc()
        _REQ_LAT_MS.labels(path=path, method=method).observe(float(dur))
        try:
            run_id = ""
            if "out" in locals() and isinstance(locals().get("out"), dict):
                run_id = str((locals()["out"].get("debug") or {}).get("run_id") or "")
            log = {
                "request_id": str(request_id),
                "run_id": run_id,
                "path": path,
                "method": method,
                "status_code": int(code),
                "latency_ms": float(dur),
            }
            print(json.dumps(log, ensure_ascii=False))
        except Exception:
            pass


@app.post("/v1/chat", response_model=AskResponse, dependencies=[Depends(auth_dep)])
def v1_chat(req: ChatRequest, response: Response) -> AskResponse:
    request_id = req.request_id or str(uuid.uuid4())
    start = _now_ms()
    path = "/v1/chat"
    method = "POST"
    try:
        messages = req.messages or []
        user_msgs = [m for m in messages if m.role == "user"]
        if not user_msgs:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="messages must include at least one user message")

        last_user = user_msgs[-1].content
        history_pairs: list[tuple[str, str]] = []
        pending_user: Optional[str] = None
        for m in messages:
            if m.role == "user":
                pending_user = m.content
            elif m.role == "assistant":
                if pending_user is not None:
                    history_pairs.append((pending_user, m.content))
                    pending_user = None
        out = system.chat(question=last_user, history=history_pairs, max_rounds=int(req.max_rounds), request_id=request_id)
        res = _make_response(request_id=request_id, out=out)
        code = 200
        return res
    except HTTPException:
        raise
    except Exception as exc:
        res = _make_error_response(request_id=request_id, exc=exc, http_status=500)
        code = 500
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return res
    finally:
        dur = _now_ms() - start
        _REQ_TOTAL.labels(path=path, method=method, status=str(code)).inc()
        _REQ_LAT_MS.labels(path=path, method=method).observe(float(dur))
        try:
            run_id = ""
            if "out" in locals() and isinstance(locals().get("out"), dict):
                run_id = str((locals()["out"].get("debug") or {}).get("run_id") or "")
            log = {
                "request_id": str(request_id),
                "run_id": run_id,
                "path": path,
                "method": method,
                "status_code": int(code),
                "latency_ms": float(dur),
            }
            print(json.dumps(log, ensure_ascii=False))
        except Exception:
            pass


def main() -> None:
    import uvicorn

    host = os.getenv("RISKAGENT_API_HOST", "0.0.0.0")
    port = int(os.getenv("RISKAGENT_API_PORT", "8000"))
    uvicorn.run("riskagent_rag.api.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

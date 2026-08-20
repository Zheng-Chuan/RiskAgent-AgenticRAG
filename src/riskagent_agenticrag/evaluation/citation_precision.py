from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
import json
import os
import re
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from riskagent_agenticrag.evaluation.judge_llm import get_judge_llm


@dataclass(frozen=True)
class CitationPrecisionResult:
    enabled: bool
    ok: bool
    metrics: dict[str, float]
    details: list[dict[str, Any]]
    error: Optional[str] = None


@dataclass(frozen=True)
class _SampleJudgeOutcome:
    index: int
    detail: dict[str, Any] | None
    judged: bool
    skipped: bool
    errored: bool
    precision: float = 0.0
    total_sentences: int = 0
    supported_sentences: int = 0
    hallucinated: bool = False


def _to_text(x: Any) -> str:
    if x is None:
        return ""
    return str(x)


def _strip_markdown_json(text: str) -> str:
    """去除 LLM 响应中的 markdown 代码块标记, 提取纯 JSON.

    deepseek-chat 等模型可能在 JSON 外包裹 ```json ... ``` 标记.
    """
    text = text.strip()
    # 移除开头的 ```json 或 ```
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
    # 移除结尾的 ```
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _read_content(x: Any) -> str:
    if hasattr(x, "content"):
        return _to_text(getattr(x, "content"))
    return _to_text(x)


def _split_sentences(text: str) -> list[str]:
    t = str(text or "").strip()
    if not t:
        return []
    parts = re.split(r"[。！？!?\.]+\s*|\n+", t)
    out = [p.strip() for p in parts if p and p.strip()]
    return out


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "we",
    "you",
    "i",
    "they",
    "he",
    "she",
    "them",
    "us",
    "our",
    "your",
    "的",
    "了",
    "在",
    "是",
    "和",
    "与",
    "及",
    "或",
    "也",
    "都",
    "就",
    "而",
    "对",
    "把",
    "将",
}


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", str(text or "").lower())
    out: list[str] = []
    for r in raw:
        if r in _STOPWORDS:
            continue
        if len(r) <= 1 and not re.match(r"[\u4e00-\u9fff]+", r):
            continue
        out.append(r)
    return out


def _heuristic_supported(*, sentence: str, contexts: list[str], threshold: float) -> bool:
    s = sentence.strip()
    if not s:
        return True
    stoks = _tokens(s)
    if not stoks:
        return True

    stoks_set = set(stoks)
    for ctx in contexts:
        c = str(ctx or "")
        if not c:
            continue
        if len(s) >= 12 and s in c:
            return True
        ctoks = set(_tokens(c))
        overlap = len(stoks_set & ctoks)
        recall = overlap / max(1, len(stoks_set))
        if overlap >= 2 and recall >= threshold:
            return True
    return False


def _compute_heuristic_precision(answer: str, contexts: list[str]) -> tuple[int, int, float, list[str], list[str]]:
    threshold = float(os.getenv("EVAL_CITATION_HEURISTIC_THRESHOLD", "0.5"))
    sentences = _split_sentences(answer)
    sentence_support = [
        (sentence, _heuristic_supported(sentence=sentence, contexts=contexts, threshold=threshold))
        for sentence in sentences
    ]
    total_sentences = len(sentence_support)
    supported = [sentence for sentence, ok in sentence_support if ok]
    unsupported = [sentence for sentence, ok in sentence_support if not ok][:5]
    supported_sentences = len(supported)
    precision = float(supported_sentences) / float(max(1, total_sentences))
    return total_sentences, supported_sentences, precision, supported[:5], unsupported


def _debug_emit(hypothesis_id: str, msg: str, *, data: dict[str, Any] | None = None) -> None:
    # #region debug-point B:citation-judge
    env_path = ".dbg/report-hang.env"
    debug_url = "http://127.0.0.1:7777/event"
    session_id = "report-hang"
    try:
        with open(env_path, encoding="utf-8") as handle:
            for line in handle.read().splitlines():
                if line.startswith("DEBUG_SERVER_URL="):
                    debug_url = line.split("=", 1)[1].strip() or debug_url
                elif line.startswith("DEBUG_SESSION_ID="):
                    session_id = line.split("=", 1)[1].strip() or session_id
    except Exception:
        return
    payload = {
        "sessionId": session_id,
        "runId": str(os.getenv("RISKAGENT_DEBUG_RUN_ID", "pre-fix") or "pre-fix"),
        "hypothesisId": hypothesis_id,
        "location": "evaluation.citation_precision",
        "msg": f"[DEBUG] {msg}",
        "data": data or {},
        "ts": int(time.time() * 1000),
    }
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                debug_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            ),
            timeout=0.8,
        ).read()
    except Exception:
        pass
    # #endregion


_JUDGE_THREAD_LOCAL = threading.local()


def _progress_enabled() -> bool:
    return str(os.getenv("EVAL_CITATION_JUDGE_PROGRESS", "")).strip().lower() in {"1", "true", "yes", "on"}


def _heartbeat_seconds() -> float:
    try:
        value = float(os.getenv("EVAL_CITATION_JUDGE_HEARTBEAT_SEC", "10"))
    except (TypeError, ValueError):
        value = 10.0
    return max(1.0, value)


def _max_concurrency() -> int:
    try:
        value = int(os.getenv("EVAL_CITATION_JUDGE_MAX_CONCURRENCY", "4"))
    except (TypeError, ValueError):
        value = 4
    return max(1, min(16, value))


def _emit_progress(msg: str) -> None:
    if not _progress_enabled():
        return
    print(f"[citation-judge] {msg}", file=sys.stderr, flush=True)


def _thread_local_judge_llm() -> Any:
    judge_llm = getattr(_JUDGE_THREAD_LOCAL, "judge_llm", None)
    if judge_llm is None:
        judge_llm = get_judge_llm()
        _JUDGE_THREAD_LOCAL.judge_llm = judge_llm
    return judge_llm


def _judge_prompt(*, question: str, answer: str, contexts: list[str]) -> str:
    return json.dumps(
        {
            "task": "citation_precision_judge",
            "instruction": (
                "You are a strict evaluator for grounded QA. "
                "Decide how much of the answer is supported by the provided contexts. "
                "Return ONLY valid JSON, no markdown, no backticks, no explanations outside the JSON. "
                "Your entire response must be a single JSON object."
            ),
            "schema": {
                "total_sentences": "int >= 1",
                "supported_sentences": "int between 0 and total_sentences",
                "citation_precision": "float between 0 and 1",
                "unsupported_sentences": "list of strings max 5",
            },
            "input": {
                "question": question,
                "answer": answer,
                "contexts": contexts,
            },
        },
        ensure_ascii=False,
    )


def _validate_result(*, total_sentences: int, supported_sentences: int, precision: float) -> None:
    if total_sentences <= 0:
        raise ValueError("invalid total_sentences")
    if supported_sentences < 0 or supported_sentences > total_sentences:
        raise ValueError("invalid supported_sentences")
    if precision < 0.0 or precision > 1.0:
        raise ValueError("invalid citation_precision")


def _judge_one_sample(*, index: int, sample: dict[str, Any], used_mode: str) -> _SampleJudgeOutcome:
    sid = _to_text(sample.get("id"))
    question = _to_text(sample.get("question"))
    answer = _to_text(sample.get("answer"))
    contexts = sample.get("contexts")
    if not isinstance(contexts, list):
        contexts = []
    contexts = [_to_text(c) for c in contexts if _to_text(c).strip()]
    if not answer.strip() or not contexts:
        return _SampleJudgeOutcome(index=index, detail=None, judged=False, skipped=True, errored=False)

    try:
        sentences = _split_sentences(answer)
        if used_mode == "llm":
            _debug_emit(
                "B",
                "judge_sample_start",
                data={"index": index, "id": sid, "contexts": len(contexts), "sentences": len(sentences)},
            )
            raw = _thread_local_judge_llm().invoke(_judge_prompt(question=question, answer=answer, contexts=contexts))
            _debug_emit("B", "judge_sample_returned", data={"index": index, "id": sid})
            content = _strip_markdown_json(_read_content(raw))
            parsed = json.loads(content)
            total_sentences = int(parsed.get("total_sentences", 0))
            supported_sentences = int(parsed.get("supported_sentences", 0))
            precision = float(parsed.get("citation_precision", 0.0))
            unsupported = parsed.get("unsupported_sentences", [])
            if not isinstance(unsupported, list):
                unsupported = []
            unsupported = [_to_text(u) for u in unsupported][:5]
            supported = [sentence for sentence in sentences if sentence not in unsupported][:supported_sentences]
            mode_name = "llm"
        else:
            total_sentences, supported_sentences, precision, supported, unsupported = _compute_heuristic_precision(
                answer=answer,
                contexts=contexts,
            )
            mode_name = used_mode
        _validate_result(
            total_sentences=total_sentences,
            supported_sentences=supported_sentences,
            precision=precision,
        )
        detail = {
            "id": sid,
            "citation_precision": precision,
            "total_sentences": total_sentences,
            "supported_sentences_count": supported_sentences,
            "supported_sentences": supported[:5],
            "unsupported_sentences": unsupported,
            "mode": mode_name,
        }
        if used_mode == "llm":
            _debug_emit(
                "B",
                "judge_sample_done",
                data={"index": index, "id": sid, "precision": precision, "unsupported": len(unsupported)},
            )
        return _SampleJudgeOutcome(
            index=index,
            detail=detail,
            judged=True,
            skipped=False,
            errored=False,
            precision=precision,
            total_sentences=total_sentences,
            supported_sentences=supported_sentences,
            hallucinated=bool(unsupported),
        )
    except Exception as e:
        _debug_emit(
            "B",
            "judge_sample_error",
            data={"index": index, "id": sid, "mode": used_mode, "error": _to_text(e)},
        )
        if used_mode == "llm":
            try:
                total_sentences, supported_sentences, precision, supported, unsupported = _compute_heuristic_precision(
                    answer=answer,
                    contexts=contexts,
                )
                _validate_result(
                    total_sentences=total_sentences,
                    supported_sentences=supported_sentences,
                    precision=precision,
                )
                detail = {
                    "id": sid,
                    "citation_precision": precision,
                    "total_sentences": total_sentences,
                    "supported_sentences_count": supported_sentences,
                    "supported_sentences": supported,
                    "unsupported_sentences": unsupported,
                    "mode": "heuristic_fallback",
                    "fallback_error": _to_text(e),
                }
                _debug_emit(
                    "B",
                    "judge_sample_heuristic_fallback_done",
                    data={"index": index, "id": sid, "precision": precision, "unsupported": len(unsupported)},
                )
                return _SampleJudgeOutcome(
                    index=index,
                    detail=detail,
                    judged=True,
                    skipped=False,
                    errored=False,
                    precision=precision,
                    total_sentences=total_sentences,
                    supported_sentences=supported_sentences,
                    hallucinated=bool(unsupported),
                )
            except Exception as fallback_error:
                _debug_emit(
                    "B",
                    "judge_sample_fallback_error",
                    data={"index": index, "id": sid, "error": _to_text(fallback_error)},
                )
                return _SampleJudgeOutcome(
                    index=index,
                    detail={
                        "id": sid,
                        "error": _to_text(fallback_error),
                        "mode": "heuristic_fallback",
                        "fallback_error": _to_text(e),
                    },
                    judged=False,
                    skipped=False,
                    errored=True,
                )
        return _SampleJudgeOutcome(
            index=index,
            detail={"id": sid, "error": _to_text(e), "mode": used_mode},
            judged=False,
            skipped=False,
            errored=True,
        )


def try_compute_citation_precision(
    *,
    samples: list[dict[str, Any]],
    mode: str = "auto",
) -> CitationPrecisionResult:
    effective_mode = (mode or "auto").lower().strip()
    if effective_mode not in {"auto", "llm", "heuristic"}:
        raise ValueError("citation judge mode must be auto llm or heuristic")

    used_mode = effective_mode
    if effective_mode in {"auto", "llm"}:
        try:
            _JUDGE_THREAD_LOCAL.judge_llm = get_judge_llm()
            used_mode = "llm"
            _debug_emit("B", "judge_llm_ready", data={"mode": used_mode})
        except Exception:
            if effective_mode == "llm":
                raise
            used_mode = "heuristic"
            _debug_emit("B", "judge_llm_unavailable_fallback", data={"mode": used_mode})

    judged = 0
    skipped = 0
    errors = 0
    sum_precision = 0.0
    hallucinated = 0
    total_sentences_sum = 0
    supported_sentences_sum = 0
    details_by_index: dict[int, dict[str, Any]] = {}
    total_candidates = sum(
        1
        for sample in samples
        if str(sample.get("answer", "")).strip() and isinstance(sample.get("contexts"), list) and any(str(c).strip() for c in sample.get("contexts", []))
    )
    started_at = time.monotonic()

    def _apply_outcome(outcome: _SampleJudgeOutcome) -> None:
        nonlocal judged, skipped, errors, sum_precision, hallucinated, total_sentences_sum, supported_sentences_sum
        if outcome.detail is not None:
            details_by_index[outcome.index] = outcome.detail
        if outcome.skipped:
            skipped += 1
            return
        if outcome.errored:
            errors += 1
            return
        if not outcome.judged:
            return
        judged += 1
        sum_precision += outcome.precision
        total_sentences_sum += outcome.total_sentences
        supported_sentences_sum += outcome.supported_sentences
        if outcome.hallucinated:
            hallucinated += 1

    if used_mode == "llm" and total_candidates > 0:
        max_workers = min(_max_concurrency(), max(1, total_candidates))
        heartbeat_sec = _heartbeat_seconds()
        _emit_progress(f"start total={total_candidates} concurrency={max_workers}")
        _debug_emit("B", "judge_parallel_start", data={"total": total_candidates, "concurrency": max_workers})
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="citation-judge") as executor:
            future_to_index: dict[Future[_SampleJudgeOutcome], int] = {
                executor.submit(_judge_one_sample, index=idx, sample=sample, used_mode=used_mode): idx
                for idx, sample in enumerate(samples, start=1)
            }
            pending = set(future_to_index.keys())
            completed = 0
            while pending:
                done, pending = wait(pending, timeout=heartbeat_sec, return_when=FIRST_COMPLETED)
                if not done:
                    elapsed = time.monotonic() - started_at
                    _debug_emit(
                        "B",
                        "judge_heartbeat",
                        data={"completed": completed, "total": total_candidates, "running": len(pending), "elapsed_s": round(elapsed, 1)},
                    )
                    _emit_progress(
                        f"heartbeat completed={completed}/{total_candidates} running={len(pending)} elapsed={elapsed:.1f}s"
                    )
                    continue
                for future in done:
                    outcome = future.result()
                    _apply_outcome(outcome)
                    if not outcome.skipped:
                        completed += 1
                        last_id = ""
                        if outcome.detail is not None:
                            last_id = str(outcome.detail.get("id") or "")
                        elapsed = time.monotonic() - started_at
                        _debug_emit(
                            "B",
                            "judge_progress",
                            data={
                                "completed": completed,
                                "total": total_candidates,
                                "running": len(pending),
                                "judged": judged,
                                "errors": errors,
                                "last_id": last_id,
                                "elapsed_s": round(elapsed, 1),
                            },
                        )
                        _emit_progress(
                            f"completed={completed}/{total_candidates} running={len(pending)} judged={judged} errors={errors} last={last_id} elapsed={elapsed:.1f}s"
                        )
    else:
        for idx, sample in enumerate(samples, start=1):
            outcome = _judge_one_sample(index=idx, sample=sample, used_mode=used_mode)
            _apply_outcome(outcome)

    details = [details_by_index[index] for index in sorted(details_by_index.keys())]

    if judged <= 0:
        return CitationPrecisionResult(
            enabled=True,
            ok=False,
            metrics={},
            details=details,
            error="no samples judged",
        )

    mean_precision = sum_precision / judged
    metrics = {
        "citation_precision": mean_precision,
        "hallucination_rate_in_citations": hallucinated / judged,
        "sentence_support_rate": float(supported_sentences_sum) / float(max(1, total_sentences_sum)),
        "unsupported_sentence_rate": 1.0 - (float(supported_sentences_sum) / float(max(1, total_sentences_sum))),
        "judged": float(judged),
        "skipped": float(skipped),
        "errors": float(errors),
    }
    _emit_progress(f"done judged={judged} skipped={skipped} errors={errors} elapsed={time.monotonic() - started_at:.1f}s")
    _debug_emit(
        "B",
        "citation_precision_summary",
        data={"judged": judged, "skipped": skipped, "errors": errors, "mode": used_mode},
    )
    return CitationPrecisionResult(enabled=True, ok=True, metrics=metrics, details=details)

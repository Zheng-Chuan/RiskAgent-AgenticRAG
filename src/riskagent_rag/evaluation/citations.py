"""Citations based evaluation.

中文注释 先实现确定性指标
- citations coverage
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _normalize_path(p: str) -> str:
    return "/" + str(p).replace("\\", "/").strip("/") + "/"


def is_valid_citation(citation: dict[str, Any], *, corpus_dir_name: str = "corpus") -> bool:
    source = str(citation.get("source", ""))
    chunk_id = str(citation.get("chunk_id", ""))
    if not source or not chunk_id:
        return False

    normalized = _normalize_path(source)
    marker = f"/{corpus_dir_name.strip('/')}/"
    return marker in normalized


@dataclass(frozen=True)
class CoverageResult:
    total: int
    passed: int

    @property
    def coverage(self) -> float:
        if self.total <= 0:
            return 0.0
        return self.passed / self.total


def compute_citations_coverage(
    samples: list[dict[str, Any]],
    *,
    corpus_dir_name: str = "corpus",
) -> CoverageResult:
    total = len(samples)
    passed = 0
    for s in samples:
        citations = s.get("citations")
        if not isinstance(citations, list):
            citations = []
        valid = [c for c in citations if isinstance(c, dict) and is_valid_citation(c, corpus_dir_name=corpus_dir_name)]
        if valid:
            passed += 1
    return CoverageResult(total=total, passed=passed)

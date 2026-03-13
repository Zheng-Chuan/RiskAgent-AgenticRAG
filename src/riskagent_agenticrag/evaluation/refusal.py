from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RefusalMetrics:
    positive_total: int
    negative_total: int
    false_refusals: int
    true_refusals: int

    @property
    def false_refusal_rate(self) -> float:
        if self.positive_total <= 0:
            return 0.0
        return self.false_refusals / self.positive_total

    @property
    def true_refusal_rate(self) -> float:
        if self.negative_total <= 0:
            return 0.0
        return self.true_refusals / self.negative_total


def is_refusal_answer(*, answer: str, citations: list[dict[str, Any]]) -> bool:
    a = (answer or "").lower()
    if citations:
        return False
    if "could not find evidence in corpus" in a:
        return True
    keywords = ["do not know", "not sure", "insufficient", "无法", "不足", "不知道"]
    return any(k.lower() in a for k in keywords)


def compute_refusal_metrics(*, samples: list[dict[str, Any]]) -> RefusalMetrics:
    positive_total = 0
    negative_total = 0
    false_refusals = 0
    true_refusals = 0

    for s in samples:
        expected_refuse = bool(s.get("expected_refuse", False))
        got_refuse = bool(s.get("got_refuse", False))
        if expected_refuse:
            negative_total += 1
            if got_refuse:
                true_refusals += 1
        else:
            positive_total += 1
            if got_refuse:
                false_refusals += 1

    return RefusalMetrics(
        positive_total=positive_total,
        negative_total=negative_total,
        false_refusals=false_refusals,
        true_refusals=true_refusals,
    )


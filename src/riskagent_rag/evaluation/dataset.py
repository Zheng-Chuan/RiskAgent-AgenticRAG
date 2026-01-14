"""Evaluation dataset loader.

中文注释
- 兼容最小 questions.json
- 支持扩展 eval_set.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class EvalItem:
    item_id: str
    question: str
    reference_answer: Optional[str]
    ground_truth_contexts: Optional[list[str]]


def load_dataset(path: Path) -> list[EvalItem]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("dataset file must be a list")

    items: list[EvalItem] = []
    for idx, obj in enumerate(raw):
        if not isinstance(obj, dict):
            continue

        item_id = str(obj.get("id", "")) or str(idx)
        question = str(obj.get("question", "")).strip()
        if not question:
            continue

        reference_answer_raw = obj.get("reference_answer")
        reference_answer = str(reference_answer_raw).strip() if reference_answer_raw is not None else None

        gt_raw = obj.get("ground_truth_contexts")
        ground_truth_contexts: Optional[list[str]] = None
        if isinstance(gt_raw, list):
            gt_list: list[str] = []
            for c in gt_raw:
                if c is None:
                    continue
                s = str(c).strip()
                if s:
                    gt_list.append(s)
            ground_truth_contexts = gt_list

        items.append(
            EvalItem(
                item_id=item_id,
                question=question,
                reference_answer=reference_answer,
                ground_truth_contexts=ground_truth_contexts,
            )
        )

    return items

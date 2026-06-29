"""Evaluation dataset loader.

中文注释
- 兼容最小 questions.json
- 支持扩展 eval_set.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class EvalQrel:
    qrel_id: str
    text: Optional[str]
    relevance: int
    chunk_id: Optional[str] = None
    source: Optional[str] = None
    section_path: Optional[str] = None
    parent_id: Optional[str] = None


@dataclass(frozen=True)
class EvalGateLabel:
    should_block: bool
    label_source: str
    reason: str


@dataclass(frozen=True)
class EvalItem:
    item_id: str
    question: str
    reference_answer: Optional[str]
    ground_truth_contexts: Optional[list[str]]
    reference_contexts: Optional[list[str]]  # For context_precision metric
    tags: list[str]
    qrels: list[EvalQrel]
    gate_label: Optional[EvalGateLabel]


def _load_qrel_gap_allowlist(path: Path) -> dict[str, str]:
    allowlist_path = path.with_name("qrels_gap_allowlist.json")
    if not allowlist_path.exists():
        return {}
    raw = json.loads(allowlist_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("qrels gap allowlist file must be a list")
    out: dict[str, str] = {}
    for row in raw:
        if not isinstance(row, dict):
            continue
        item_id = str(row.get("id", "")).strip()
        if not item_id:
            continue
        reason = str(row.get("reason", "")).strip() or "approved_gap"
        out[item_id] = reason
    return out


def load_dataset(path: Path) -> list[EvalItem]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("dataset file must be a list")

    qrel_gap_allowlist = _load_qrel_gap_allowlist(path)
    qrels_by_id: dict[str, list[EvalQrel]] = {}
    qrels_path = path.with_name("qrels.json")
    if qrels_path.exists():
        qrels_raw = json.loads(qrels_path.read_text(encoding="utf-8"))
        if not isinstance(qrels_raw, list):
            raise ValueError("qrels file must be a list")
        for row in qrels_raw:
            if not isinstance(row, dict):
                continue
            item_id = str(row.get("id", "")).strip()
            if not item_id:
                continue
            parsed_qrels: list[EvalQrel] = []
            has_text_only_qrel = False
            raw_qrels = row.get("qrels")
            if isinstance(raw_qrels, list):
                for index, qrel in enumerate(raw_qrels):
                    if not isinstance(qrel, dict):
                        continue
                    text_raw = str(qrel.get("text", "")).strip()
                    text = text_raw or None
                    chunk_id = str(qrel.get("chunk_id", "")).strip() or None
                    source = str(qrel.get("source", "")).strip() or None
                    section_path = str(qrel.get("section_path", "")).strip() or None
                    parent_id = str(qrel.get("parent_id", "")).strip() or None
                    if not any([text, chunk_id, source, section_path, parent_id]):
                        continue
                    qrel_id = str(qrel.get("qrel_id", "")).strip() or f"{item_id}_r{index + 1}"
                    try:
                        relevance = int(qrel.get("relevance", 1))
                    except (TypeError, ValueError):
                        relevance = 1
                    if text and not any([chunk_id, source, section_path, parent_id]):
                        has_text_only_qrel = True
                    parsed_qrels.append(
                        EvalQrel(
                            qrel_id=qrel_id,
                            text=text,
                            relevance=max(1, relevance),
                            chunk_id=chunk_id,
                            source=source,
                            section_path=section_path,
                            parent_id=parent_id,
                        )
                    )
            if has_text_only_qrel and item_id not in qrel_gap_allowlist:
                raise ValueError(f"text-only qrels for {item_id} require qrels_gap_allowlist.json approval")
            qrels_by_id[item_id] = parsed_qrels

    gate_labels_by_id: dict[str, EvalGateLabel] = {}
    gate_labels_path = path.with_name("gate_labels.json")
    if gate_labels_path.exists():
        gate_raw = json.loads(gate_labels_path.read_text(encoding="utf-8"))
        if not isinstance(gate_raw, list):
            raise ValueError("gate labels file must be a list")
        for row in gate_raw:
            if not isinstance(row, dict):
                continue
            item_id = str(row.get("id", "")).strip()
            if not item_id:
                continue
            gate_labels_by_id[item_id] = EvalGateLabel(
                should_block=bool(row.get("should_block", False)),
                label_source=str(row.get("label_source", "manual")).strip() or "manual",
                reason=str(row.get("reason", "")).strip(),
            )

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

        # Load reference_contexts for context_precision metric
        ref_ctx_raw = obj.get("reference_contexts")
        reference_contexts: Optional[list[str]] = None
        if isinstance(ref_ctx_raw, list):
            ref_ctx_list: list[str] = []
            for c in ref_ctx_raw:
                if c is None:
                    continue
                s = str(c).strip()
                if s:
                    ref_ctx_list.append(s)
            reference_contexts = ref_ctx_list

        tags_raw = obj.get("tags")
        tags: list[str] = []
        if isinstance(tags_raw, list):
            for tag in tags_raw:
                s = str(tag).strip()
                if s and s not in tags:
                    tags.append(s)

        items.append(
            EvalItem(
                item_id=item_id,
                question=question,
                reference_answer=reference_answer,
                ground_truth_contexts=ground_truth_contexts,
                reference_contexts=reference_contexts,
                tags=tags,
                qrels=qrels_by_id.get(item_id, []),
                gate_label=gate_labels_by_id.get(item_id),
            )
        )

    return items

"""逐题分析 recall@5 缺口: 哪些题拉低了均值, 检索到了什么, gold 是什么.

复用评测同款匹配逻辑 (advanced_metrics), 保证与报告口径一致.

用法:
    python scripts/analyze_recall_gaps.py --report .artifacts/reports/rag_eval_v9b_final.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from riskagent_agenticrag.evaluation.advanced_metrics import (
    _matched_qrel_ids,
    _retrieved_rows,
    _sample_qrels,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=".artifacts/reports/rag_eval_v9b_final.json")
    parser.add_argument("--top", type=int, default=15, help="展示最差的 N 题")
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    samples: list[dict[str, Any]] = report.get("samples", [])

    rows: list[dict[str, Any]] = []
    for s in samples:
        qrels = _sample_qrels(s)
        retrieved = _retrieved_rows(s)
        # 评测最终送入 rerank 的 docs 即 retrieved_docs (final_k 覆盖 max k)
        if not qrels:
            rows.append({"id": s.get("id"), "question": s.get("question", "")[:60],
                         "n_qrels": 0, "hit": 0, "recall": None, "missed": [], "retrieved_src": []})
            continue

        gold_ids = []
        for idx, q in enumerate(qrels, start=1):
            qid = str(q.get("qrel_id") or f"qrel_{idx}")
            gold_ids.append((qid, q))

        top5 = retrieved[:5]
        hit_ids: set[str] = set()
        retrieved_srcs = []
        for row in top5:
            retrieved_srcs.append(str(row.get("source") or row.get("chunk_id") or "?")[-40:])
            for mid in _matched_qrel_ids(row, qrels):
                hit_ids.add(mid)

        missed = [(qid, q) for qid, q in gold_ids if qid not in hit_ids]
        recall = len(hit_ids) / len(gold_ids) if gold_ids else None
        rows.append({
            "id": s.get("id"), "question": str(s.get("question", ""))[:60],
            "n_qrels": len(gold_ids), "hit": len(hit_ids), "recall": recall,
            "missed": missed, "retrieved_src": retrieved_srcs,
        })

    scored = [r for r in rows if r["recall"] is not None]
    zero = [r for r in scored if r["recall"] == 0.0]
    partial = [r for r in scored if 0.0 < r["recall"] < 1.0]
    full = [r for r in scored if r["recall"] >= 1.0]
    avg = sum(r["recall"] for r in scored) / len(scored)
    print(f"recall@5 = {avg:.3f} | 满分 {len(full)} 题, 部分 {len(partial)} 题, 零分 {len(zero)} 题\n")

    # 多 gold 严格惩罚视角: 命中至少一个 gold 的题占比
    at_least_one = [r for r in scored if r["hit"] > 0]
    print(f"命中 >=1 gold 的题: {len(at_least_one)}/{len(scored)} ({len(at_least_one)/len(scored):.2%})")
    print(f"完全脱靶的题: {[r['id'] for r in zero]}\n")

    print(f"=== 零分题明细 (top {args.top}) ===")
    for r in sorted(scored, key=lambda x: x["recall"])[: args.top]:
        print(f"\n[{r['id']}] recall={r['recall']:.2f} ({r['hit']}/{r['n_qrels']}) {r['question']}")
        print("  检索到 (top5):")
        for src in r["retrieved_src"]:
            print(f"    - {src}")
        print("  未命中 gold:")
        for qid, q in r["missed"][:3]:
            print(f"    - {qid} src={str(q.get('source',''))[-45:]} sec={str(q.get('section_path',''))[:40]}")
            print(f"      text: {str(q.get('text',''))[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

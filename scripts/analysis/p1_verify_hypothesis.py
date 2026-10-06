"""P1 研究: 补充验证 -- 灌水基线证据 + 无重复下降题明细.

中文注释
- 验证 1: v10e 有重复题 vs 无重复题的 precision 基线 (重复片段灌水证据)
- 验证 2: 无重复但大幅下降的题 (q41/q31) 的 context 构成变化明细
- 验证 3: 敏感性分析 -- 重复片段分数取不同值时 v10e "去重口径" precision
"""

from __future__ import annotations

import json
from pathlib import Path

REPORTS = {
    "v10e": Path(".artifacts/reports/rag_eval_prod_pipeline_v10e_crag_off_ab_20260824_104435.json"),
    "v10f": Path(".artifacts/reports/rag_eval_prod_pipeline_v10f_crag_hybrid_20260825_031459.json"),
}


def norm(text: str) -> str:
    return (text or "").strip()


def main() -> None:
    data = {tag: json.loads(p.read_text(encoding="utf-8")) for tag, p in REPORTS.items()}
    samples_e = {s["id"]: s for s in data["v10e"]["samples"]}
    samples_f = {s["id"]: s for s in data["v10f"]["samples"]}
    ids = [s["id"] for s in data["v10e"]["samples"]]
    prec_e = dict(zip(ids, data["v10e"]["ragas"]["raw_scores"]["ragas_context_precision_no_ref"], strict=False))
    prec_f = dict(zip(ids, data["v10f"]["ragas"]["raw_scores"]["ragas_context_precision_no_ref"], strict=False))

    dup_in_e = {}
    for qid, s in samples_e.items():
        texts = [norm(c) for c in s["contexts"]]
        dup_in_e[qid] = len(texts) - len(set(texts))
    dup_qids = [q for q in ids if dup_in_e[q] > 0]
    nodup_qids = [q for q in ids if dup_in_e[q] == 0]

    # ---- 验证 1: v10e 基线灌水证据 ----
    print("## V1. v10e 基线: 有重复题 vs 无重复题的 precision (同版本内部对比)")
    pe_dup = sum(prec_e[q] for q in dup_qids) / len(dup_qids)
    pe_nodup = sum(prec_e[q] for q in nodup_qids) / len(nodup_qids)
    print(f"  v10e 有重复题 (n={len(dup_qids)}): precision = {pe_dup:.3f}")
    print(f"  v10e 无重复题 (n={len(nodup_qids)}): precision = {pe_nodup:.3f}")
    print(f"  灌水幅度 (有重复 - 无重复): {pe_dup - pe_nodup:+.3f}")

    # ---- 验证 2: 无重复但下降大的题明细 ----
    print("\n## V2. 无重复但 precision 下降 > 0.2 的题 (纯 CRAG 混合策略影响)")
    for q in nodup_qids:
        d = prec_f[q] - prec_e[q]
        if d < -0.2:
            se, sf = samples_e[q], samples_f[q]
            print(f"\n  --- {q} (v10e {prec_e[q]:.3f} -> v10f {prec_f[q]:.3f}, diff {d:+.3f}) ---")
            print(f"  question: {se['question'][:90]}")
            print(f"  tags: {se.get('tags')}")
            srcs_e = [doc.get("source", "?").split("/")[-1] for doc in se.get("retrieved_docs") or []]
            srcs_f = [doc.get("source", "?").split("/")[-1] for doc in sf.get("retrieved_docs") or []]
            print(f"  v10e docs: {srcs_e}")
            print(f"  v10f docs: {srcs_f}")
            # context 首行对比
            print("  v10e contexts 首行:")
            for i, c in enumerate(se["contexts"]):
                print(f"    [{i}] {norm(c)[:70]!r}")
            print("  v10f contexts 首行:")
            for i, c in enumerate(sf["contexts"]):
                print(f"    [{i}] {norm(c)[:70]!r}")

    # ---- 验证 3: 敏感性分析 ----
    print("\n## V3. 敏感性分析: v10e 重复片段分数 s_dup 假设下的 '去重口径' precision")
    overall_e = sum(prec_e.values()) / 50
    n_dup_slots = sum(dup_in_e.values())  # 46 个重复槽位
    # 去重不补位: 每题 contexts 从 4 -> 4-dup, 重复片段分数从总分中去掉一份
    for s_dup in (0.5, 0.7, 0.8, 0.9, 1.0):
        # per-question: dedup_prec = (4*prec_e - dup_count*s_dup) / (4 - dup_count)
        total = 0.0
        for q in ids:
            k = dup_in_e[q]
            if k == 0:
                total += prec_e[q]
            else:
                total += (4 * prec_e[q] - k * s_dup) / (4 - k)
        print(f"  s_dup={s_dup:.1f}: v10e 去重口径 precision = {total/50:.3f}")

    print(f"\n  参考: v10e 原始口径 {overall_e:.3f} (重复片段计分), v10f 实测 {sum(prec_f.values())/50:.3f} (去重+补位)")


if __name__ == "__main__":
    main()

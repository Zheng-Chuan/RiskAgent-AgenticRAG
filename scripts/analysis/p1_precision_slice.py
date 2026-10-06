"""P1 研究: ragas precision slice 分析 -- 核心对比脚本.

中文注释
- per-sample precision diff (v10e CRAG OFF vs v10f hybrid)
- context 构成变化: 重复片段 / 换入新片段 / 有效片段数
- 分题型 (tags) slice 统计
- 输出 markdown 报告供沉淀
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

REPORTS = {
    "v10e": Path(".artifacts/reports/rag_eval_prod_pipeline_v10e_crag_off_ab_20260824_104435.json"),
    "v10f": Path(".artifacts/reports/rag_eval_prod_pipeline_v10f_crag_hybrid_20260825_031459.json"),
}


def norm(text: str) -> str:
    """文本归一化 (前后空格), 用于重复片段判定."""
    return (text or "").strip()


def main() -> None:
    data = {tag: json.loads(p.read_text(encoding="utf-8")) for tag, p in REPORTS.items()}
    samples_e = {s["id"]: s for s in data["v10e"]["samples"]}
    samples_f = {s["id"]: s for s in data["v10f"]["samples"]}
    prec_e = data["v10e"]["ragas"]["raw_scores"]["ragas_context_precision_no_ref"]
    prec_f = data["v10f"]["ragas"]["raw_scores"]["ragas_context_precision_no_ref"]
    ids_e = [s["id"] for s in data["v10e"]["samples"]]
    ids_f = [s["id"] for s in data["v10f"]["samples"]]
    assert ids_e == ids_f, "sample 顺序不一致, 无法对齐"
    prec_e = dict(zip(ids_e, prec_e, strict=False))
    prec_f = dict(zip(ids_f, prec_f, strict=False))

    # ---- 1. per-sample precision diff 总览 ----
    diffs = {qid: prec_f[qid] - prec_e[qid] for qid in ids_e}
    up = [q for q in ids_e if diffs[q] > 0.05]
    down = [q for q in ids_e if diffs[q] < -0.05]
    flat = [q for q in ids_e if abs(diffs[q]) <= 0.05]
    print("## 1. per-sample precision diff (v10f - v10e)")
    print(f"  平均: v10e={sum(prec_e.values())/50:.3f} -> v10f={sum(prec_f.values())/50:.3f}")
    print(f"  上升(>0.05): {len(up)} 题, 下降(<-0.05): {len(down)} 题, 持平: {len(flat)} 题")

    # ---- 2. 下降题与重复 chunk 的关系 ----
    print("\n## 2. precision 下降题 vs v10e 重复 chunk")
    dup_in_e = {}
    for qid, s in samples_e.items():
        texts = [norm(c) for c in s["contexts"]]
        dup_in_e[qid] = len(texts) - len(set(texts))
    down_with_dup = sum(1 for q in down if dup_in_e[q] > 0)
    print(f"  下降题 {len(down)} 个中, v10e 存在重复片段: {down_with_dup} ({down_with_dup/len(down)*100:.0f}%)")
    # 全量: 重复题 vs 非重复题的平均 precision 变化
    dup_qids = [q for q in ids_e if dup_in_e[q] > 0]
    nodup_qids = [q for q in ids_e if dup_in_e[q] == 0]
    avg_dup = sum(diffs[q] for q in dup_qids) / len(dup_qids)
    avg_nodup = sum(diffs[q] for q in nodup_qids) / len(nodup_qids) if nodup_qids else 0.0
    print(f"  v10e 有重复题 (n={len(dup_qids)}): 平均 diff = {avg_dup:+.3f}")
    print(f"  v10e 无重复题 (n={len(nodup_qids)}): 平均 diff = {avg_nodup:+.3f}")

    # ---- 3. 有效 (去重后) 片段数 ----
    print("\n## 3. 有效片段数 (unique contexts)")
    uniq_e = [len({norm(c) for c in samples_e[q]["contexts"]}) for q in ids_e]
    uniq_f = [len({norm(c) for c in samples_f[q]["contexts"]}) for q in ids_e]
    print(f"  v10e: 平均 unique contexts = {sum(uniq_e)/50:.2f} (表面 4.00)")
    print(f"  v10f: 平均 unique contexts = {sum(uniq_f)/50:.2f} (表面 4.00)")

    # ---- 4. 换入新片段分析 (v10f 有而 v10e 没有的片段) ----
    print("\n## 4. v10f 换入的新片段 (相对同题 v10e)")
    new_sources = Counter()
    replaced_by_dup = Counter()  # 被去掉的 v10e 重复片段来源
    for qid in ids_e:
        texts_e = {norm(c) for c in samples_e[qid]["contexts"]}
        texts_f = {norm(c) for c in samples_f[qid]["contexts"]}
        for c in samples_f[qid].get("retrieved_docs") or []:
            if norm(c.get("content", "")) in texts_f and norm(c.get("content", "")) not in texts_e:
                new_sources[c.get("source", "?")] += 1
        for c in samples_e[qid].get("retrieved_docs") or []:
            content = norm(c.get("content", ""))
            if dup_in_e[qid] > 0:
                # 统计 v10e 中出现 >=2 次的片段来源 (被 dedup 挤掉的)
                texts_list = [norm(x) for x in samples_e[qid]["contexts"]]
                if texts_list.count(content) >= 2:
                    replaced_by_dup[c.get("source", "?")] += 1
    print(f"  换入新片段的 source 分布: {dict(new_sources.most_common(8))}")
    print(f"  v10e 重复片段 (被去掉的那份) source 分布: {dict(replaced_by_dup.most_common(8))}")

    # ---- 5. 分题型 slice ----
    print("\n## 5. 分题型 slice (tags)")
    tag_stats: dict[str, list] = defaultdict(list)
    for qid in ids_e:
        for t in samples_e[qid].get("tags") or ["untagged"]:
            tag_stats[t].append(qid)
    rows = []
    for t, qids in sorted(tag_stats.items(), key=lambda kv: -len(kv[1])):
        pe = sum(prec_e[q] for q in qids) / len(qids)
        pf = sum(prec_f[q] for q in qids) / len(qids)
        rows.append((t, len(qids), pe, pf, pf - pe))
    print(f"  {'tag':<14} {'n':>3} {'v10e':>6} {'v10f':>6} {'diff':>7}")
    for t, n, pe, pf, d in rows:
        print(f"  {t:<14} {n:>3} {pe:>6.3f} {pf:>6.3f} {d:>+7.3f}")

    # ---- 6. Top 下降题明细 ----
    print("\n## 6. Top 10 下降题明细")
    top_down = sorted(down, key=lambda q: diffs[q])[:10]
    print(f"  {'qid':<5} {'v10e':>6} {'v10f':>6} {'diff':>7} {'v10e重复':>7} {'tags':<24}")
    for q in top_down:
        tags = ",".join(samples_e[q].get("tags") or [])
        print(f"  {q:<5} {prec_e[q]:>6.3f} {prec_f[q]:>6.3f} {diffs[q]:>+7.3f} {dup_in_e[q]:>7} {tags:<24}")

    # ---- 7. 无重复题的精度变化 (纯 CRAG 混合策略影响, 剔除 dedup 因素) ----
    print("\n## 7. 剔除 dedup 因子: v10e 无重复题的 precision 变化 (纯 CRAG 混合策略影响)")
    if nodup_qids:
        pe = sum(prec_e[q] for q in nodup_qids) / len(nodup_qids)
        pf = sum(prec_f[q] for q in nodup_qids) / len(nodup_qids)
        print(f"  n={len(nodup_qids)}: v10e={pe:.3f} -> v10f={pf:.3f} (diff {pf-pe:+.3f})")


if __name__ == "__main__":
    main()

"""P1 研究: ragas precision slice 分析 -- 第一步数据结构探查.

中文注释
- 探查 v10d / v10e / v10f 三份评测报告 JSON 的结构
- 定位 per-sample precision 与 context (docs) 相关字段
- 输出到 stdout, 供后续 slice 分析使用
"""

from __future__ import annotations

import json
from pathlib import Path

REPORTS = {
    "v10d": Path(".artifacts/reports/rag_eval_prod_pipeline_v10d_full_reeval_20260821_141306.json"),
    "v10e": Path(".artifacts/reports/rag_eval_prod_pipeline_v10e_crag_off_ab_20260824_104435.json"),
    "v10f": Path(".artifacts/reports/rag_eval_prod_pipeline_v10f_crag_hybrid_20260825_031459.json"),
}


def main() -> None:
    for tag, path in REPORTS.items():
        print(f"===== {tag} =====")
        if not path.exists():
            print(f"  MISSING: {path}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        print("  top keys:", sorted(data.keys()))

        # 汇总层面 precision 指标
        for sec in ("metrics", "aggregate", "answer_metrics", "ragas", "gate_metrics"):
            val = data.get(sec)
            if isinstance(val, dict):
                prec = {k: v for k, v in val.items() if "precision" in k.lower()}
                if prec:
                    print(f"  [{sec}] precision:", json.dumps(prec, ensure_ascii=False))

        # per-sample 结构
        samples = data.get("samples") or []
        print("  n_samples:", len(samples))
        if samples:
            s0 = samples[0]
            print("  sample keys:", sorted(s0.keys()))
            # 找 sample 内 precision / context 相关字段
            for key, val in s0.items():
                kl = key.lower()
                if "precision" in kl or "context" in kl or "docs" in kl or "retrieved" in kl:
                    desc = f"    {key}: "
                    if isinstance(val, list):
                        desc += f"list[{len(val)}]"
                        if val and isinstance(val[0], dict):
                            desc += f" item_keys={sorted(val[0].keys())}"
                    elif isinstance(val, dict):
                        desc += f"dict keys={sorted(val.keys())}"
                    else:
                        desc += repr(val)[:120]
                    print(desc)

        # ragas / answer_eval section 内部结构 (找 per-sample precision)
        for sec in ("ragas", "answer_eval", "citation_precision"):
            val = data.get(sec)
            if isinstance(val, dict):
                print(f"  [{sec}] keys:", sorted(val.keys()))
                for k, v in val.items():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        print(f"    {k}: list[{len(v)}] item_keys={sorted(v[0].keys())}")

        # tags (题型) 与 decision_log 结构
        if samples:
            s0 = samples[0]
            print("  tags:", s0.get("tags"))
            print("  id/question:", s0.get("id"), "/", str(s0.get("question"))[:60])
            dl = s0.get("decision_log")
            print("  decision_log type:", type(dl).__name__)
            if isinstance(dl, list) and dl:
                print("    decision_log[0]:", json.dumps(dl[0], ensure_ascii=False)[:300])
            elif isinstance(dl, dict):
                print("    decision_log keys:", sorted(dl.keys()))
            # contexts 与 retrieved_docs 的关系
            ctx = s0.get("contexts") or []
            docs = s0.get("retrieved_docs") or []
            print("  contexts[0] 前 100 字符:", (ctx[0][:100] if ctx else None))
            print("  retrieved_docs[0] source:", (docs[0].get("source") if docs else None))
            # qrels: gold chunk_id 列表?
            print("  qrels:", json.dumps(s0.get("qrels"), ensure_ascii=False)[:200])
            print("  ground_truth_contexts[0] 前 80 字符:", (str(s0["ground_truth_contexts"][0])[:80] if s0.get("ground_truth_contexts") else None))
        print()


if __name__ == "__main__":
    main()

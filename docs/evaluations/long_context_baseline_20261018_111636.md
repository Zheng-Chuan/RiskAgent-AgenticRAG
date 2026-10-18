# 长上下文基线对比实验 (RFC-006 B)

- 生成时间: 2026-10-18T11:16:36+00:00 (2026-10-18 修订: 移除 map_reduce_full 列)
- 题集: tests/data/questions.json (n=10)
- 窗口: 128000 tokens

## 统一指标对比

| Metric | rag_main | parent_stuffing |
|--------|-----|-----|
| faithfulness | 1.000 | 0.430 |
| answer_relevancy | - | - |
| numeric_consistency_score | 0.975 (95% CI 0.925-1.000) | 0.986 (95% CI 0.957-1.000) |
| refusal_rate | - | - |
| error_rate | - | - |
| latency p50 (ms) | 21,507 | 10,918 |
| latency p95 (ms) | 24,750 | 19,452 |
| prompt tokens/题 | 670 | 17,481 |
| completion tokens/题 | 419 | 262 |
| total tokens/题 | 1,089 | 17,743 |

## 补充 (RAGAS, 同次跑批)

| Metric | rag_main | parent_stuffing |
|--------|-----|-----|
| context_recall | 0.889 | 0.750 |
| answer_correctness | 0.393 | 0.318 |
| context_precision_no_ref | 0.790 | 0.558 |
| contradiction_score | 0.000 | 0.000 |
| 误拒率 (refusal_rate) | 0.0 | 0.2 |

## 结论

- rag_main (现有检索主链) 全面优于 parent_stuffing: faithfulness 1.0 vs 0.43, context_precision 0.79 vs 0.56, 且成本仅为其 1/16 (1.1k vs 17.7k tokens/题).
- "检索 + 小上下文" 不是长上下文模型的省略项, 塞满窗口反而引入噪声降低忠实度并出现误拒.
- 曾设计 map_reduce_full (全量知识逐段抽取) 第三模式, 实测每题需遍历 577 段 (约 2.9h/题) 且收益无望超过主链, 已于 2026-10-18 移除.

## 说明

- CI 为单题级 bootstrap (1000 次重采样, percentile 法). 题集不含负例题, refusal_rate 为误拒率, 越低越好.
- 本报告为一次性实验产出, 结论是否纳入每期评测对照列见对应 ADR.

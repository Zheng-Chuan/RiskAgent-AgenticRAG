# RAG Evaluation Report - focused_smoke_after_grounding_fix_20260709

**Generated:** 2026-07-09 17:02:35

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Samples | 5 |
| Passed | 5 (100.0%) |
| Failed | 0 (0.0%) |

## Answer Evaluation

| Metric | Value | Threshold |
|--------|-------|-----------|
| citation_coverage | 1.000 | 0.8 |
| faithfulness | 0.794 | 0.75 |
| answer_relevancy | 0.540 | 0.7 |
| sentence_support_rate | 0.794 | - |

## Threshold Gate

- Verdict: fail
- Threshold Failures: 2
- Baseline Regressions: 0

## Sample Details

### Sample 1: q01

**Question:** What is FRTB and why does it matter for market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB stands for Fundamental Review of the Trading Book.
- It is a comprehensive suite of capital rules developed by the Basel Committee on Banking Supervision as part of Basel III, intended ...

**Unsupported Sentences:**
- It is a comprehensive suite of capital rules developed by the Basel Committee on Banking Supervision as part of Basel III, intended to be applied to banks' wholesale trading activities.
- FRTB was finalised in January 2016 as the Minimum Capital Requirements for Market Risk.

---

### Sample 2: q02

**Question:** Explain Delta in the context of derivatives risk.

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Delta is the sensitivity of an option's price to the underlying spot price, written as dV/dS.
- It is described as “ve to small changes in the underlying price; often used by market makers t...

**Unsupported Sentences:**
- Delta is the sensitivity of an option's price to the underlying spot price, written as dV/dS.
- From the Greeks overview: “the sensitivity of option price to spot is delta, written as dV/dS.”

---

### Sample 3: q03

**Question:** What is Gamma and how is it different from Delta?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Delta is the sensitivity to the underlying price level.
- Gamma is the sensitivity of Delta to the underlying price.

Citations: [source=corpus/Background.md chunk_id=Background.md:222936993...

---

### Sample 4: q04

**Question:** What is Vega and when is it important?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Vega is defined as the change in the market value of an option as a result of a small amount of change to the implied volatility.
- The context places vega within the sensitivity definitions...

**Unsupported Sentences:**
- The instrument’s vega and implied volatility used in the calculation of vega sensitivities must be sourced from pricing models used by the independent risk control unit of the bank.
- The implied volatility of the option must be mapped to one or more maturity tenors.

---

### Sample 5: q05

**Question:** What is CVA and what risk does it represent?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA stands for Credit Valuation Adjustment.
- CVA is an adjustment to the risk-free value that increases when counterparty credit quality worsens.
- CVA depends on the exposure profile over ...

**Unsupported Sentences:**
- In practice, CVA often interacts with collateral, netting sets, and wrong-way risk.

---

## Recommendations

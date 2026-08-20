# RAG Evaluation Report - unified_pipeline_k8s

**Generated:** 2026-08-11 15:22:12

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Samples | 50 |
| Passed | 49 (98.0%) |
| Failed | 1 (2.0%) |

## Answer Evaluation

| Metric | Value | Threshold |
|--------|-------|-----------|
| citation_coverage | 1.000 | 0.8 |
| faithfulness | 0.192 | 0.75 |
| answer_relevancy | 0.890 | 0.7 |
| sentence_support_rate | 0.192 | - |

## Threshold Gate

- Verdict: pass
- Threshold Failures: 0
- Baseline Regressions: 0

## Sample Details

### Sample 1: q01

**Question:** What is FRTB and why does it matter for market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB stands for Fundamental Review of the Trading Book and aims to improve the market risk capital framework post-2008.
- It focuses on increasing risk sensitivity and enhancing model risk g...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:9d9df405ddf4] [source=corpus/regulatory_seed/docx/en/isda_afme_frtb_position_paper
- docx chunk_id=isda_afme_frtb_position_paper

---

### Sample 2: q02

**Question:** Explain Delta in the context of derivatives risk.

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Delta measures the sensitivity of a derivative's price to changes in the price of the underlying asset.
- Vanna is a second-order Greek that measures the sensitivity of Delta to changes in i...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:c0a440a36ba4] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488
- pdf chunk_id=bis_bcbs_d488

---

### Sample 3: q03

**Question:** What is Gamma and how is it different from Delta?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions delta sensitivities in relation to minimum capital requirements for market risk.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d4...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:72a208fab649] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation
- pdf chunk_id=iosco_iq_margin_2013_consultation

---

### Sample 4: q04

**Question:** What is Vega and when is it important?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Vega is a sensitivity measure referenced in the context of minimum capital requirements for market risk.
- Vega risk buckets, risk weights, and correlations are defined under the sensitiviti...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:63af23317f33] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457

---

### Sample 5: q05

**Question:** What is CVA and what risk does it represent?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA stands for Credit Valuation Adjustment, an adjustment to the risk-free value that increases when counterparty credit quality worsens.
- CVA represents counterparty risk, the risk that th...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:02a6daa31fa9] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488
- pdf chunk_id=bis_bcbs_d488

---

### Sample 6: q06

**Question:** What does FRTB stand for?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB stands for the **Fundamental Review of the Trading Book**.
- It is a set of capital rules developed by the Basel Committee on Banking Supervision (BCBS) under Basel III.

Citations: [so...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:9d9df405ddf4] [source=corpus/regulatory_seed/docx/en/isda_afme_frtb_position_paper
- docx chunk_id=isda_afme_frtb_position_paper

---

### Sample 7: q07

**Question:** What is the purpose of FRTB?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB aims to **improve market risk capital framework after 2008** and **increase risk sensitivity and model risk governance**.
- It is a **comprehensive suite of capital rules** under Basel ...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:9d9df405ddf4] [source=corpus/regulatory_seed/docx/en/isda_afme_frtb_position_paper
- docx chunk_id=isda_afme_frtb_position_paper

---

### Sample 8: q08

**Question:** What is Credit Valuation Adjustment?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Credit Valuation Adjustment (CVA) is the price paid to hedge counterparty credit risk in derivative instruments.
- CVA reduces the mark-to-market value of an asset by its calculated value.
-...

**Unsupported Sentences:**
- 1) TLDR
- md chunk_id=cva_cfi
- md:47dc12f28674] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488
- pdf chunk_id=bis_bcbs_d488
- pdf:365c2c42a54f] [source=corpus/acceptance/cva_cfi

---

### Sample 9: q09

**Question:** When was CVA introduced as a requirement?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA was introduced as a requirement during the 2007/08 Global Financial Crisis.
- It was incorporated into fair value accounting for over-the-counter derivative instruments.

Citations: [sou...

**Unsupported Sentences:**
- 1) TLDR
- md chunk_id=cva_cfi
- md:47dc12f28674] [source=corpus/regulatory_seed/docx/en/isda_afme_cva_position_paper
- docx chunk_id=isda_afme_cva_position_paper
- docx:f873d74b794e] [source=corpus/regulatory_seed/docx/en/isda_afme_cva_position_paper

---

### Sample 10: q10

**Question:** What is XVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- XVA refers to valuation adjustments in financial derivatives accounting.

Citations: [source=corpus/regulatory_seed/md/en/wikipedia_xva.md chunk_id=wikipedia_xva.md:c510d340e7cf] [source=cor...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/md/en/wikipedia_xva
- md chunk_id=wikipedia_xva
- md:c510d340e7cf] [source=corpus/regulatory_seed/md/en/wikipedia_xva
- md chunk_id=wikipedia_xva

---

### Sample 11: q11

**Question:** What is the Basel Committee?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The Basel Committee on Banking Supervision sets minimum capital requirements for market risk (January 2019, revised February 2019).
- It collaborates with the Board of the International Orga...

**Unsupported Sentences:**
- 1) TLDR
- - It addresses credit valuation adjustment risk through consultative documents (November 2019)
- Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2020
- pdf chunk_id=iosco_iq_margin_2020
- pdf:f6aec941f5ed] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation

---

### Sample 12: q12

**Question:** When was FRTB finalized?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB was finalized in **January 2016** as the Minimum Capital Requirements for Market Risk.
- The standard was later revised in **January 2019 (rev. February 2019)** and integrated into the ...

**Unsupported Sentences:**
- 1) TLDR
- - The standard was later revised in **January 2019 (rev
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:9b89f16f75e0] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488

---

### Sample 13: q13

**Question:** What is Basel III?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Basel III is a set of standards finalized in December 2017 to address pre-crisis regulatory shortcomings and strengthen banking system resilience.
- One element of Basel III focuses on the C...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488
- pdf chunk_id=bis_bcbs_d488
- pdf:7f20a0149c4f] [source=corpus/acceptance/frtb_icma
- md chunk_id=frtb_icma

---

### Sample 14: q14

**Question:** What is the difference between trading book and banking book?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The **trading book** includes instruments subject to **market risk capital requirements**, while the **banking book** includes instruments subject to **credit risk capital requirements**.
- ...

**Unsupported Sentences:**
- 1) TLDR
- 2]–[RBC25
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:2f8e50ce7774] [source=corpus/Background

---

### Sample 15: q15

**Question:** What is PnL attribution?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- PnL attribution is a common concept used in interviews and systems related to FRTB (Fundamental Review of the Trading Book).
- FRTB aims to improve market risk capital framework and increase...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:9d9df405ddf4] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457

---

### Sample 16: q16

**Question:** What is backtesting in market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Backtesting in market risk involves using actual daily P&Ls to assess if risk measures accurately capture trading volatility.
- Banks must perform backtesting using both hypothetical and act...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:bf4e1063b15c] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457

---

### Sample 17: q17

**Question:** What is risk factor eligibility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Risk factor eligibility is a common concept used in FRTB (Fundamental Review of the Trading Book) interviews and systems.
- FRTB aims to improve market risk capital framework post-2008 and i...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:9d9df405ddf4] [source=corpus/regulatory_seed/docx/en/isda_afme_frtb_position_paper
- docx chunk_id=isda_afme_frtb_position_paper

---

### Sample 18: q18

**Question:** What is DVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- No usable details are available to answer the question.

Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation.pdf chunk_id=iosco_iq_margin_2013_consultation.pdf...

**Unsupported Sentences:**
- 1) TLDR
- - No usable details are available to answer the question
- Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation
- pdf chunk_id=iosco_iq_margin_2013_consultation
- pdf:a67ea8d6c6fb] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation

---

### Sample 19: q19

**Question:** What is FVA?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The context discusses trading desk definitions, regulatory approvals, and swap definitions but does not reference FVA.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pd...

**Unsupported Sentences:**
- 2) Key Facts
- - The context discusses trading desk definitions, regulatory approvals, and swap definitions but does not reference FVA
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:a45d2fc51255] [source=corpus/regulatory_seed/pdf/en/cftc_2020_27736_margin_uncleared_swaps

---

### Sample 20: q20

**Question:** What is KVA?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The context discusses trading desk definitions, regulatory approvals, and swap-related terms but does not reference KVA.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457....

**Unsupported Sentences:**
- 2) Key Facts
- - The context discusses trading desk definitions, regulatory approvals, and swap-related terms but does not reference KVA
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:a45d2fc51255] [source=corpus/regulatory_seed/pdf/en/cftc_2020_27736_margin_uncleared_swaps

---

### Sample 21: q21

**Question:** What is MVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses margin requirements for non-centrally-cleared derivatives (NCCDs) and initial margin thresholds.

Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation
- pdf chunk_id=iosco_iq_margin_2013_consultation
- pdf:7e7ba7ee6dd5] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation
- pdf chunk_id=iosco_iq_margin_2013_consultation

---

### Sample 22: q22

**Question:** What is ColVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- ColVA is not defined or mentioned in the provided context.
- The context discusses Credit Valuation Adjustment (CVA) as a pricing adjustment for counterparty credit risk in derivatives.

Cit...

**Unsupported Sentences:**
- 1) TLDR
- - ColVA is not defined or mentioned in the provided context
- Citations: [source=corpus/regulatory_seed/docx/en/isda_afme_cva_position_paper
- docx chunk_id=isda_afme_cva_position_paper
- docx:49144ae361dc] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488

---

### Sample 23: q23

**Question:** What is the default probability in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Default probability is a term included in the formula for calculating Credit Valuation Adjustment (CVA).
- CVA reduces the mark-to-market value of an asset by accounting for counterparty cre...

**Unsupported Sentences:**
- 1) TLDR
- md chunk_id=cva_cfi
- md:47dc12f28674] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488
- pdf chunk_id=bis_bcbs_d488
- pdf:481cec9634e8] [source=corpus/regulatory_seed/docx/en/isda_afme_cva_position_paper

---

### Sample 24: q24

**Question:** What is loss given default (LGD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Loss given default (LGD) refers to the probability-weighted loss on the default of a counterparty.
- Margin requirements are designed to mitigate counterparty credit risk by ensuring accessi...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation
- pdf chunk_id=iosco_iq_margin_2013_consultation
- pdf:46432c3b3d5c] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation
- pdf chunk_id=iosco_iq_margin_2013_consultation

---

### Sample 25: q25

**Question:** What is exposure at default (EAD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Exposure at Default (EAD) is derived from Effective Expected Positive Exposure (EEPE) using a multiplier (α) in both SA-CCR and IMM methods.
- EAD is calculated for a netting set (EAD<sub>NS...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488
- pdf chunk_id=bis_bcbs_d488
- pdf:cb9322f1747e] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation
- pdf chunk_id=iosco_iq_margin_2013_consultation

---

### Sample 26: q26

**Question:** What is the role of discount factors in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Discount factors are one of the terms used in the CVA calculation formula.
- CVA reduces the mark-to-market value of a derivative asset by accounting for counterparty credit risk.

Citations...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488
- pdf chunk_id=bis_bcbs_d488
- pdf:cb9322f1747e] [source=corpus/regulatory_seed/docx/en/isda_afme_cva_position_paper
- docx chunk_id=isda_afme_cva_position_paper

---

### Sample 27: q27

**Question:** What is CRR II?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses CRR 3's CVA risk framework and FRTB under Basel III.

Citations: [source=corpus/regulatory_seed/docx/en/isda_afme_frtb_position_paper.docx chunk_id=isda_afme_frtb_posit...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/docx/en/isda_afme_frtb_position_paper
- docx chunk_id=isda_afme_frtb_position_paper
- docx:9260f9409880] [source=corpus/regulatory_seed/docx/en/isda_afme_cva_position_paper
- docx chunk_id=isda_afme_cva_position_paper

---

### Sample 28: q28

**Question:** What is the difference between FRTB and Basel II.5?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB is a comprehensive suite of capital rules under Basel III, finalized in January 2016, addressing shortcomings in Basel II.5.
- FRTB aims to improve the market risk capital framework pos...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:9d9df405ddf4] [source=corpus/regulatory_seed/docx/en/isda_afme_frtb_position_paper
- docx chunk_id=isda_afme_frtb_position_paper

---

### Sample 29: q29

**Question:** Does FRTB increase bank capital costs?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB was not intended to increase banks' capital costs beyond Basel II.5, but industry analysis suggests otherwise.
- It aims to improve market risk capital framework post-2008 and increase ...

**Unsupported Sentences:**
- 1) TLDR
- 5, but industry analysis suggests otherwise
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:9d9df405ddf4] [source=corpus/regulatory_seed/docx/en/isda_afme_frtb_position_paper

---

### Sample 30: q30

**Question:** What is the BCBS?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The BCBS (Basel Committee on Banking Supervision) sets minimum capital requirements for market risk (January 2019, revised February 2019).
- It collaborates with the International Organizati...

**Unsupported Sentences:**
- 1) TLDR
- - It issues consultative documents, such as on Credit Valuation Adjustment risk (November 2019)
- Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2020
- pdf chunk_id=iosco_iq_margin_2020
- pdf:f6aec941f5ed] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation

---

### Sample 31: q31

**Question:** What is Theta in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Theta measures the sensitivity of a derivative's value to the passage of time, also known as time decay.
- It is one of the key Greeks used to assess risk sensitivities in derivatives.

Cita...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:731a8674f78d] [source=corpus/acceptance/greeks_gundersen
- md chunk_id=greeks_gundersen

---

### Sample 32: q32

**Question:** What is Rho in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Rho is the sensitivity of a derivative's value to changes in interest rates.
- It is one of the key Greeks used to measure risk sensitivities in derivatives.

Citations: [source=corpus/Backg...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:731a8674f78d] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457

---

### Sample 33: q33

**Question:** What is Volga?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses vega risk buckets, curvature risk buckets, and their calculation methods in capital requirements.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf ch...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:72a208fab649] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457

---

### Sample 34: q34

**Question:** What is Vanna?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Vanna is a second-order Greek measuring the sensitivity of Delta to changes in implied volatility.
- Vanna equivalently measures the sensitivity of Vega to changes in the underlying price.

...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:c0a440a36ba4] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488
- pdf chunk_id=bis_bcbs_d488

---

### Sample 35: q35

**Question:** What is Charm?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Charm is not explicitly defined in the provided context.
- The context discusses Greeks, which are sensitivities of a derivative value to small changes in risk factors, but Charm is not list...

**Unsupported Sentences:**
- 1) TLDR
- - Charm is not explicitly defined in the provided context
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:c0a440a36ba4] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation

---

### Sample 36: q36

**Question:** What is the difference between implied and historical volatility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Implied volatility reflects the market's expectation of future volatility, derived from option prices and the Black-Scholes model.
- Historical volatility is a backward-looking measure based...

**Unsupported Sentences:**
- TLDR
- Key Facts

---

### Sample 37: q37

**Question:** What is a delta-neutral portfolio?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions delta sensitivities in the context of market risk capital requirements.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d457.pdf:72...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:72a208fab649] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457_note
- pdf chunk_id=bis_bcbs_d457_note

---

### Sample 38: q38

**Question:** What is gamma hedging?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Gamma hedging is not mentioned in the provided context.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d457.pdf:0e40c6a1ef10] [source=corpus/regulatory...

**Unsupported Sentences:**
- 1) TLDR
- - Gamma hedging is not mentioned in the provided context
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:0e40c6a1ef10] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation

---

### Sample 39: q39

**Question:** What is volatility skew?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Volatility skew is not explicitly defined in the provided context.
- The context discusses sensitivity to near-term return volatility and its impact on initial margin frameworks.

Citations:...

**Unsupported Sentences:**
- 1) TLDR
- - Volatility skew is not explicitly defined in the provided context
- Citations: [source=corpus/regulatory_seed/pdf/en/fsb_review_otc_effectiveness_2017
- pdf chunk_id=fsb_review_otc_effectiveness_2017
- pdf:c3d28599e1cb] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457

---

### Sample 40: q40

**Question:** What is volatility smile?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 41: q41

**Question:** What is a risk factor?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- A **risk factor** is an underlying variable (e.g., interest rates, credit spreads, FX rates) used to calculate market risk capital requirements.
- Risk factors are categorized into **risk cl...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:72fb58a38a21] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457

---

### Sample 42: q42

**Question:** What is model risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Model risk relates to regulatory approval of trading desk models for market risk capital calculations.
- Trading desks must document compliance with model requirements as part of approval.

...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:a45d2fc51255] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457

---

### Sample 43: q43

**Question:** What is counterparty credit risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Counterparty credit risk is the risk that the counterparty defaults before final settlement.
- CVA (Credit Valuation Adjustment) adjusts the risk-free value based on counterparty credit qual...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:02a6daa31fa9] [source=corpus/Background
- md chunk_id=Background

---

### Sample 44: q44

**Question:** What is wrong-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Wrong-way risk occurs when exposure to a counterparty increases as the counterparty's credit quality deteriorates.
- An example of wrong-way risk is buying a put option from a bank on the ba...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:bfd07d611b41] [source=corpus/Background
- md chunk_id=Background

---

### Sample 45: q45

**Question:** What is right-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Right-way risk is not explicitly defined in the provided context.
- The context discusses margin requirements for non-centrally-cleared derivatives but does not address right-way risk.

Cita...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation
- pdf chunk_id=iosco_iq_margin_2013_consultation
- pdf:38956266a8fb] [source=corpus/regulatory_seed/pdf/en/cftc_2020_27736_margin_uncleared_swaps
- pdf chunk_id=cftc_2020_27736_margin_uncleared_swaps

---

### Sample 46: q46

**Question:** What is a credit support annex (CSA)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- A CSA (Credit Support Annex) is a legal document supplementing the ISDA Master Agreement that governs collateral terms to mitigate credit risk.
- It defines rules for posting and receiving c...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/Background
- md chunk_id=Background
- md:bbdac6808ba2] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488
- pdf chunk_id=bis_bcbs_d488

---

### Sample 47: q47

**Question:** What is initial margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions "initial margin" only in the title of "Element 5: Treatment of provided initial margin" without further details.

Citations: [source=corpus/regulatory_seed/pdf/en/iosco_...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2020
- pdf chunk_id=iosco_iq_margin_2020
- pdf:08536027d65f] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2020
- pdf chunk_id=iosco_iq_margin_2020

---

### Sample 48: q48

**Question:** What is variation margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Variation margin is the mandatory exchange of funds representing the settlement of running profit/loss of a derivative, with no net liquidity costs.
- It is part of margin requirements for n...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2020
- pdf chunk_id=iosco_iq_margin_2020
- pdf:0945220c1016] [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2020
- pdf chunk_id=iosco_iq_margin_2020

---

### Sample 49: q49

**Question:** What is value at risk (VaR)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Value at risk (VaR) measures the worst expected loss on a portfolio from market movements over a given time horizon and confidence level.
- VaR is used alongside expected shortfall (ES) in r...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:76cbf35975bf] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457

---

### Sample 50: q50

**Question:** What is expected shortfall (ES)?

**Status:** ✅ PASS

**Answer Preview:** Since the context is entirely unrelated to the question, I cannot provide an answer based on it.

Citations: [source=corpus/regulatory_seed/pdf/en/fsb_otc_progress_2017.pdf chunk_id=fsb_otc_progress_2...

**Unsupported Sentences:**
- Since the context is entirely unrelated to the question, I cannot provide an answer based on it
- Citations: [source=corpus/regulatory_seed/pdf/en/fsb_otc_progress_2017
- pdf chunk_id=fsb_otc_progress_2017
- pdf:70516b1fd92c] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457

---

## Recommendations

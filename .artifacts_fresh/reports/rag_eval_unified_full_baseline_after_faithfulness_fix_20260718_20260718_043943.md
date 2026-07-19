# RAG Evaluation Report - unified_full_baseline_after_faithfulness_fix_20260718

**Generated:** 2026-07-18 12:39:43

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Samples | 50 |
| Passed | 33 (66.0%) |
| Failed | 17 (34.0%) |

## Answer Evaluation

| Metric | Value | Threshold |
|--------|-------|-----------|
| citation_coverage | 0.960 | 0.8 |
| faithfulness | 0.874 | 0.75 |
| answer_relevancy | 0.875 | 0.7 |
| sentence_support_rate | 0.874 | - |

## Threshold Gate

- Verdict: fail
- Threshold Failures: 1
- Baseline Regressions: 0

## Sample Details

### Sample 1: q01

**Question:** What is FRTB and why does it matter for market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB stands for Fundamental Review of the Trading Book, a framework to improve the market risk capital framework after 2008.
- It aims to increase risk sensitivity and model risk governance....

---

### Sample 2: q02

**Question:** Explain Delta in the context of derivatives risk.

**Status:** ✅ PASS

**Answer Preview:** 1) **TLDR**
- Delta is the sensitivity of a derivative value to the underlying price level.
- Other related Greeks include Gamma, which is the sensitivity of Delta to the underlying price, and Vanna, ...

---

### Sample 3: q03

**Question:** What is Gamma and how is it different from Delta?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Gamma is the sensitivity of Delta to the underlying price, while Delta is the sensitivity to the underlying price level.
- Delta measures first-order price risk; Gamma measures how Delta its...

**Unsupported Sentences:**
- Delta measures first-order price risk; Gamma measures how Delta itself changes with the underlying price.

---

### Sample 4: q04

**Question:** What is Vega and when is it important?

**Status:** ✅ PASS

**Answer Preview:** 1) **TLDR**
- Vega is defined as the change in the market value of the option as a result of a small amount of change to the implied volatility.
- The instrument’s vega and implied volatility used in ...

**Unsupported Sentences:**
- 1) **TLDR**
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:b93bae6eef8a] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457

---

### Sample 5: q05

**Question:** What is CVA and what risk does it represent?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA stands for Credit Valuation Adjustment, an adjustment to the risk‑free value that increases when counterparty credit quality worsens.
- It represents counterparty risk – the risk that th...

---

### Sample 6: q06

**Question:** What does FRTB stand for?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB stands for Fundamental Review of the Trading Book.
- It is a suite of capital rules developed by the Basel Committee on Banking Supervision as part of Basel III, finalised in January 20...

---

### Sample 7: q07

**Question:** What is the purpose of FRTB?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 8: q08

**Question:** What is Credit Valuation Adjustment?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Credit Valuation Adjustment (CVA) is the price that an investor would pay to hedge the counterparty credit risk of a derivative instrument.
- It reduces the mark to market value of an asset ...

---

### Sample 9: q09

**Question:** When was CVA introduced as a requirement?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 10: q10

**Question:** What is XVA?

**Status:** ❌ FAIL

**Answer Preview:** I'm unable to answer the question because no relevant information was found in the indexed corpus.

**Next actions:**
1. **Refine your query** – Try specifying a particular type of XVA (e.g., CVA, DVA...

---

### Sample 11: q11

**Question:** What is the Basel Committee?

**Status:** ❌ FAIL

**Answer Preview:** I'm unable to answer your question because no relevant information was found in the indexed corpus.

To proceed, consider these actions:
- **Refine your search** with more specific terms (e.g., “Basel...

---

### Sample 12: q12

**Question:** When was FRTB finalized?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 13: q13

**Question:** What is Basel III?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 14: q14

**Question:** What is the difference between trading book and banking book?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 15: q15

**Question:** What is PnL attribution?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- PnL attribution is a common concept used in interviews and systems within the FRTB framework.

Citations: [source=corpus/Background.md chunk_id=Background.md:9d9df405ddf4] [source=corpus/reg...

---

### Sample 16: q16

**Question:** What is backtesting in market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- No usable information on backtesting is present in the context.
- To find a definition, consult the Basel Committee's market risk framework or the specific sections on backtesting within the...

**Unsupported Sentences:**
- 1) TLDR
- No usable information on backtesting is present in the context.
- - To find a definition, consult the Basel Committee's market risk framework or the specific sections on backtesting within the minimum capital requirements for market risk.

---

### Sample 17: q17

**Question:** What is risk factor eligibility?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 18: q18

**Question:** What is DVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- DVA (Debit Valuation Adjustment) is the adjustment to a derivative price due to the institution's own default risk.
- DVA is basically CVA from the counterparty’s perspective; if one party i...

---

### Sample 19: q19

**Question:** What is FVA?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 20: q20

**Question:** What is KVA?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 21: q21

**Question:** What is MVA?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 22: q22

**Question:** What is ColVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CollVA is the value of the optionality embedded in a CSA to post collateral in different currencies.

Citations: [source=corpus/regulatory_seed/md/en/wikipedia_xva.md chunk_id=wikipedia_xva....

---

### Sample 23: q23

**Question:** What is the default probability in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- In CVA, the default probability is the risk neutral probability of counterparty default between times s and t.
- These probabilities can be obtained from the term structure of credit default...

---

### Sample 24: q24

**Question:** What is loss given default (LGD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- For calculating the gross JTD, LGD is set at 100% for equity instruments and non‑senior debt instruments, 75% for senior debt instruments, and 25% for covered bonds.
- When the price of the ...

---

### Sample 25: q25

**Question:** What is exposure at default (EAD)?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 26: q26

**Question:** What is the role of discount factors in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Discount factors are one of the terms included in the formula for calculating CVA.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488.pdf chunk_id=bis_bcbs_d488.pdf:68675529c400...

---

### Sample 27: q27

**Question:** What is CRR II?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CRR II is the Revised Capital Requirements Regulation, through which the Fundamental Review of the Trading Book (FRTB) is being implemented in the EU.
- FRTB is a comprehensive suite of capi...

---

### Sample 28: q28

**Question:** What is the difference between FRTB and Basel II.5?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB aims to address a number of identified shortcomings in the existing Basel II.5 framework.
- Basel II.5 reforms did not address key structural shortcomings in the market risk framework, ...

---

### Sample 29: q29

**Question:** Does FRTB increase bank capital costs?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Yes, the implementation of the FRTB will materially increase capital requirements for banks with market making activities in Europe.
- FRTB was not intended to increase banks' capital costs ...

---

### Sample 30: q30

**Question:** What is the BCBS?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- BCBS is an entity that, together with IOSCO, issues consultative papers on margin requirements for non-centrally-cleared derivatives.
- The BCBS and IOSCO fully expect to benefit from inform...

---

### Sample 31: q31

**Question:** What is Theta in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Theta is the sensitivity of a derivative's value to the passage of time (also known as time decay).

Citations: [source=corpus/Background.md chunk_id=Background.md:222936993a67] [source=corp...

---

### Sample 32: q32

**Question:** What is Rho in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Rho is the sensitivity of a derivative's value to changes in interest rates.
- Rho is one of the key Greeks used to measure risk sensitivities of a derivative.

Citations: [source=corpus/Bac...

---

### Sample 33: q33

**Question:** What is Volga?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Volga is a second-order Greek measuring the sensitivity of Vega to changes in implied volatility (also called vomma).

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chun...

---

### Sample 34: q34

**Question:** What is Vanna?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Vanna is a second-order Greek measuring the sensitivity of Delta to changes in implied volatility, equivalently the sensitivity of Vega to changes in the underlying price.

Citations: [sourc...

---

### Sample 35: q35

**Question:** What is Charm?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Charm is the sensitivity of Delta to the passage of time (also known as delta decay or DdeltaDtime).

Citations: [source=corpus/Background.md chunk_id=Background.md:402e6913648a] [source=cor...

---

### Sample 36: q36

**Question:** What is the difference between implied and historical volatility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Implied volatility is the market's expectation of future volatility, derived from option prices and implied by the Black-Scholes model, while historical volatility is a backward-looking meas...

---

### Sample 37: q37

**Question:** What is a delta-neutral portfolio?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- A delta-neutral portfolio is a portfolio whose total delta is zero, making it insensitive to small changes in the underlying price.
- It is often used by market makers to hedge directional r...

---

### Sample 38: q38

**Question:** What is gamma hedging?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Gamma is defined as the sensitivity of Delta to the underlying price.

Citations: [source=corpus/Background.md chunk_id=Background.md:0e189bafb653] [source=corpus/regulatory_seed/pdf/en/cftc...

---

### Sample 39: q39

**Question:** What is volatility skew?

**Status:** ❌ FAIL

**Answer Preview:** 

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
- The term appears only in the description of a pricing model, which determines the change in an instrument’s value as a function of risk factors.

Citations: [source=corpus/regulatory_seed/pd...

**Unsupported Sentences:**
- The term appears only in the description of a pricing model, which determines the change in an instrument’s value as a function of risk factors.

---

### Sample 42: q42

**Question:** What is model risk?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 43: q43

**Question:** What is counterparty credit risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Counterparty credit risk is the risk that the counterparty defaults before final settlement.
- CVA (Credit Valuation Adjustment) is an adjustment to the risk-free value that increases when c...

**Unsupported Sentences:**
- Right-way risk is the opposite of wrong-way risk; occurs when exposure to a counterparty decreases as the counterparty's credit quality improves.
- Counterparty credit risk drives the need for a Credit Valuation Adjustment (CVA), which adjusts the risk-free value of a trade.
- Managing this risk involves tools like netting sets, CSAs, and awareness of wrong-way and right-way risk, as CVA often interacts with collateral, netting sets, and wrong-way risk.

---

### Sample 44: q44

**Question:** What is wrong-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Wrong-way risk occurs when exposure to a counterparty increases as the counterparty's credit quality deteriorates.
- An example is buying a put option from a bank on the bank's own stock.
- ...

---

### Sample 45: q45

**Question:** What is right-way risk?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 46: q46

**Question:** What is a credit support annex (CSA)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- A Credit Support Annex (CSA) is a legal document that supplements the ISDA Master Agreement, governing the terms for posting and receiving collateral between counterparties to mitigate credi...

---

### Sample 47: q47

**Question:** What is initial margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Initial margin is subject to rigorous and robust dispute resolution procedures between counterparties before a transaction begins.
- The baseline initial margin amount can be calculated usin...

---

### Sample 48: q48

**Question:** What is variation margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Variation margin is a component of the baseline minimum amounts and methodologies for margin requirements for non-centrally-cleared derivatives, mentioned alongside initial margin.
- The BCB...

---

### Sample 49: q49

**Question:** What is value at risk (VaR)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Value at risk (VaR) is a measure of the worst expected loss on a portfolio of instruments resulting from market movements over a given time horizon and a pre-defined confidence level.
- VaR ...

---

### Sample 50: q50

**Question:** What is expected shortfall (ES)?

**Status:** ❌ FAIL

**Answer Preview:** 

---

## Recommendations

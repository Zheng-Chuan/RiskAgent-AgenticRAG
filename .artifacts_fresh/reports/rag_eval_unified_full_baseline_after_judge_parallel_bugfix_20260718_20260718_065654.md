# RAG Evaluation Report - unified_full_baseline_after_judge_parallel_bugfix_20260718

**Generated:** 2026-07-18 14:56:54

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Samples | 50 |
| Passed | 38 (76.0%) |
| Failed | 12 (24.0%) |

## Answer Evaluation

| Metric | Value | Threshold |
|--------|-------|-----------|
| citation_coverage | 0.960 | 0.8 |
| faithfulness | 0.775 | 0.75 |
| answer_relevancy | 0.848 | 0.7 |
| sentence_support_rate | 0.775 | - |

## Threshold Gate

- Verdict: fail
- Threshold Failures: 1
- Baseline Regressions: 0

## Sample Details

### Sample 1: q01

**Question:** What is FRTB and why does it matter for market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB stands for Fundamental Review of the Trading Book, a comprehensive suite of capital rules developed by the Basel Committee on Banking Supervision as part of Basel III, intended to be ap...

---

### Sample 2: q02

**Question:** Explain Delta in the context of derivatives risk.

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Delta is the sensitivity of a derivative's value to the underlying price level.
- Delta is one of the key Greeks, which are sensitivities of a derivative value to small changes in risk facto...

---

### Sample 3: q03

**Question:** What is Gamma and how is it different from Delta?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Gamma is the sensitivity of Delta to the underlying price, whereas Delta is the sensitivity to the underlying price level.
- Gamma is a second-order Greek that measures how Delta changes whe...

**Unsupported Sentences:**
- Gamma is a second-order Greek that measures how Delta changes when the underlying price moves.

---

### Sample 4: q04

**Question:** What is Vega and when is it important?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Vega is defined as the change in the market value of the option as a result of a small amount of change to the implied volatility.
- In the market risk capital framework, option‑level vega r...

---

### Sample 5: q05

**Question:** What is CVA and what risk does it represent?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA stands for Credit Valuation Adjustment and represents counterparty risk, which is the risk that the counterparty defaults before final settlement.
- CVA is an adjustment to the risk-free...

---

### Sample 6: q06

**Question:** What does FRTB stand for?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB stands for Fundamental Review of the Trading Book.
- It is a comprehensive suite of capital rules developed by the Basel Committee on Banking Supervision as part of Basel III, intended ...

---

### Sample 7: q07

**Question:** What is the purpose of FRTB?

**Status:** ✅ PASS

**Answer Preview:** You may find an answer by providing the relevant excerpts from the Basel Committee documentation on the Fundamental Review of the Trading Book.

Citations: [source=corpus/regulatory_seed/pdf/en/iosco_...

**Unsupported Sentences:**
- You may find an answer by providing the relevant excerpts from the Basel Committee documentation on the Fundamental Review of the Trading Book.

---

### Sample 8: q08

**Question:** What is Credit Valuation Adjustment?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Credit Valuation Adjustment (CVA) is the price that an investor would pay to hedge the counterparty credit risk of a derivative instrument.
- CVA also refers to a measure of market risk.
- I...

---

### Sample 9: q09

**Question:** When was CVA introduced as a requirement?

**Status:** ❌ FAIL

**Answer Preview:** I'm unable to answer that question because no relevant information was found in the indexed corpus.

**Next actions:**
1. **Refine your query** – try specifying the full term (e.g., “Credit Valuation ...

---

### Sample 10: q10

**Question:** What is XVA?

**Status:** ✅ PASS

**Answer Preview:** The provided context contains only a Wikipedia page structure with headings like “Context,” “Valuation adjustments,” and “Accounting impact,” along with a repeated bibliography entry for a publication...

---

### Sample 11: q11

**Question:** What is the Basel Committee?

**Status:** ❌ FAIL

**Answer Preview:** I'm unable to answer that question because no relevant information was found in the indexed corpus. This means the documents I have access to do not contain evidence about the Basel Committee.

Here a...

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

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The trading book (TB) boundary defines assets that fall within the capital requirements for market risk (assets held with a trading intent), while the banking book (BB) boundary defines asse...

**Unsupported Sentences:**
- 1) TLDR
- Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457
- pdf chunk_id=bis_bcbs_d457
- pdf:ab3e345c9c1a] [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457_note
- pdf chunk_id=bis_bcbs_d457_note

---

### Sample 15: q15

**Question:** What is PnL attribution?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 16: q16

**Question:** What is backtesting in market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Backtesting involves comparing expected shortfall or value-at-risk measures against actual trading outcomes.
- The internally modelled risk measurement is generally based on a static portfol...

---

### Sample 17: q17

**Question:** What is risk factor eligibility?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts:
- Risk factor eligibility is listed as a common concept in FRTB, alongside trading book vs banking book and backtesting and PnL attribution.

Citations: [source=corpus/Background.md chun...

---

### Sample 18: q18

**Question:** What is DVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- DVA (Debit Valuation Adjustment) is the adjustment (increment) to a derivative price due to the institution's own default risk.
- DVA is basically CVA from the counterparty’s perspective.
- ...

---

### Sample 19: q19

**Question:** What is FVA?

**Status:** ✅ PASS

**Answer Preview:** - Provide the full text of the XVA article, specifically the "Valuation adjustments" section.
- Provide a document or glossary that explicitly defines FVA.

Citations: [source=corpus/regulatory_seed/m...

**Unsupported Sentences:**
- Provide the full text of the XVA article, specifically the "Valuation adjustments" section.
- Provide a document or glossary that explicitly defines FVA.

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

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 23: q23

**Question:** What is the default probability in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Credit valuation adjustment quantifies the cost of counterparty credit risk as the difference between the risk-free portfolio value and the true portfolio value that accounts for the possibi...

**Unsupported Sentences:**
- CVA involves the risk-neutral expectation of the discounted loss, where the default probability is modeled using the counterparty's credit spread or hazard rate derived from credit default swap spreads.
- The calculation integrates expected exposure, loss given default, and default probabilities over the life of the portfolio, typically approximated as a sum over time intervals of the product of discounted expected exposure, default probability, and loss given default.
- Credit valuation adjustment (CVA) is "a risk management tool and an accounting adjustment that quantifies the cost of counterparty credit risk – the risk that a counterparty might default on a derivatives contract."
- The risk-neutral expectation formula for CVA is: CVA = (1-R) ∫₀ᵀ E[discount factor * EPE(t) * PD(t)] where R is the recovery rate, EPE(t) is the expected positive exposure at time t, and PD(t) is the risk-neutral default probability density at time t.
- In practice, the calculation is approximated as: CVA ≈ (1-R) Σᵢ (discount factor at time i) * (expected exposure at time i) * (default probability at time i) * (default probability weight for the i-th time interval).

---

### Sample 24: q24

**Question:** What is loss given default (LGD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- For calculating the gross JTD, loss given default (LGD) is set at 100% for equity instruments and non‑senior debt instruments, 75% for senior debt instruments, and 25% for covered bonds.
- W...

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
- Discount factors are a term in the formula for calculating CVA.
- The formula is written with terms including maturity, discount factors, loss given default, default probability, and exposur...

---

### Sample 27: q27

**Question:** What is CRR II?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CRR II stands for the Revised Capital Requirements Regulation, the EU legislative framework through which the Fundamental Review of the Trading Book (FRTB) is being implemented.

Citations: ...

---

### Sample 28: q28

**Question:** What is the difference between FRTB and Basel II.5?

**Status:** ✅ PASS

**Answer Preview:** 1) **TLDR**
- FRTB is a comprehensive suite of capital rules under Basel III that aims to address a number of identified shortcomings in the existing Basel II.5 framework, and while it was not intende...

---

### Sample 29: q29

**Question:** Does FRTB increase bank capital costs?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Yes, FRTB will materially increase capital requirements for banks with market making activities in Europe.
- FRTB was not intended to increase banks’ capital costs beyond those imposed by Ba...

---

### Sample 30: q30

**Question:** What is the BCBS?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- BCBS can be contacted via e-mail at baselcommittee@bis.org.
- The paper is not a final proposal; BCBS and IOSCO expect to receive comments and QIS responses to inform a final proposal.

Cita...

---

### Sample 31: q31

**Question:** What is Theta in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Theta is the sensitivity of a derivative's value to the passage of time, also known as time decay.

Citations: [source=corpus/Background.md chunk_id=Background.md:222936993a67] [source=corpu...

---

### Sample 32: q32

**Question:** What is Rho in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Rho is the sensitivity of a derivative's value to changes in interest rates.
- Rho is one of the key Greeks used to measure risk sensitivities.

Citations: [source=corpus/Background.md chunk...

---

### Sample 33: q33

**Question:** What is Volga?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Volga is a second-order Greek measuring the sensitivity of Vega to changes in implied volatility (also called vomma).
- Volga is one of several risk sensitivities (Greeks) listed alongside D...

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
- It is one of the second-order Greeks.

Citations: [source=corpus/Background.md chunk_id...

**Unsupported Sentences:**
- It is one of the second-order Greeks.

---

### Sample 36: q36

**Question:** What is the difference between implied and historical volatility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Implied volatility is the market’s expectation of future volatility, derived from option prices and implied by the Black‑Scholes model, while historical volatility is a backward‑looking meas...

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
- The context defines gamma as the sensitivity of delta to the underlying price.

Citations: [source=corpus/Background.md chunk_id=Background.md:0e189bafb653] [source=corpus/regulatory_seed/pd...

---

### Sample 39: q39

**Question:** What is volatility skew?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context only mentions a related concept, volatility smile, as "a pattern where both out-of-the-money and in-the-money options have higher implied v" (text truncated).

Citations: [source...

**Unsupported Sentences:**
- The context only mentions a related concept, volatility smile, as "a pattern where both out-of-the-money and in-the-money options have higher implied v" (text truncated).
- Volatility smile: a pattern where both out-of-the-money and in-the-money options have higher implied v (context cuts off after "implied v").

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
- Risk factor is referenced in the context as an element within a pricing model, which may determine the change in the value of an instrument as a function of risk factors.

Citations: [source...

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
- Counterparty risk is the risk that the counterparty defaults before final settlement.
- CVA is an adjustment to the risk-free value and increases when counterparty credit quality worsens.
- ...

---

### Sample 44: q44

**Question:** What is wrong-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Wrong-way risk is a key counterparty risk concept.
- CVA often interacts with wrong-way risk.

Citations: [source=corpus/Background.md chunk_id=Background.md:dba00c31cda3]

2) Key Facts
- Th...

---

### Sample 45: q45

**Question:** What is right-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Right-way risk is not addressed in the provided context.

Citations: [source=corpus/Background.md chunk_id=Background.md:dba00c31cda3]

---

### Sample 46: q46

**Question:** What is a credit support annex (CSA)?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 47: q47

**Question:** What is initial margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Margin generally is described as “defaulter-pay”, protecting the surviving party after a counterparty default by absorbing losses with the defaulting entity’s collateral.

Citations: [source...

---

### Sample 48: q48

**Question:** What is variation margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Variation margin is a component of margin requirements for non-centrally-cleared derivatives, referenced alongside initial margin in the BCBS-IOSCO framework under Element 3: Baseline minimu...

**Unsupported Sentences:**
- Variation margin is a component of margin requirements for non-centrally-cleared derivatives, referenced alongside initial margin in the BCBS-IOSCO framework under Element 3: Baseline minimum amounts and methodologies for initial and variation margin.
- The BCBS and IOSCO evaluated the calculation of baseline variation margin amounts by reference to systemic risk reduction and promotion of central clearing.
- Element 3 is described as a third key element of the margin requirements, covering the minimum, baseline amount of initial and variation margin required to be collected for a non-centrally-cleared derivative and the methodologies for calculating that baseline amount.
- The BCBS and IOSCO considered the extent to which baseline margin amounts would be sufficient to offset systemic risk from the perspective of systemic risk reduction.
- The baseline amounts for variation margin are evaluated for their contribution to the two underlying benefits of margin requirements: systemic risk reduction and promotion of central clearing.

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

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Expected shortfall (ES) is a risk measure that, to recognise the risk of market illiquidity, prescribes different liquidity horizons for different risk factors.
- ES is compared to value-at-...

---

## Recommendations

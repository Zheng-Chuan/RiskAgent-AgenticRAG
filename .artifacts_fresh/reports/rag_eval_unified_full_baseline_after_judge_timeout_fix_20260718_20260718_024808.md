# RAG Evaluation Report - unified_full_baseline_after_judge_timeout_fix_20260718

**Generated:** 2026-07-18 10:48:08

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
| faithfulness | 0.591 | 0.75 |
| answer_relevancy | 0.865 | 0.7 |
| sentence_support_rate | 0.591 | - |

## Threshold Gate

- Verdict: fail
- Threshold Failures: 2
- Baseline Regressions: 0

## Sample Details

### Sample 1: q01

**Question:** What is FRTB and why does it matter for market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB is the Fundamental Review of the Trading Book, a market risk framework that addresses shortcomings in the existing Basel II.5 framework and, in the EU, is being implemented as binding p...

**Unsupported Sentences:**
- FRTB is the Fundamental Review of the Trading Book, a market risk framework that addresses shortcomings in the existing Basel II.5 framework and, in the EU, is being implemented as binding pillar 1 capital requirements via CRR 3.
- It introduces both a Standardized Approach (SA) and an Internal Model Approach (IMA) for market risk.
- It matters because it converts reporting requirements into binding capital requirements and finalises the trading/banking book boundary, with analysis indicating banks will see significant incr in capital costs.
- In the EU, implementation followed a two-step approach: CRR 22 set reporting requirements for both the FRTB Standardized Approach (SA) and the Internal Model Approach (IMA) and certain elements of the trading and banking book boundary; CRR 3 converts these reporting requirements into pillar 1 capital binding requirements and finalises the trading/ banking book boundary.
- CRR 3 represents a key step in the implementation of FRTB in Europe, and it will be crucial to ensure its calibration and design remains fit and appropriate.

---

### Sample 2: q02

**Question:** Explain Delta in the context of derivatives risk.

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Delta is the sensitivity to the underlying price level.
- Delta is often used by market makers to hedge directional risk.

Citations: [source=corpus/Background.md chunk_id=Background.md:0e18...

**Unsupported Sentences:**
- - Delta is often used by market makers to hedge directional risk.
- - Delta is described as sensitivity to small changes in the underlying price and is often used by market makers to hedge directional risk.
- - Delta is relevant because it is often used by market makers to hedge directional risk.

---

### Sample 3: q03

**Question:** What is Gamma and how is it different from Delta?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Gamma is the sensitivity of Delta to the underlying price, while Delta is the sensitivity of the derivative value to the underlying price level.
- Gamma is a second-order Greek that measures...

---

### Sample 4: q04

**Question:** What is Vega and when is it important?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Vega is defined as the change in the market value of an option as a result of a small amount of change to the implied volatility.
- The option-level vega risk sensitivity is measured by mult...

**Unsupported Sentences:**
- The instrument’s vega and implied volatility used in the calculation must be sourced from pricing models used by the independent risk control unit of the bank.
- The instrument’s vega and implied volatility used in vega sensitivity calculations must be sourced from pricing models used by the independent risk control unit of the bank.
- As specified in the vega risk factor definitions, the implied volatility of the option must be mapped to one or more maturity tenors.

---

### Sample 5: q05

**Question:** What is CVA and what risk does it represent?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA stands for Credit Valuation Adjustment, an adjustment to the risk-free value that represents counterparty risk—the risk that the counterparty defaults before final settlement.
- CVA incr...

---

### Sample 6: q06

**Question:** What does FRTB stand for?

**Status:** ❌ FAIL

**Answer Preview:** I'm unable to answer this question because no relevant information was found in the indexed corpus. The retrieval context is empty.

Here are suggested next steps:

- Search the internal regulatory or...

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
- CVA reduces the mark to market value of an asset...

**Unsupported Sentences:**
- CVA was introduced as a new requirement for fair value accounting during the 2007/08 Global Financial Crisis.
- Market participants started incorporating credit valuation adjustment when calculating the value of over-the-counter derivative instruments.
- The formula for calculating CVA is written with terms including maturity, discount factors, loss given default, default probability, and exposure over time.

---

### Sample 9: q09

**Question:** When was CVA introduced as a requirement?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 10: q10

**Question:** What is XVA?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 11: q11

**Question:** What is the Basel Committee?

**Status:** ❌ FAIL

**Answer Preview:** I'm unable to answer your question because no relevant information was found in the indexed corpus. Here are a few next steps you can take:

- **Rephrase your query** – Try using different keywords or...

---

### Sample 12: q12

**Question:** When was FRTB finalized?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not specify when FRTB was finalized.
- A paper on the CRR3 proposal related to FRTB is dated May 2022.
- CRR3 is described as a key step in the implementation of FR...

**Unsupported Sentences:**
- The provided context does not specify when FRTB was finalized.
- A paper on the CRR3 proposal related to FRTB is dated May 2022.
- CRR3 is described as a key step in the implementation of FRTB in Europe.
- A paper titled "CRR3 – Fundamental Review of the Trading Book (FRTB)" is dated May 2022.
- In the EU, FRTB implementation has followed a two-step approach, with CRR2 setting out reporting requirements and CRR3 converting these into pillar 1 capital binding requirements and finalising the trading/banking book boundary.

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
- The trading book contains assets held with a trading intent and subject to market risk capital requirements, while the banking book contains assets subject to credit risk capital requirement...

**Unsupported Sentences:**
- Industry concerns include operational requirements, complexity, potential rigidity in instrument designation, and downside effects in funding and liquidity activities resulting from the revised boundary.
- The industry remains concerned about the operational requirements, complexity and potential rigidity in instrument designation, as well as downside effects in funding and liquidity activities resulting from the revised trading/banking book boundary.

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
- Backtesting in market risk is a process that compares risk measures and trading outcomes for profit and loss (P&L) attribution test and backtesting, based on the sensitivity of a static port...

**Unsupported Sentences:**
- Backtesting in market risk is a process that compares risk measures and trading outcomes for profit and loss (P&L) attribution test and backtesting, based on the sensitivity of a static portfolio to instantaneous price shocks.
- It uses end‑of‑day trading positions input into the risk measurement model to assess the possible change in the value of the static portfolio due to price and rate movements over the assumed holding period.
- Trading desk‑level backtesting arises because internally modelled risk measurement is generally based on the sensitivity of a static portfolio to instantaneous price shocks.
- End‑of‑day trading positions are input into the risk measurement model, which assesses the possible change in the value of this static portfolio due to price and rate movements over the assumed holding period.

---

### Sample 17: q17

**Question:** What is risk factor eligibility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define risk factor eligibility; it only lists the term as a common concept used in interviews and systems related to the Fundamental Review of the Trading Book ...

---

### Sample 18: q18

**Question:** What is DVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- DVA (Debit Valuation Adjustment) is the adjustment (increment) to a derivative price due to the institution's own default risk.
- DVA is basically CVA from the counterparty’s perspective; if...

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
- Default probability is one of the terms used in calculating CVA, along with maturity, discount factors, loss given default, and exposure over time.

Citations: [source=corpus/acceptance/cva_...

---

### Sample 24: q24

**Question:** What is loss given default (LGD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Loss given default is a term included in the formula for calculating Credit Valuation Adjustment (CVA).
- The CVA formula also includes maturity, discount factors, default probability, and e...

**Unsupported Sentences:**
- Loss given default is a term included in the formula for calculating Credit Valuation Adjustment (CVA).
- The CVA formula also includes maturity, discount factors, default probability, and exposure over time.
- The formula for calculating CVA is written with terms including maturity, discount factors, loss given default, default probability, and exposure over time.

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

Citations: [source=corpus/regulatory_seed/md/en/wikipedia_xva.md chunk_id=wikipedia_xva.md:ea4adbefdb58] [...

---

### Sample 27: q27

**Question:** What is CRR II?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CRR II is the Revised Capital Requirements Regulation, which is the EU vehicle for implementing the Fundamental Review of the Trading Book (FRTB).

Citations: [source=corpus/acceptance/frtb_...

**Unsupported Sentences:**
- CRR II is the Revised Capital Requirements Regulation, which is the EU vehicle for implementing the Fundamental Review of the Trading Book (FRTB).
- In the EU, FRTB is being implemented as part of the Revised Capital Requirements Regulation (CRR II), and related Banking Package proposals.

---

### Sample 28: q28

**Question:** What is the difference between FRTB and Basel II.5?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB aims to address a number of identified shortcomings in the existing Basel II.5 framework.
- While FRTB was not intended to increase banks’ capital costs beyond those imposed by Basel II...

**Unsupported Sentences:**
- The Fundamental Review of the Trading Book (FRTB) is a comprehensive suite of capital rules developed by the Basel Committee on Banking Supervision (BCBS) as part of Basel III, intended to be applied to banks’ wholesale trading activities.
- FRTB was finalised in January 2016 as the Minimum Capital Requirements for Market Risk.

---

### Sample 29: q29

**Question:** Does FRTB increase bank capital costs?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Yes, the implementation of FRTB will materially increase capital requirements for banks with market making activities in Europe, even though FRTB was not intended to increase banks' capital ...

**Unsupported Sentences:**
- The increase is noted in the context of European market making activities, while elsewhere the Commission is trying to promote market making.

---

### Sample 30: q30

**Question:** What is the BCBS?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- BCBS is an entity that, together with IOSCO, is developing a framework for margin requirements on non-centrally-cleared derivatives.
- The BCBS can be contacted by e-mail at baselcommittee@b...

**Unsupported Sentences:**
- BCBS is an entity that, together with IOSCO, is developing a framework for margin requirements on non-centrally-cleared derivatives.
- The BCBS and IOSCO jointly issued a consultative paper on margin requirements for non-centrally-cleared derivatives.
- The paper does not propose a specific implementation process and does not represent a final proposal; the BCBS and IOSCO expect to benefit from comment and QIS processes.

---

### Sample 31: q31

**Question:** What is Theta in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) Theta is the sensitivity of a derivative's value to the passage of time (also known as time decay).
2) Theta is one of the key Greeks that measure sensitivities of a derivative value to small chang...

---

### Sample 32: q32

**Question:** What is Rho in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Rho is the sensitivity of a derivative's value to changes in interest rates.

Citations: [source=corpus/Background.md chunk_id=Background.md:222936993a67] [source=corpus/regulatory_seed/pdf/...

---

### Sample 33: q33

**Question:** What is Volga?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Volga is a second-order Greek measuring the sensitivity of Vega to changes in implied volatility (also called vomma).

Citations: [source=corpus/Background.md chunk_id=Background.md:22293699...

**Unsupported Sentences:**
- Volga is a second-order Greek measuring the sensitivity of Vega to changes in implied volatility (also called vomma).
- Volga is a second-order Greek.
- It measures the sensitivity of Vega to changes in implied volatility.
- It is also called vomma.

---

### Sample 34: q34

**Question:** What is Vanna?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Vanna is a second-order Greek measuring the sensitivity of Delta to changes in implied volatility, equivalently the sensitivity of Vega to changes in the underlying price.
- It is one of the...

**Unsupported Sentences:**
- Vanna is a second-order Greek measuring the sensitivity of Delta to changes in implied volatility, equivalently the sensitivity of Vega to changes in the underlying price.
- It is one of the risk sensitivities (Greeks) for derivatives.
- Vanna: second-order Greek measuring the sensitivity of Delta to changes in implied volatility, equivalently the sensitivity of Vega to changes in the underlying price.

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

**Unsupported Sentences:**
- A delta-neutral portfolio is a portfolio whose total delta is zero, making it insensitive to small changes in the underlying price.
- It is often used by market makers to hedge directional risk.
- A delta-neutral portfolio has a total delta of zero.
- It is insensitive to small changes in the underlying price.
- Market makers often use it to hedge directional risk.

---

### Sample 38: q38

**Question:** What is gamma hedging?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define gamma hedging, so I cannot answer the question.
- Gamma is defined as the sensitivity of Delta to the underlying price, but no hedging concept is describ...

**Unsupported Sentences:**
- TLDR - The provided context does not define gamma hedging, so I cannot answer the question.
- Gamma is defined as the sensitivity of Delta to the underlying price, but no hedging concept is described.
- Key Facts - Gamma: sensitivity of Delta to the underlying price.
- Why it matters - No information on why gamma hedging matters is present in the context.

---

### Sample 39: q39

**Question:** What is volatility skew?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 40: q40

**Question:** What is volatility smile?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- A volatility smile is a pattern where both out-of-the-money and in-the-money options have higher implied v.

Citations: [source=corpus/Background.md chunk_id=Background.md:402e6913648a] [sou...

---

### Sample 41: q41

**Question:** What is a risk factor?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 42: q42

**Question:** What is model risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define model risk.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d457.pdf:1a94a59ca3d1]

2) Key Facts
- No facts about m...

**Unsupported Sentences:**
- Next action: Consult a source that explicitly defines model risk, such as a risk management glossary or a regulatory document on model risk management.

---

### Sample 43: q43

**Question:** What is counterparty credit risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Counterparty credit risk is the risk that the counterparty defaults before final settlement.
- A Credit Valuation Adjustment (CVA) is an adjustment to the risk-free value that increases when...

**Unsupported Sentences:**
- Key related concepts include netting set, CSA, wrong-way risk, and right-way risk.
- A netting set is a group of trades with a single counterparty that can be netted under a single master agreement (e.g., ISDA Master Agreement), reducing overall exposure by offsetting positive and negative mark-to-market values.
- A CSA (Credit Support Annex) is a legal document that supplements the ISDA Master Agreement, governing the terms for posting and receiving collateral between counterparties to mitigate credit risk.
- Wrong-way risk occurs when exposure to a counterparty increases as the counterparty's credit quality deteriorates; for example, buying a put option from a bank on the bank's own stock.
- Right-way risk is the opposite of wrong-way risk; occurs when exposure to a counterparty decreases as the counterparty's credit quality improves.

---

### Sample 44: q44

**Question:** What is wrong-way risk?

**Status:** ❌ FAIL

**Answer Preview:** 

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
- A CSA (Credit Support Annex) is a legal document that supplements the ISDA Master Agreement, governing the terms for posting and receiving collateral between counterparties to mitigate credi...

**Unsupported Sentences:**
- A CSA (Credit Support Annex) is a legal document that supplements the ISDA Master Agreement, governing the terms for posting and receiving collateral between counterparties to mitigate credit risk.
- CSA is a legal document that supplements the ISDA Master Agreement.
- It governs the terms for posting and receiving collateral between counterparties.
- Its purpose is to mitigate credit risk.
- The context lists CSA among key counterparty risk concepts, indicating its role in managing credit exposure within a netting set framework.

---

### Sample 47: q47

**Question:** What is initial margin?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 48: q48

**Question:** What is variation margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Variation margin represents the settlement of the running profit/loss of a derivative.
- It has no net liquidity costs because it is a transfer of resources from one party to another.
- The ...

---

### Sample 49: q49

**Question:** What is value at risk (VaR)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define value at risk (VaR).
- No facts about VaR are available in the given text.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=b...

---

### Sample 50: q50

**Question:** What is expected shortfall (ES)?

**Status:** ❌ FAIL

**Answer Preview:** 

---

## Recommendations

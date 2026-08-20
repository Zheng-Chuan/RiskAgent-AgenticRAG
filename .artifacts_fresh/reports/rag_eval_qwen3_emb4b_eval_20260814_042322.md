# RAG Evaluation Report - qwen3_emb4b_eval

**Generated:** 2026-08-14 04:23:22

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
| faithfulness | 0.517 | 0.75 |
| answer_relevancy | 0.905 | 0.7 |
| sentence_support_rate | 0.517 | - |

## Threshold Gate

- Verdict: fail
- Threshold Failures: 2
- Baseline Regressions: 0

## Sample Details

### Sample 1: q01

**Question:** What is FRTB and why does it matter for market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB (Fundamental Review of the Trading Book) is a market risk capital framework introduced to improve risk sensitivity and governance post-2008.
- It distinguishes between trading book and ...

---

### Sample 2: q02

**Question:** Explain Delta in the context of derivatives risk.

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Delta in derivatives risk is referenced in the context of **delta risk capital requirement**.
- The steps for calculating delta risk capital requirement are outlined in **Graph A1**.

Citati...

**Unsupported Sentences:**
- (Context does not explicitly discuss relevance; omit this section.)

---

### Sample 3: q03

**Question:** What is Gamma and how is it different from Delta?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions "delta risk buckets, risk weights and correlations" but provides no further details.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcb...

**Unsupported Sentences:**
- The context mentions "delta risk buckets, risk weights and correlations" but provides no further details.
- The context references "delta risk buckets, risk weights and correlations" without elaboration.

---

### Sample 4: q04

**Question:** What is Vega and when is it important?

**Status:** ✅ PASS

**Answer Preview:** Next steps:
- Provide context that explicitly defines Vega and its relevance.
- Clarify if the question pertains to options trading, risk metrics, or another financial concept.

Citations: [source=cor...

**Unsupported Sentences:**
- Next steps:
- Provide context that explicitly defines Vega and its relevance.
- Clarify if the question pertains to options trading, risk metrics, or another financial concept.

---

### Sample 5: q05

**Question:** What is CVA and what risk does it represent?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- **CVA (Credit Valuation Adjustment)** is the price paid to hedge counterparty credit risk in derivatives, reducing an asset's mark-to-market value by the CVA amount.
- CVA became a fair valu...

**Unsupported Sentences:**
- CVA became a fair value accounting requirement during the 2007/08 Global Financial Crisis.
- Its calculation involves maturity, discount factors, loss given default, default probability, and exposure over time.
- CVA addresses counterparty credit risk, a critical concern in derivative valuations, especially after the 2007/08 crisis highlighted systemic vulnerabilities.

---

### Sample 6: q06

**Question:** What does FRTB stand for?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB stands for **Fundamental Review of the Trading Book**.
- It is a **Basel III capital rules suite** for banks' wholesale trading activities.
- Finalized in **January 2016** as the **Mini...

---

### Sample 7: q07

**Question:** What is the purpose of FRTB?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB's purpose is to improve the market risk capital framework post-2008.
- It aims to increase risk sensitivity and model risk governance.
- In Europe, CRR 3 implements FRTB by converting r...

---

### Sample 8: q08

**Question:** What is Credit Valuation Adjustment?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Credit Valuation Adjustment (CVA) is the price paid to hedge counterparty credit risk in derivatives.
- CVA reduces the mark-to-market value of an asset by its calculated amount.
- It became...

**Unsupported Sentences:**
- It ensures derivatives are valued more accurately by incorporating counterparty risk, improving financial stability post-crisis.

---

### Sample 9: q09

**Question:** When was CVA introduced as a requirement?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA was introduced as a requirement for fair value accounting **during the 2007/08 Global Financial Crisis**.
- It was adopted to account for counterparty credit risk in over-the-counter der...

**Unsupported Sentences:**
- - It was adopted to account for counterparty credit risk in over-the-counter derivative valuations.
- - CVA is the price paid to hedge counterparty credit risk in derivatives.
- - It reduces the mark-to-market value of an asset by the CVA amount.
- - The CVA formula includes maturity, discount factors, loss given default, default probability, and exposure over time.
- - The context states CVA was introduced to address counterparty credit risk in derivatives during a period of financial instability, improving fair value accounting.

---

### Sample 10: q10

**Question:** What is XVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The title "The Long and Short of It: An Overview of XVA" suggests XVA is a financial topic, but no details are given.

Citations: [source=corpus/regulatory_seed/md/en/wikipedia_xva.md chunk_...

**Unsupported Sentences:**
- The context includes a title referencing XVA but provides no further information about it.
- Not applicable (context does not discuss relevance of XVA).

---

### Sample 11: q11

**Question:** What is the Basel Committee?

**Status:** ✅ PASS

**Answer Preview:** - Provide context that explicitly mentions the Basel Committee, its purpose, or its functions.
- Clarify if the question refers to a specific aspect of the Basel Committee (e.g., regulations, risk fra...

**Unsupported Sentences:**
- - Provide context that explicitly mentions the Basel Committee, its purpose, or its functions.

---

### Sample 12: q12

**Question:** When was FRTB finalized?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context provides dates for other final rules related to margin requirements for uncleared swaps (e.g., January 5, 2021, and September 23, 2020).

Citations: [source=corpus/regulatory_see...

**Unsupported Sentences:**
- The context provides dates for other final rules related to margin requirements for uncleared swaps (e.g., January 5, 2021, and September 23, 2020).
- A final rule regarding margin requirements for uncleared swaps was published on **01/05/2021** (86 FR 229).
- Another final rule on the same topic was published on **9/23/2020** (85 FR 59702).

---

### Sample 13: q13

**Question:** What is Basel III?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Basel III includes amendments to the market risk framework, such as adjustments for FX curvature risk and "base currency" approaches.
- The framework involves both a standardized approach an...

**Unsupported Sentences:**
- The framework involves both a standardized approach and an internal models approach for calculating capital requirements.

---

### Sample 14: q14

**Question:** What is the difference between trading book and banking book?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB distinguishes between trading book and banking book as part of its market risk capital framework.
- The context mentions trading book vs banking book as a common concept in FRTB but doe...

**Unsupported Sentences:**
- The context mentions trading book vs banking book as a common concept in FRTB but does not define their differences.
- FRTB is part of Basel III, finalized in January 2016 as the Minimum Capital Requirements for Market Risk.
- It addresses shortcomings in Basel II.5 and applies to banks' wholesale trading activities.

---

### Sample 15: q15

**Question:** What is PnL attribution?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- PnL attribution is a common concept used in FRTB (Fundamental Review of the Trading Book) interviews and systems.
- FRTB aims to improve market risk capital framework post-2008, including ri...

**Unsupported Sentences:**
- PnL attribution is a common concept used in FRTB (Fundamental Review of the Trading Book) interviews and systems.
- FRTB aims to improve market risk capital framework post-2008, including risk sensitivity and model risk governance.

---

### Sample 16: q16

**Question:** What is backtesting in market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions minimum capital requirements for market risk and delta risk buckets but does not link them to backtesting.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d45...

**Unsupported Sentences:**
- The context mentions minimum capital requirements for market risk and delta risk buckets but does not link them to backtesting.
- The context defines delta risk buckets, risk weights, and correlations on page 37.
- The context discusses minimum capital requirements for market risk in the introduction and contents.

---

### Sample 17: q17

**Question:** What is risk factor eligibility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Risk factor eligibility is a common concept used in FRTB interviews and systems.
- FRTB aims to improve market risk capital framework post-2008 and increase risk sensitivity.

Citations: [so...

**Unsupported Sentences:**
- Risk factor eligibility is a common concept used in FRTB interviews and systems.
- FRTB aims to improve market risk capital framework post-2008 and increase risk sensitivity.
- FRTB stands for Fundamental Review of the Trading Book.
- It was finalized in January 2016 as the Minimum Capital Requirements for Market Risk under Basel III.
- FRTB addresses shortcomings in the Basel II.5 framework for banks' wholesale trading activities.

---

### Sample 18: q18

**Question:** What is DVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses Credit Valuation Adjustment (CVA) but does not mention DVA.

Citations: [source=corpus/regulatory_seed/md/en/wikipedia_xva.md chunk_id=wikipedia_xva.md:e7cb1cf8fc74] [s...

**Unsupported Sentences:**
- The context discusses Credit Valuation Adjustment (CVA) but does not mention DVA.
- The context references "Credit valuation adjustment" (CVA) but does not define or discuss DVA.
- Not applicable (context does not address DVA or its relevance).

---

### Sample 19: q19

**Question:** What is FVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FVA (Funding Valuation Adjustment) accounts for funding costs or benefits due to differences between a bank's funding rate and collateral rates, especially for trades without a full Credit S...

**Unsupported Sentences:**
- - It arises from variation margin discrepancies between the bank's treasury funding rate and clearing house collateral rates.
- 3) Why it matters
- Ensures accurate pricing by incorporating funding risks not covered by CSAs, avoiding mispricing in uncollateralized or partially collateralized trades.

---

### Sample 20: q20

**Question:** What is KVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses minimum capital requirements for market risk and regulatory book boundaries.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d457....

**Unsupported Sentences:**
- The context discusses minimum capital requirements for market risk and regulatory book boundaries.
- The context covers "Minimum capital requirements for market risk."
- It includes sections on the "Boundary between the banking book and the trading book," "Scope of the trading book," and "Standards for assigning instruments to the regulatory books."

---

### Sample 21: q21

**Question:** What is MVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses internal risk transfers and capital requirements but does not link them to MVA.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d4...

**Unsupported Sentences:**
- The context discusses internal risk transfers and capital requirements but does not link them to MVA.
- The context covers minimum capital requirements for market risk (9).
- Not applicable (context does not discuss MVA or its relevance).

---

### Sample 22: q22

**Question:** What is ColVA?

**Status:** ✅ PASS

**Answer Preview:** Next steps:
- Verify if "ColVA" is referenced in additional context not provided here.
- Clarify if the term is an abbreviation or acronym for a specific financial concept.
- Provide supplementary con...

**Unsupported Sentences:**
- Verify if "ColVA" is referenced in additional context not provided here.
- Clarify if the term is an abbreviation or acronym for a specific financial concept.
- Provide supplementary context that explicitly defines or discusses "ColVA."

---

### Sample 23: q23

**Question:** What is the default probability in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Default probability is a term in the CVA formula but its specific value or calculation is not provided in the context.
- CVA adjusts the value of derivatives to account for counterparty cred...

**Unsupported Sentences:**
- Default probability is a term in the CVA formula but its specific value or calculation is not provided in the context.
- CVA adjusts the value of derivatives to account for counterparty credit risk.
- CVA ensures derivatives are valued fairly by accounting for the risk of counterparty default.

---

### Sample 24: q24

**Question:** What is loss given default (LGD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Loss given default (LGD) is a term used in the formula for calculating Credit Valuation Adjustment (CVA).
- CVA adjusts the fair value of derivatives to account for counterparty credit risk....

**Unsupported Sentences:**
- Loss given default (LGD) is a term used in the formula for calculating Credit Valuation Adjustment (CVA).
- CVA adjusts the fair value of derivatives to account for counterparty credit risk.

---

### Sample 25: q25

**Question:** What is exposure at default (EAD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Exposure at default (EAD) is not explicitly defined in the provided context.

Citations: [source=corpus/regulatory_seed/pdf/en/cftc_2020_27736_margin_uncleared_swaps.pdf chunk_id=cftc_2020_2...

**Unsupported Sentences:**
- Exposure at default (EAD) is not explicitly defined in the provided context.
- The context mentions "exposure over time" but does not define or elaborate on exposure at default (EAD).
- Not discussed in the context.

---

### Sample 26: q26

**Question:** What is the role of discount factors in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Discount factors are explicitly listed as a term in the CVA calculation formula.
- CVA adjusts the mark-to-market value of derivatives to account for counterparty credit risk.

Citations: [s...

**Unsupported Sentences:**
- CVA became a fair value accounting requirement after the 2007/08 Global Financial Crisis to better reflect credit risk in derivative valuations.
- CVA is the price paid to hedge counterparty credit risk in derivatives.

---

### Sample 27: q27

**Question:** What is CRR II?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CRR II refers to the Revised Capital Requirements Regulation, mentioned alongside Banking Package proposals.

Citations: [source=corpus/acceptance/frtb_icma.md chunk_id=frtb_icma.md:c249bb36...

**Unsupported Sentences:**
- - (No explicit relevance discussed in the provided context.)

---

### Sample 28: q28

**Question:** What is the difference between FRTB and Basel II.5?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions FRTB implementation in the EU and margin requirements for derivatives but does not compare it to Basel II.5.

Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_m...

**Unsupported Sentences:**
- The context mentions FRTB implementation in the EU and margin requirements for derivatives but does not compare it to Basel II.5.
- FRTB implementation in the European Union is discussed.
- Margin requirements for non-centrally cleared derivatives are mentioned, including zero initial margin for transactions with zero counterparty risk.

---

### Sample 29: q29

**Question:** Does FRTB increase bank capital costs?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions potential liquidity impacts and market function effects from regulatory requirements.

Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2013_consultation...

**Unsupported Sentences:**
- The BCBS and IOSCO propose treating branches as part of the same legal entity as their headquarters in cross-border transactions.
- Conflicts may arise if jurisdictions do not uniformly adopt margin requirements, leading to regulatory inconsistencies.
- Regulatory inconsistencies could complicate compliance for banks operating across jurisdictions.

---

### Sample 30: q30

**Question:** What is the BCBS?

**Status:** ✅ PASS

**Answer Preview:** Next steps:
- Provide context that explicitly mentions BCBS or its functions.
- Clarify if you are asking about a specific aspect of BCBS (e.g., regulations, risk frameworks).

Citations: [source=corp...

**Unsupported Sentences:**
- Next steps:
- Provide context that explicitly mentions BCBS or its functions.
- Clarify if you are asking about a specific aspect of BCBS (e.g., regulations, risk frameworks).

---

### Sample 31: q31

**Question:** What is Theta in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Theta is listed as one of the Greeks in position fields, alongside delta, gamma, and vega.

Citations: [source=corpus/BusinessObjects.md chunk_id=BusinessObjects.md:8a59cafcbad1] [source=cor...

**Unsupported Sentences:**
- Greeks are part of position tracking, which is essential for managing trading/hedging strategies and risk-weighted assets.
- Position fields track metrics like quantity/notional, price/pv, and greeks.

---

### Sample 32: q32

**Question:** What is Rho in Greeks?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 33: q33

**Question:** What is Volga?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- No numerical or qualitative details about Volga are provided.

2) Key Facts
- The context discusses minimum capital requirements for market risk, proxy mapping, and external validation of in...

**Unsupported Sentences:**
- No numerical or qualitative details about Volga are provided.
- The context discusses minimum capital requirements for market risk, proxy mapping, and external validation of internal models.

---

### Sample 34: q34

**Question:** What is Vanna?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- No facts about Vanna are explicitly stated in the provided context.

Citations: [source=corpus/regulatory_seed/pdf/en/cftc_2020_27736_margin_uncleared_swaps.pdf chunk_id=cftc_2020_27736...

**Unsupported Sentences:**
- No facts about Vanna are explicitly stated in the provided context.
- Not applicable.

---

### Sample 35: q35

**Question:** What is Charm?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- No facts about "Charm" are explicitly stated in the provided context.

Citations: [source=corpus/regulatory_seed/pdf/en/cftc_2020_27736_margin_uncleared_swaps.pdf chunk_id=cftc_2020_277...

**Unsupported Sentences:**
- No facts about "Charm" are explicitly stated in the provided context.
- Not applicable.

---

### Sample 36: q36

**Question:** What is the difference between implied and historical volatility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- **Implied volatility** is the market's expectation of future volatility, derived from option prices and implied by the Black-Scholes model.
- **Historical volatility** is a backward-looking ...

**Unsupported Sentences:**
- - **Implied volatility** is the market's expectation of future volatility, derived from option prices and implied by the Black-Scholes model.
- - **Historical volatility** is a backward-looking measure based on past price movements of the underlying asset.

---

### Sample 37: q37

**Question:** What is a delta-neutral portfolio?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The context only repeats the phrase "definition of delta risk buckets, risk weights and correlations" with a page reference of "37".

Citations: [source=corpus/regulatory_seed/pdf/en/bi...

**Unsupported Sentences:**
- 2) Key Facts
- The context only repeats the phrase "definition of delta risk buckets, risk weights and correlations" with a page reference of "37".

---

### Sample 38: q38

**Question:** What is gamma hedging?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Gamma hedging involves managing the sensitivity of Delta to changes in the underlying asset's price.
- It is a second-order risk management technique focused on Delta's responsiveness to pri...

**Unsupported Sentences:**
- It is a second-order risk management technique focused on Delta's responsiveness to price movements.
- Gamma hedging helps stabilize Delta, which is critical for maintaining balanced exposure to the underlying asset's price movements.

---

### Sample 39: q39

**Question:** What is volatility skew?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Volatility skew is not explicitly defined in the provided context.
- The context discusses related concepts like implied volatility and volatility smile but does not address skew.

Citations...

**Unsupported Sentences:**
- Volatility skew is not explicitly defined in the provided context.
- The context discusses related concepts like implied volatility and volatility smile but does not address skew.
- Implied volatility is the market's expectation of future volatility, derived from option prices.
- Volatility smile is a pattern where both out-of-the-money and in-the-money options have higher implied volatility.

---

### Sample 40: q40

**Question:** What is volatility smile?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- **Volatility smile** is a pattern where both out-of-the-money and in-the-money options have higher implied volatility.
- It reflects market expectations of future volatility derived from opt...

**Unsupported Sentences:**
- It reflects market expectations of future volatility derived from option prices.
- Implied volatility is the market's expectation of future volatility, derived from option prices and implied by the Black-Scholes model.

---

### Sample 41: q41

**Question:** What is a risk factor?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions "delta risk buckets, risk weights and correlations" but does not link them to risk factors.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=...

**Unsupported Sentences:**
- The context mentions "delta risk buckets, risk weights and correlations" but does not link them to risk factors.
- The context references "delta risk buckets, risk weights and correlations" on page 37.
- The context discusses "Minimum capital requirements for market risk" but does not define risk factors.

---

### Sample 42: q42

**Question:** What is model risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context focuses on minimum capital requirements for market risk and regulatory book boundaries.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d457...

**Unsupported Sentences:**
- The context focuses on minimum capital requirements for market risk and regulatory book boundaries.
- The context discusses "minimum capital requirements for market risk."
- It covers the "boundary between the banking book and the trading book."

---

### Sample 43: q43

**Question:** What is counterparty credit risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Counterparty credit risk is the risk that the counterparty defaults before final settlement.
- CVA (Credit Valuation Adjustment) adjusts the risk-free value based on counterparty credit qual...

---

### Sample 44: q44

**Question:** What is wrong-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Wrong-way risk occurs when exposure to a counterparty increases as the counterparty's credit quality deteriorates.
- An example is buying a put option from a bank on the bank's own stock.

C...

**Unsupported Sentences:**
- Wrong-way risk complicates CVA (Credit Valuation Adjustment) calculations by introducing scenarios where exposure and credit risk move unfavorably in tandem.

---

### Sample 45: q45

**Question:** What is right-way risk?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The provided context discusses minimum capital requirements for market risk.
- It covers topics like the boundary between the banking book and trading book, scope of the trading book, a...

**Unsupported Sentences:**
- The provided context discusses minimum capital requirements for market risk.
- It covers topics like the boundary between the banking book and trading book, scope of the trading book, and supervisory powers.
- No explicit reference to "right-way risk" is made.
- Not applicable (context does not address relevance).

---

### Sample 46: q46

**Question:** What is a credit support annex (CSA)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- A CSA is a legal document supplementing the ISDA Master Agreement that governs collateral terms to mitigate credit risk.
- It defines rules for posting and receiving collateral between count...

**Unsupported Sentences:**
- The context links CSAs to counterparty risk mitigation, though no further explicit rationale is provided.

---

### Sample 47: q47

**Question:** What is initial margin?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The context mentions "TC’s margin requirements with the BCBS/IOSCO Framework" but does not define initial margin.
- References to the Dodd-Frank Act and G20 Summit discuss regulatory st...

**Unsupported Sentences:**
- The context mentions "TC’s margin requirements with the BCBS/IOSCO Framework" but does not define initial margin.
- References to the Dodd-Frank Act and G20 Summit discuss regulatory standards but do not address initial margin.
- Not addressed in the context.

---

### Sample 48: q48

**Question:** What is variation margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Variation margin is not explicitly defined in the provided context.
- The context discusses margin requirements for non-centrally cleared derivatives but does not specify variation margin.

...

**Unsupported Sentences:**
- Variation margin is not explicitly defined in the provided context.
- The context discusses margin requirements for non-centrally cleared derivatives but does not specify variation margin.
- Margin requirements for non-centrally cleared derivatives are mentioned as a "significant policy change."
- Initial margin requirements are highlighted as not currently applied to many transactions.
- The context emphasizes cross-border coordination among regulators to address inconsistencies in margin requirements.

---

### Sample 49: q49

**Question:** What is value at risk (VaR)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Value at Risk (VaR) is not explicitly defined in the provided context.
- The context discusses minimum capital requirements for market risk and regulatory book boundaries.

Citations: [sourc...

**Unsupported Sentences:**
- Value at Risk (VaR) is not explicitly defined in the provided context.
- The context discusses minimum capital requirements for market risk and regulatory book boundaries.
- The context mentions "Minimum capital requirements for market risk."
- It references "RBC25 Boundary between the banking book and the trading book."
- Topics include "Scope of the trading book" and "Standards for assigning instruments to the regulatory books."

---

### Sample 50: q50

**Question:** What is expected shortfall (ES)?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The provided context discusses minimum capital requirements for market risk, the boundary between banking and trading books, and supervisory standards.
- No information about expected s...

**Unsupported Sentences:**
- The provided context discusses minimum capital requirements for market risk, the boundary between banking and trading books, and supervisory standards.
- No information about expected shortfall (ES) is included.
- Not applicable (context does not address ES or its relevance).
- (Strictly omitted unsupported aspects.)

---

## Recommendations

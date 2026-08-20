# RAG Evaluation Report - cosine_fix_eval

**Generated:** 2026-08-14 05:15:29

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
| faithfulness | 0.521 | 0.75 |
| answer_relevancy | 0.840 | 0.7 |
| sentence_support_rate | 0.521 | - |

## Threshold Gate

- Verdict: fail
- Threshold Failures: 2
- Baseline Regressions: 0

## Sample Details

### Sample 1: q01

**Question:** What is FRTB and why does it matter for market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB (Fundamental Review of the Trading Book) is a regulatory framework to improve market risk capital standards post-2008.
- It aims to increase risk sensitivity and strengthen model risk g...

---

### Sample 2: q02

**Question:** Explain Delta in the context of derivatives risk.

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Delta in derivatives risk is discussed in the context of **delta risk capital requirement**.
- The steps for calculating delta risk capital requirement are outlined in **Graph A1**.

Citatio...

---

### Sample 3: q03

**Question:** What is Gamma and how is it different from Delta?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context only references "delta risk buckets, risk weights and correlations" on page 37.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d457.pdf:c28...

**Unsupported Sentences:**
- The context only references "delta risk buckets, risk weights and correlations" on page 37.
- The context mentions "delta risk buckets, risk weights and correlations" but provides no further details.
- (Omitted; context does not discuss relevance.)

---

### Sample 4: q04

**Question:** What is Vega and when is it important?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 5: q05

**Question:** What is CVA and what risk does it represent?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- **CVA (Credit Valuation Adjustment)** is the price paid to hedge counterparty credit risk in derivatives, reducing an asset's mark-to-market value by the CVA amount.
- CVA became a fair valu...

**Unsupported Sentences:**
- Calculation involves terms: **maturity, discount factors, loss given default, default probability, and exposure over time**.
- Post-crisis reforms mandated CVA to improve transparency in **over-the-counter derivatives** markets.

---

### Sample 6: q06

**Question:** What does FRTB stand for?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB stands for Fundamental Review of the Trading Book.
- It is a Basel III capital rules framework for banks' wholesale trading activities.

Citations: [source=corpus/Background.md chunk_id...

**Unsupported Sentences:**
- Developed by the Basel Committee on Banking Supervision (BCBS) as part of Basel III.
- Finalized in January 2016 as the Minimum Capital Requirements for Market Risk.

---

### Sample 7: q07

**Question:** What is the purpose of FRTB?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB's purpose is to **improve market risk capital framework after 2008** and **increase risk sensitivity and model risk governance**.
- It finalizes **trading/banking book boundary** and co...

---

### Sample 8: q08

**Question:** What is Credit Valuation Adjustment?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Credit Valuation Adjustment (CVA) is the price paid to hedge counterparty credit risk in derivatives, reducing an asset's mark-to-market value by the CVA amount.
- CVA became a fair value ac...

**Unsupported Sentences:**
- Ensures accurate derivative valuation by accounting for counterparty default risk.
- Regulatory and accounting alignment remains a focus (e.g., BCBS standards).

---

### Sample 9: q09

**Question:** When was CVA introduced as a requirement?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA was introduced as a requirement for fair value accounting during the 2007/08 Global Financial Crisis.
- It was adopted to account for counterparty credit risk in over-the-counter derivat...

**Unsupported Sentences:**
- It reduces the mark-to-market value of an asset by the CVA amount.
- The context implies CVA addressed gaps in risk measurement exposed by the financial crisis, particularly for OTC derivatives.
- It was adopted to account for counterparty credit risk in over-the-counter derivative valuations.

---

### Sample 10: q10

**Question:** What is XVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- **XVA** is a collective term for a family of valuation adjustments, including **CVA** (Credit Valuation Adjustment).
- **CVA** applies to interest rate derivatives, foreign exchange derivati...

**Unsupported Sentences:**
- **Regulatory CVA** excludes the bank’s own default and follows accounting constraints.
- **CVA** impacts capital requirements (**Basel III**) and financial reporting (**IFRS 13**), necessitating dedicated risk management.

---

### Sample 11: q11

**Question:** What is the Basel Committee?

**Status:** ✅ PASS

**Answer Preview:** - Request context that explicitly mentions the Basel Committee, its purpose, or its functions.
- Clarify if the question pertains to banking regulation, risk management frameworks, or another specific...

**Unsupported Sentences:**
- - Request context that explicitly mentions the Basel Committee, its purpose, or its functions.
- - Clarify if the question pertains to banking regulation, risk management frameworks, or another specific aspect of the Basel Committee's work.
- (No TLDR, Key Facts, or "Why it matters" sections are included, as the context lacks relevant information.)

---

### Sample 12: q12

**Question:** When was FRTB finalized?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context provides dates for final rules related to margin requirements for uncleared swaps, but not FRTB.

Citations: [source=corpus/regulatory_seed/html/en/cftc_capital_margin_page.html ...

**Unsupported Sentences:**
- The context provides dates for final rules related to margin requirements for uncleared swaps, but not FRTB.
- Final Rule: 86 FR 229, effective February 4, 2021, relates to margin requirements for uncleared swaps.
- Another Final Rule: 85 FR 71246, dated September 23, 2020, also pertains to margin requirements for uncleared swaps.

---

### Sample 13: q13

**Question:** What is Basel III?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Basel III includes amendments to the market risk framework, such as adjustments for FX curvature risk and "base currency" approaches.
- The framework involves both a standardized approach an...

**Unsupported Sentences:**
- The framework involves both a standardized approach and an internal models approach for calculating capital requirements.
- The amendments aim to reduce FX risk capital requirements compared to prior analyses.

---

### Sample 14: q14

**Question:** What is the difference between trading book and banking book?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions "Trading book vs banking book" as a common concept in FRTB but does not define their differences.
- FRTB focuses on improving market risk capital frameworks for trading ...

**Unsupported Sentences:**
- The context mentions "Trading book vs banking book" as a common concept in FRTB but does not define their differences.
- FRTB focuses on improving market risk capital frameworks for trading activities.
- "Trading book vs banking book" is listed as a common concept but lacks further detail.

---

### Sample 15: q15

**Question:** What is PnL attribution?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- PnL attribution is mentioned as a common concept in FRTB (Fundamental Review of the Trading Book) for market risk capital frameworks.
- It is grouped with backtesting and risk factor eligibi...

**Unsupported Sentences:**
- - It is grouped with backtesting and risk factor eligibility under FRTB's high-level goals.
- - PnL attribution is listed among concepts like trading book vs. banking book and backtesting.
- - The context associates PnL attribution with FRTB's goals of increasing risk sensitivity and model risk governance.
- (No further details on PnL attribution's mechanics or examples are provided in the context.)

---

### Sample 16: q16

**Question:** What is backtesting in market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Backtesting in market risk is not explicitly defined in the provided context.
- The context discusses FRTB (Fundamental Review of the Trading Book) and its implementation in Europe under CRR...

**Unsupported Sentences:**
- Backtesting in market risk is not explicitly defined in the provided context.
- The context discusses FRTB (Fundamental Review of the Trading Book) and its implementation in Europe under CRR3.

---

### Sample 17: q17

**Question:** What is risk factor eligibility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Risk factor eligibility is a common concept used in FRTB (Fundamental Review of the Trading Book) interviews and systems.
- FRTB aims to improve market risk capital framework post-2008 and i...

**Unsupported Sentences:**
- Risk factor eligibility is a common concept used in FRTB (Fundamental Review of the Trading Book) interviews and systems.
- FRTB aims to improve market risk capital framework post-2008 and increase risk sensitivity.
- Risk factor eligibility is listed among common FRTB concepts used in interviews and systems.

---

### Sample 18: q18

**Question:** What is DVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- **DVA (Debit Valuation Adjustment)** is an increment to a derivative price due to the institution's own default risk.
- It is analogous to CVA (Credit Valuation Adjustment).

Citations: [sou...

**Unsupported Sentences:**
- It is analogous to CVA (Credit Valuation Adjustment).
- DVA is analogous to **CVA**.

---

### Sample 19: q19

**Question:** What is FVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses other valuation adjustments like CVA (Credit Valuation Adjustment) and DVA (Debit Valuation Adjustment).

Citations: [source=corpus/regulatory_seed/md/en/wikipedia_xva....

**Unsupported Sentences:**
- The context discusses other valuation adjustments like CVA (Credit Valuation Adjustment) and DVA (Debit Valuation Adjustment).
- The context lists XVA adjustments, including DVA (Debit Valuation Adjustment), which is analogous to CVA.
- The context highlights the importance of careful aggregation of valuation adjustments (e.g., CVA, DVA) to avoid double counting.

---

### Sample 20: q20

**Question:** What is KVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context discusses minimum capital requirements for market risk and regulatory book boundaries.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_b...

**Unsupported Sentences:**
- The provided context discusses minimum capital requirements for market risk and regulatory book boundaries.
- The context covers "Minimum capital requirements for market risk."
- It includes sections on the "Boundary between the banking book and the trading book," "Scope of the trading book," and "Standards for assigning instruments to the regulatory books."

---

### Sample 21: q21

**Question:** What is MVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- No key facts or relevance are discussed in the provided context.

Citations: [source=corpus/regulatory_seed/pdf/en/fsb_otc_progress_2017.pdf chunk_id=fsb_otc_progress_2017.pdf:b09b709d9bf5]
...

**Unsupported Sentences:**
- No key facts or relevance are discussed in the provided context.
- None available in the context.
- Not addressed in the context.

---

### Sample 22: q22

**Question:** What is ColVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses internal risk transfers and regulatory capital requirements for trading desks.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d45...

**Unsupported Sentences:**
- The context discusses internal risk transfers and regulatory capital requirements for trading desks.
- Internal risk transfers between trading desks within the scope of market risk capital requirements (including FX risk and commodities risk in the banking book) generally receive regulatory capital recognition.
- Internal risk transfers between the internal risk transfer desk and other trading desks only receive regulatory capital recognition if constraints in [RBC25.25] to [RBC25.27] are fulfilled.

---

### Sample 23: q23

**Question:** What is the default probability in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The default probability is a term in the CVA calculation formula.
- CVA adjusts the value of derivatives to account for counterparty credit risk.

Citations: [source=corpus/acceptance/cva_cf...

**Unsupported Sentences:**
- The default probability is a term in the CVA calculation formula.
- CVA adjusts the value of derivatives to account for counterparty credit risk.
- CVA is the price paid to hedge counterparty credit risk in derivatives.

---

### Sample 24: q24

**Question:** What is loss given default (LGD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Loss given default (LGD) is a term used in the formula for calculating Credit Valuation Adjustment (CVA).
- CVA adjusts the fair value of derivatives to account for counterparty credit risk....

**Unsupported Sentences:**
- Loss given default (LGD) is a term used in the formula for calculating Credit Valuation Adjustment (CVA).

---

### Sample 25: q25

**Question:** What is exposure at default (EAD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Exposure at default (EAD) is not explicitly defined in the provided context.
- The context mentions "exposure over time" but does not link it to EAD.

Citations: [source=corpus/acceptance/cv...

**Unsupported Sentences:**
- Exposure at default (EAD) is not explicitly defined in the provided context.
- The context references "exposure over time" but does not define or explain exposure at default (EAD).
- Not discussed in the context.

---

### Sample 26: q26

**Question:** What is the role of discount factors in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Discount factors are one of the terms in the CVA calculation formula.
- CVA adjusts the mark-to-market value of derivatives to account for counterparty credit risk.

Citations: [source=corpu...

**Unsupported Sentences:**
- CVA was introduced as a fair value accounting requirement during the 2007/08 Global Financial Crisis.
- CVA pricing helps investors hedge counterparty credit risk in derivative instruments.
- It ensures fair valuation by incorporating credit risk into over-the-counter derivatives.

---

### Sample 27: q27

**Question:** What is CRR II?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CRR II refers to the Revised Capital Requirements Regulation, part of the Banking Package proposals.
- It is mentioned alongside the Fundamental Review of the Trading Book (FRTB) but no furt...

**Unsupported Sentences:**
- It is mentioned alongside the Fundamental Review of the Trading Book (FRTB) but no further details are provided.
- The context links it to FRTB but does not elaborate on their relationship.

---

### Sample 28: q28

**Question:** What is the difference between FRTB and Basel II.5?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB is a Basel III framework finalized in January 2016 to address shortcomings in Basel II.5 for banks' wholesale trading activities.
- FRTB was not intended to increase capital costs beyon...

**Unsupported Sentences:**
- The context implies FRTB was designed to enhance the regulatory framework for market risk, though it does not explicitly state the specific shortcomings addressed.
- FRTB was not intended to increase capital costs beyond Basel II.5 but aimed to improve the existing framework.

---

### Sample 29: q29

**Question:** Does FRTB increase bank capital costs?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- It mentions potential conflicts in margin requirements between jurisdictions that could impact liquidity and market function.

Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margi...

**Unsupported Sentences:**
- It mentions potential conflicts in margin requirements between jurisdictions that could impact liquidity and market function.
- Branches are treated as part of the same legal entity as their headquarters in cross-border transactions (e.g., a US branch of a French bank is treated as a French legal entity).
- Regulatory inconsistencies may create operational challenges for banks operating across borders, though the direct effect on capital costs is not discussed.

---

### Sample 30: q30

**Question:** What is the BCBS?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The BCBS (Basel Committee on Banking Supervision) is referenced in a footnote as the source for revisions to the securitisation framework in December 2014, 2016, and 2018.
- The BCBS documen...

**Unsupported Sentences:**
- The BCBS documents are hosted at www.bis.org/bcbs/.
- The documents are accessible at:
- www.bis.org/bcbs/publ/d303.htm
- www.bis.org/bcbs/publ/d374.pdf
- www.bis.org/bcbs/publ/d442.pdf

---

### Sample 31: q31

**Question:** What is Theta in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Theta measures the sensitivity of a derivative's value to the passage of time, also known as time decay.

Citations: [source=corpus/Background.md chunk_id=Background.md:222936993a67] [source...

---

### Sample 32: q32

**Question:** What is Rho in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Rho is the sensitivity of a derivative's value to changes in interest rates.

Citations: [source=corpus/Background.md chunk_id=Background.md:222936993a67] [source=corpus/regulatory_seed/pdf/...

**Unsupported Sentences:**
- - (Context does not explicitly discuss relevance; omitted.)

---

### Sample 33: q33

**Question:** What is Volga?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- No relevant details about financial derivatives or risk concepts related to Volga are present.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d457.pdf:...

**Unsupported Sentences:**
- No relevant details about financial derivatives or risk concepts related to Volga are present.
- The context discusses minimum capital requirements for market risk, proxy mapping, and external validation of internal models.
- Not applicable (context does not address Volga).

---

### Sample 34: q34

**Question:** What is Vanna?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- No facts about Vanna are present in the context.

3) Why it matters
- Not applicable (no relevant context).

(Note: The context snippets provided are either incomplete or unrelated to t...

**Unsupported Sentences:**
- 2) Key Facts
- No facts about Vanna are present in the context.
- 3) Why it matters
- Not applicable (no relevant context).
- (Note: The context snippets provided are either incomplete or unrelated to the question about Vanna. No usable information is available.)
- Citations: [source=corpus/regulatory_seed/md/en/wikipedia_cva.md chunk_id=wikipedia_cva.md:4fe3da32efea]

---

### Sample 35: q35

**Question:** What is Charm?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- No financial derivatives or risk concepts related to "Charm" are discussed.

2) Key Facts
- The context includes references to derivatives market practices, jurisdictional arbitrage, and cap...

**Unsupported Sentences:**
- No financial derivatives or risk concepts related to "Charm" are discussed.
- The context includes references to derivatives market practices, jurisdictional arbitrage, and capital optimization but does not address "Charm."
- Not applicable (no discussion of "Charm" in context).

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
- The context repeatedly mentions "delta risk buckets, risk weights and correlations" but provides no further details.
- The number "37" appears in all context entries without explanation...

**Unsupported Sentences:**
- The context repeatedly mentions "delta risk buckets, risk weights and correlations" but provides no further details.
- The number "37" appears in all context entries without explanation.

---

### Sample 38: q38

**Question:** What is gamma hedging?

**Status:** ✅ PASS

**Answer Preview:** Since the context is entirely unrelated to the question, no further details can be extracted.

**Unsupported Sentences:**
- Since the context is entirely unrelated to the question, no further details can be extracted.

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
- Implied volatility is the market's expectation of future volatility, derived from option prices and implied by the Black-Scholes model.
- Volatility smile is a pattern where both out-of-the-money and in-the-money options have higher implied volatility.

---

### Sample 40: q40

**Question:** What is volatility smile?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- **Volatility smile** is a pattern where both out-of-the-money and in-the-money options have higher implied volatility.
- It relates to market expectations of future volatility, derived from ...

**Unsupported Sentences:**
- It relates to market expectations of future volatility, derived from option prices.
- Implied volatility reflects the market's expectation of future volatility, derived from option prices and the Black-Scholes model.

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
- Standards for assigning instruments to regulatory books and supervisory powers are mentioned.
- Not addressed in the context.

---

### Sample 43: q43

**Question:** What is counterparty credit risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Counterparty credit risk is the risk that the counterparty defaults before final settlement.
- It involves adjustments like CVA, which increases as counterparty credit quality worsens.
- Mit...

---

### Sample 44: q44

**Question:** What is wrong-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Wrong-way risk occurs when exposure to a counterparty increases as the counterparty's credit quality deteriorates.
- An example is buying a put option from a bank on the bank's own stock.

C...

**Unsupported Sentences:**
- Wrong-way risk interacts with CVA (Credit Valuation Adjustment), which adjusts the risk-free value based on counterparty credit quality.
- It is a critical consideration in managing counterparty risk alongside collateral, netting sets, and right-way risk.

---

### Sample 45: q45

**Question:** What is right-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context outlines minimum capital requirements for market risk and regulatory book boundaries.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d457.p...

**Unsupported Sentences:**
- The context outlines minimum capital requirements for market risk and regulatory book boundaries.
- The context covers "Minimum capital requirements for market risk."
- It includes sections on the "Boundary between the banking book and the trading book," "Scope of the trading book," and "Standards for assigning instruments to the regulatory books."

---

### Sample 46: q46

**Question:** What is a credit support annex (CSA)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- A **Credit Support Annex (CSA)** is a legal document supplementing the ISDA Master Agreement.
- It governs collateral posting and receiving terms to mitigate credit risk between counterparti...

---

### Sample 47: q47

**Question:** What is initial margin?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The context references margin requirements under the BCBS/IOSCO Framework.
- It cites the Dodd-Frank Act and G20 commitments on regulatory standards.
- No explicit details about initial...

**Unsupported Sentences:**
- The context references margin requirements under the BCBS/IOSCO Framework.
- It cites the Dodd-Frank Act and G20 commitments on regulatory standards.
- No explicit details about initial margin are included.
- Not discussed in the context.

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
- Initial margin requirements are highlighted as a significant policy change for market participants.

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
- The document outlines "Minimum capital requirements for market risk."
- It includes sections on the boundary between banking and trading books, scope of the trading book, and standards for assigning instruments to regulatory books.
- Supervisory powers and documentation of instrument designation are also mentioned.

---

### Sample 50: q50

**Question:** What is expected shortfall (ES)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Expected shortfall (ES) is not defined or mentioned in the provided context.

2) Key Facts
- The context discusses minimum capital requirements for market risk, regulatory boundaries between...

**Unsupported Sentences:**
- Expected shortfall (ES) is not defined or mentioned in the provided context.
- The context discusses minimum capital requirements for market risk, regulatory boundaries between banking and trading books, and supervisory standards.
- No explicit reference to expected shortfall (ES) exists in the provided text.
- Not applicable (context does not address ES or its relevance).

---

## Recommendations

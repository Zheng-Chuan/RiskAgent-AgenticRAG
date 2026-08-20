Defaulted container "api" out of: api, wait-milvus (init), wait-redis (init)
# RAG Evaluation Report - k8s_fix_verify

**Generated:** 2026-08-11 16:00:09

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
| faithfulness | 0.623 | 0.75 |
| answer_relevancy | 0.893 | 0.7 |
| sentence_support_rate | 0.623 | - |

## Threshold Gate

- Verdict: fail
- Threshold Failures: 2
- Baseline Regressions: 9

## Sample Details

### Sample 1: q01

**Question:** What is FRTB and why does it matter for market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB (Fundamental Review of the Trading Book) is a market risk capital framework introduced after 2008 to improve risk sensitivity and model governance.
- It distinguishes between trading bo...

---

### Sample 2: q02

**Question:** Explain Delta in the context of derivatives risk.

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Delta is defined within the context of market risk capital requirements for derivatives.
- The context references delta sensitivities in relation to risk weights and buckets.

Citations: [so...

**Unsupported Sentences:**
- - The context references delta sensitivities in relation to risk weights and buckets.
- - Delta is associated with risk weights and buckets in market risk calculations.
- - Delta sensitivities are defined alongside vega sensitivities.

---

### Sample 3: q03

**Question:** What is Gamma and how is it different from Delta?

**Status:** ❌ FAIL

**Answer Preview:** 

---

### Sample 4: q04

**Question:** What is Vega and when is it important?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Vega is defined in the context of delta and vega sensitivities under minimum capital requirements for market risk.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_i...

**Unsupported Sentences:**
- Vega is mentioned alongside delta sensitivities in the definition of minimum capital requirements for market risk.

---

### Sample 5: q05

**Question:** What is CVA and what risk does it represent?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA (Credit Valuation Adjustment) is the price paid to hedge counterparty credit risk in derivatives.
- CVA reduces the mark-to-market value of an asset by its CVA value.
- CVA was introduce...

**Unsupported Sentences:**
- - CVA (Credit Valuation Adjustment) is the price paid to hedge counterparty credit risk in derivatives.
- - CVA reduces the mark-to-market value of an asset by its CVA value.
- - CVA was introduced as a requirement for fair value accounting.

---

### Sample 6: q06

**Question:** What does FRTB stand for?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB stands for **Fundamental Review of the Trading Book**.
- It is a set of capital rules developed by the **Basel Committee on Banking Supervision (BCBS)** under **Basel III**.

Citations:...

---

### Sample 7: q07

**Question:** What is the purpose of FRTB?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The purpose of FRTB is to address shortcomings in the Basel II.5 framework for banks' wholesale trading activities.
- FRTB aims to mitigate systemic risk and improve transparency in derivati...

**Unsupported Sentences:**
- FRTB aims to mitigate systemic risk and improve transparency in derivatives markets.
- FRTB is designed to enhance the stability and transparency of financial markets by addressing weaknesses in previous regulatory frameworks.

---

### Sample 8: q08

**Question:** What is Credit Valuation Adjustment?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Credit Valuation Adjustment (CVA) is the price paid to hedge counterparty credit risk in a derivative instrument.
- CVA reduces the mark-to-market value of an asset by its calculated value.
...

---

### Sample 9: q09

**Question:** When was CVA introduced as a requirement?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA was introduced as a requirement for fair value accounting during the 2007/08 Global Financial Crisis.
- Market participants began incorporating CVA when valuing over-the-counter derivati...

**Unsupported Sentences:**
- CVA is the price paid to hedge counterparty credit risk in derivatives.
- It reduces the mark-to-market value of an asset by the CVA value.
- CVA addresses counterparty credit risk in derivative valuations, a critical concern highlighted by the financial crisis.

---

### Sample 10: q10

**Question:** What is XVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- XVA is not explicitly defined in the provided context.
- The context discusses Credit Valuation Adjustment (CVA) as a measure of counterparty credit risk in derivative instruments.

Citation...

**Unsupported Sentences:**
- XVA is not explicitly defined in the provided context.
- The context discusses Credit Valuation Adjustment (CVA) as a measure of counterparty credit risk in derivative instruments.
- CVA is relevant for accurately valuing derivative instruments by accounting for counterparty credit risk.

---

### Sample 11: q11

**Question:** What is the Basel Committee?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The Basel Committee on Banking Supervision sets minimum capital requirements for market risk (January 2019, revised February 2019).
- It collaborates with the International Organization of S...

**Unsupported Sentences:**
- The Basel Committee on Banking Supervision sets minimum capital requirements for market risk (January 2019, revised February 2019).
- A consultative document on Credit Valuation Adjustment risk was issued in November 2019, with comments due by 25 February 2020.

---

### Sample 12: q12

**Question:** When was FRTB finalized?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB was finalized in **January 2016** as the *Minimum Capital Requirements for Market Risk*.
- A revised version of the standard was published in **January 2019 (rev. February 2019)**.

Cit...

**Unsupported Sentences:**
- - A revised version of the standard was published in **January 2019 (rev. February 2019)**.
- - A revised version was issued in **January 2019 (rev. February 2019)** and integrated into the consolidated Basel Framework.
- - FRTB addresses shortcomings in the Basel II.5 framework for banks' wholesale trading activities.

---

### Sample 13: q13

**Question:** What is Basel III?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Basel III is a set of regulatory standards finalized in December 2017 to address shortcomings of the pre-crisis regulatory framework.
- It aims to provide a resilient banking system that sup...

---

### Sample 14: q14

**Question:** What is the difference between trading book and banking book?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The trading book includes instruments subject to market risk capital requirements, while the banking book includes instruments subject to credit risk capital requirements.
- The boundary bet...

---

### Sample 15: q15

**Question:** What is PnL attribution?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- PnL attribution is a common concept used in FRTB (Fundamental Review of the Trading Book) for market risk frameworks.
- It is mentioned alongside backtesting and risk factor eligibility in F...

---

### Sample 16: q16

**Question:** What is backtesting in market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Backtesting in market risk involves testing capital requirements using hypothetical and actual daily P&L outcomes to assess risk measure accuracy.
- Banks must perform backtesting at both ba...

---

### Sample 17: q17

**Question:** What is risk factor eligibility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Risk factor eligibility is a common concept in FRTB (Fundamental Review of the Trading Book).
- FRTB aims to improve market risk capital framework post-2008 and enhance risk sensitivity.

Ci...

**Unsupported Sentences:**
- Risk factor eligibility is a common concept in FRTB (Fundamental Review of the Trading Book).
- FRTB aims to improve market risk capital framework post-2008 and enhance risk sensitivity.
- Risk factor eligibility is listed among the common concepts used in FRTB interviews and systems.

---

### Sample 18: q18

**Question:** What is DVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- It discusses Credit Valuation Adjustment (CVA) as a pricing mechanism for hedging counterparty credit risk in derivatives.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d488.pdf...

**Unsupported Sentences:**
- It discusses Credit Valuation Adjustment (CVA) as a pricing mechanism for hedging counterparty credit risk in derivatives.
- Credit Valuation Adjustment (CVA) is the price paid to hedge counterparty credit risk in derivatives.
- CVA reduces the mark-to-market value of an asset by its CVA value.
- CVA became a fair value accounting requirement during the 2007/08 Global Financial Crisis.
- CVA incorporation in derivative valuation addresses counterparty credit risk, improving financial stability post-crisis.

---

### Sample 19: q19

**Question:** What is FVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- It focuses on Credit Valuation Adjustment (CVA) risk and its regulatory revisions under Basel III.

Citations: [source=corpus/regulatory_seed/docx/en/isda_afme_cva_position_paper.docx chunk_...

**Unsupported Sentences:**
- It focuses on Credit Valuation Adjustment (CVA) risk and its regulatory revisions under Basel III.
- The Basel Committee on Banking Supervision (BCBS) published targeted revisions to the CVA framework in July 2020.
- The revisions aim to align the CVA requirement more closely with the Counterparty Credit Risk (CCR) framework.
- A proposed calibration adjustment for the SA-CVA involves changing the multiplier *mCVA* from 1.25 to a range of [1 to 1.25].
- The revisions incentivize banks to centrally clear over-the-counter derivatives.

---

### Sample 20: q20

**Question:** What is KVA?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The context describes the Financial Stability Board's (FSB) role in coordinating international financial policies.
- The FSB's mandate is outlined in its Charter, governing policymaking...

**Unsupported Sentences:**
- The context describes the Financial Stability Board's (FSB) role in coordinating international financial policies.
- The FSB's mandate is outlined in its Charter, governing policymaking and related activities.
- FSB decisions are non-binding and do not create legal rights.

---

### Sample 21: q21

**Question:** What is MVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses swaps, prudential regulators, and margin requirements but does not address MVA.

Citations: [source=corpus/regulatory_seed/pdf/en/fsb_otc_progress_2017.pdf chunk_id=fsb...

**Unsupported Sentences:**
- The context discusses swaps, prudential regulators, and margin requirements but does not address MVA.
- The context defines swaps to include interest rate swaps, commodity swaps, credit default swaps, and currency swaps.
- Prudential regulators include the Board of Governors of the Federal Reserve System, the Office of the Comptroller of the Currency, the Federal Deposit Insurance Corporation, the Farm Credit Administration, and the Federal Housing Finance Agency.

---

### Sample 22: q22

**Question:** What is ColVA?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The context discusses margin requirements for non-centrally-cleared derivatives (NCCDs).
- It mentions BCBS-IOSCO's evaluation of universal two-way margin implementation.
- The CFTC iss...

**Unsupported Sentences:**
- The context discusses margin requirements for non-centrally-cleared derivatives (NCCDs).
- It mentions BCBS-IOSCO's evaluation of universal two-way margin implementation.
- The CFTC issued a comparability determination for NCCD margin requirements in September 2016.

---

### Sample 23: q23

**Question:** What is the default probability in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Default probability is a term in the CVA calculation formula.
- CVA incorporates counterparty credit risk into derivative valuation.
- CVA became a fair value accounting requirement during t...

**Unsupported Sentences:**
- Default probability is a term in the CVA calculation formula.
- CVA incorporates counterparty credit risk into derivative valuation.
- CVA ensures derivatives are valued more accurately by reflecting the risk of counterparty default.

---

### Sample 24: q24

**Question:** What is loss given default (LGD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Loss given default (LGD) refers to the probability-weighted loss on the default of a counterparty.
- Margin requirements are designed to mitigate counterparty credit risk by providing access...

**Unsupported Sentences:**
- Margin requirements are designed to mitigate counterparty credit risk by providing accessible and rapidly liquidatable protection.
- Margin must be accessible at the time of need and liquidated rapidly during financial stress at a predictable price.
- Margin offers enhanced protection against counterparty credit risk when effectively implemented.

---

### Sample 25: q25

**Question:** What is exposure at default (EAD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Exposure at default (EAD) is a measure of the potential exposure at the time of default.
- EAD is converted from Effective expected positive exposure (EEPE) using a multiplier α in both SA-C...

**Unsupported Sentences:**
- EAD is a critical component in assessing credit risk, as it quantifies the potential loss exposure at the time of default.
- EAD is calculated using Effective expected positive exposure (EEPE) in both SA-CCR and IMM methods.
- A multiplier α is used to convert EEPE to EAD.

---

### Sample 26: q26

**Question:** What is the role of discount factors in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Discount factors are one of the terms used in the CVA calculation formula.
- CVA reduces the mark-to-market value of an asset by accounting for counterparty credit risk.

Citations: [source=...

**Unsupported Sentences:**
- CVA reduces the mark-to-market value of an asset by accounting for counterparty credit risk.
- CVA was introduced as a fair value accounting requirement during the 2007/08 Global Financial Crisis.
- CVA ensures proper valuation of over-the-counter derivatives by incorporating credit risk.

---

### Sample 27: q27

**Question:** What is CRR II?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses CRR 3 revisions related to Credit Valuation Adjustment (CVA) risk and the FRTB under Basel III.

Citations: [source=corpus/regulatory_seed/docx/en/isda_afme_cva_positio...

**Unsupported Sentences:**
- The context discusses CRR 3 revisions related to Credit Valuation Adjustment (CVA) risk and the FRTB under Basel III.
- In July 2020, the BCBS published targeted revisions to the CVA framework as part of Basel III.
- The FRTB is a set of capital rules finalized in January 2016 under Basel III for banks' trading activities.
- The CVA revisions aim to address market risk in transactions involving counterparties.
- The FRTB seeks to improve capital requirements for market risk in trading activities.

---

### Sample 28: q28

**Question:** What is the difference between FRTB and Basel II.5?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB aims to improve the market risk capital framework post-2008 and increase risk sensitivity.
- Basel II.5 introduced enhanced capital requirements for trading book exposures and increment...

**Unsupported Sentences:**
- TLDR
- Key Facts

---

### Sample 29: q29

**Question:** Does FRTB increase bank capital costs?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB was not intended to increase banks' capital costs beyond those imposed by Basel II.5.
- FRTB aims to improve the market risk capital framework and increase risk sensitivity.

Citations:...

**Unsupported Sentences:**
- FRTB enhances the market risk capital framework to ensure better risk management and governance post-2008 financial crisis.
- FRTB is a suite of capital rules developed by the Basel Committee on Banking Supervision (BCBS) as part of Basel III.

---

### Sample 30: q30

**Question:** What is the BCBS?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The BCBS is the Basel Committee on Banking Supervision.
- It sets standards like minimum capital requirements for market risk.
- It collaborates with bodies like the International Organizati...

---

### Sample 31: q31

**Question:** What is Theta in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Theta measures the sensitivity of a derivative's value to the passage of time, also called time decay.
- It is one of the key Greeks used to assess risk sensitivities in derivatives.

Citati...

---

### Sample 32: q32

**Question:** What is Rho in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Rho is the sensitivity of a derivative's value to changes in interest rates.
- It is one of the key Greeks used to measure risk sensitivities in derivatives.

Citations: [source=corpus/Backg...

---

### Sample 33: q33

**Question:** What is Volga?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Volga is a second-order Greek that measures the sensitivity of Vega to changes in implied volatility.
- Volga is also referred to as vomma.

Citations: [source=corpus/Background.md chunk_id=...

---

### Sample 34: q34

**Question:** What is Vanna?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The context discusses trading desk definitions, regulatory approvals, and swap definitions but does not address Vanna.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pd...

**Unsupported Sentences:**
- The context discusses trading desk definitions, regulatory approvals, and swap definitions but does not address Vanna.
- Not applicable (context does not discuss Vanna or its relevance).

---

### Sample 35: q35

**Question:** What is Charm?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The provided context discusses electronic trading, interest rate derivatives, and Credit Valuation Adjustment (CVA) risk but does not reference "Charm."

Citations: [source=corpus/regul...

**Unsupported Sentences:**
- The provided context discusses electronic trading, interest rate derivatives, and Credit Valuation Adjustment (CVA) risk but does not reference "Charm."
- Not applicable (context does not address relevance of "Charm").

---

### Sample 36: q36

**Question:** What is the difference between implied and historical volatility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Implied volatility reflects the market's expectation of future volatility, derived from option prices and the Black-Scholes model.
- Historical volatility is a backward-looking measure based...

**Unsupported Sentences:**
- Implied volatility reflects the market's expectation of future volatility, derived from option prices and the Black-Scholes model.
- Historical volatility is a backward-looking measure based on past price movements of the underlying asset.
- Implied volatility represents market expectations for future price fluctuations, while historical volatility provides insight into past price behavior, helping traders assess risk and pricing dynamics.

---

### Sample 37: q37

**Question:** What is a delta-neutral portfolio?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- A delta-neutral portfolio is not explicitly defined in the provided context.
- The context mentions delta sensitivities in the context of market risk capital requirements.

Citations: [sourc...

**Unsupported Sentences:**
- A delta-neutral portfolio is not explicitly defined in the provided context.
- The context mentions delta sensitivities in the context of market risk capital requirements.
- Delta sensitivities are referenced in the context of market risk capital requirements.
- The context includes details on risk weights, correlation parameters, and curvature risk calculations.
- Delta sensitivities are relevant for understanding market risk and capital requirements in financial regulations.

---

### Sample 38: q38

**Question:** What is gamma hedging?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions gamma impact in options but does not link it to hedging.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457.pdf chunk_id=bis_bcbs_d457.pdf:0e40c6a1ef10] [so...

**Unsupported Sentences:**
- The context mentions gamma impact in options but does not link it to hedging.
- Each option on the same underlying has a gamma impact that is either positive or negative.

---

### Sample 39: q39

**Question:** What is volatility skew?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Volatility skew refers to differences in implied volatility across options with the same underlying and maturity but different moneyness.
- It is mentioned in the context of risk factors for...

---

### Sample 40: q40

**Question:** What is volatility smile?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- **Volatility smile** refers to the risk of changes in implied volatility parameters for instruments with optionality, relative to other instruments with the same underlying and maturity but ...

**Unsupported Sentences:**
- - **Volatility smile** refers to the risk of changes in implied volatility parameters for instruments with optionality, relative to other instruments with the same underlying and maturity but different moneyness.
- - It is identified as a specific risk type (smile risk) that does not automatically subject an instrument to the RRAO (Risk-Based Capital Requirements for Market Risk).
- - The context highlights smile risk as a distinct factor in regulatory capital frameworks, emphasizing its exclusion from automatic RRAO classification. This distinction clarifies how optionality-related risks are treated in capital requirements.

---

### Sample 41: q41

**Question:** What is a risk factor?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The cited sources discuss credit default swaps, counterparty risk, and regulatory requirements but do not address risk factors.

Citations: [source=corpus/regulatory_seed/pdf/en/fsb_review_o...

**Unsupported Sentences:**
- The cited sources discuss credit default swaps, counterparty risk, and regulatory requirements but do not address risk factors.
- The context references papers on credit default swaps (D’Errico et al., 2016; Du et al., 2016; Duffie & Zhu, 2011) and regulatory swap definitions (Federal Register, 2021).
- No explicit mention of "risk factor" or its characteristics is made in the provided excerpts.

---

### Sample 42: q42

**Question:** What is model risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Model risk is associated with the approval and ongoing supervision of trading desk models by regulators.
- Trading desks must document their policies to satisfy regulatory requirements for m...

**Unsupported Sentences:**
- Model risk is associated with the approval and ongoing supervision of trading desk models by regulators.
- Trading desks must document their policies to satisfy regulatory requirements for model approval.
- Model risk is relevant because supervisors assess the granularity of trading desk definitions and ensure compliance with regulatory standards, impacting capital requirements and risk management.

---

### Sample 43: q43

**Question:** What is counterparty credit risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Counterparty credit risk is the risk that the counterparty defaults before final settlement.
- It is mitigated through mechanisms like netting sets and collateral agreements.

Citations: [so...

---

### Sample 44: q44

**Question:** What is wrong-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Wrong-way risk occurs when exposure to a counterparty increases as their credit quality deteriorates (e.g., buying a put option from a bank on its own stock).
- It contrasts with right-way r...

---

### Sample 45: q45

**Question:** What is right-way risk?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The context discusses margin requirements for non-centrally-cleared derivatives.
- It provides examples of potential margin frameworks, including "Full, two-way margining with zero thre...

**Unsupported Sentences:**
- The context discusses margin requirements for non-centrally-cleared derivatives.
- It provides examples of potential margin frameworks, including "Full, two-way margining with zero thresholds."
- The margin framework aims to balance systemic risk reduction with costs, but relevance to "right-way risk" is not addressed.

---

### Sample 46: q46

**Question:** What is a credit support annex (CSA)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- A CSA is a legal document supplementing the ISDA Master Agreement that governs collateral terms to mitigate credit risk.
- It defines rules for posting and receiving collateral between count...

**Unsupported Sentences:**
- - The context links CSAs to counterparty risk mitigation, though it does not elaborate further.
- 3) Why it matters

---

### Sample 47: q47

**Question:** What is initial margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions "initial margin" only in the phrase "Treatment of provided initial margin" without further detail.

Citations: [source=corpus/regulatory_seed/pdf/en/iosco_iq_margin_2020...

**Unsupported Sentences:**
- The term "initial margin" appears once in the context under "Element 5: Treatment of provided initial margin" but is not defined.
- Omitted (no relevance discussed in context).

---

### Sample 48: q48

**Question:** What is variation margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Variation margin represents the settlement of the running profit/loss of a derivative.
- It is exchanged regularly and timely among parties to non-centrally cleared derivatives.

Citations: ...

---

### Sample 49: q49

**Question:** What is value at risk (VaR)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Value at risk (VaR) is not explicitly defined in the provided context.
- The context discusses risk metrics like sensitivity, delta risk, vega risk, and curvature risk but does not mention V...

**Unsupported Sentences:**
- Value at risk (VaR) is not explicitly defined in the provided context.
- The context discusses risk metrics like sensitivity, delta risk, vega risk, and curvature risk but does not mention VaR.
- Sensitivity: a bank’s estimate of the change in value of an instrument due to a small change in one of its underlying risk factors.
- Delta risk: the linear estimate of the change in value of a financial instrument due to a movement in the value of a risk factor.
- Vega risk: the potential loss resulting from the change in value of a derivative due to a change in the implied volatility of its underlying.

---

### Sample 50: q50

**Question:** What is expected shortfall (ES)?

**Status:** ✅ PASS

**Answer Preview:** 2) Key Facts
- The context discusses central clearing and risk management of non-centrally cleared derivatives (NCCDs).
- 17 jurisdictions have a legislative framework for determining when products sh...

**Unsupported Sentences:**
- The context discusses central clearing and risk management of non-centrally cleared derivatives (NCCDs).
- Not applicable (context does not address the relevance of expected shortfall).

---

## Recommendations

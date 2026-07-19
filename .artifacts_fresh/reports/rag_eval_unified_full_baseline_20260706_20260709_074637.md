# RAG Evaluation Report - unified_full_baseline_20260706

**Generated:** 2026-07-09 15:46:37

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Samples | 50 |
| Passed | 46 (92.0%) |
| Failed | 4 (8.0%) |

## Answer Evaluation

| Metric | Value | Threshold |
|--------|-------|-----------|
| citation_coverage | 0.920 | 0.8 |
| faithfulness | 0.512 | 0.75 |
| answer_relevancy | 0.882 | 0.7 |
| sentence_support_rate | 0.512 | - |

## Threshold Gate

- Verdict: fail
- Threshold Failures: 3
- Baseline Regressions: 0

## Sample Details

### Sample 1: q01

**Question:** What is FRTB and why does it matter for market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB is the Fundamental Review of the Trading Book, a market risk framework whose design and calibration are addressed in the EU’s CRR 3 proposal.
- The EU implemented FRTB via a two-step ap...

---

### Sample 2: q02

**Question:** Explain Delta in the context of derivatives risk.

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Delta is a Greek that measures the sensitivity of a derivative’s value to the underlying price level.
- In the context of interest rate risk (Delta GIRR), the sensitivity is defined as PV01,...

---

### Sample 3: q03

**Question:** What is Gamma and how is it different from Delta?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Gamma is the sensitivity of Delta to the underlying price.
- Delta is the sensitivity to the underlying price level.
- Thus, Gamma measures how Delta changes when the underlying price change...

---

### Sample 4: q04

**Question:** What is Vega and when is it important?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR  
- Vega (∂Ci/∂σi) is defined as the change in the market value of an option (Ci) resulting from a small change in its implied volatility (σi).  
- The context does not describe circumstances ...

**Unsupported Sentences:**
- Vega is sourced from pricing models used by the bank’s independent risk control unit.
- Since the context is insufficient to answer “when is it important,” you may want to consult the full vega risk factor definitions in [MAR21.8]–[MAR21.14] for additional details, or refer to the broader market risk framework for the role of vega in capital requirements.

---

### Sample 5: q05

**Question:** What is CVA and what risk does it represent?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CVA (Credit Valuation Adjustment) is an adjustment to the risk-free value.
- It reflects counterparty risk, which is the risk that the counterparty defaults before final settlement.
- CVA in...

---

### Sample 6: q06

**Question:** What does FRTB stand for?

**Status:** ❌ FAIL

**Answer Preview:** I'm unable to provide the meaning of "FRTB" based on the available indexed documents. No relevant evidence was found in the retrieval corpus.

**Suggested next actions:**
1. **Check internal glossarie...

---

### Sample 7: q07

**Question:** What is the purpose of FRTB?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB aims to improve the market risk capital framework after 2008.
- It seeks to increase risk sensitivity and model risk governance.
- It addresses shortcomings identified in the existing B...

**Unsupported Sentences:**
- It addresses shortcomings identified in the existing Basel II.5 framework.
- FRTB is a comprehensive suite of capital rules developed by the Basel Committee on Banking Supervision (BCBS) as part of Basel III, intended to be applied to banks' wholesale trading activities. (ctx 2)
- Finalised in January 2016 as the Minimum Capital Requirements for Market Risk, it aims to address a number of identified shortcomings in the existing Basel II.5 framework. (ctx 2)

---

### Sample 8: q08

**Question:** What is Credit Valuation Adjustment?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Credit Valuation Adjustment (CVA) is the price an investor would pay to hedge the counterparty credit risk of a derivative instrument.
- It reduces the mark to market value of an asset by th...

**Unsupported Sentences:**
- CVA became a fair value accounting requirement during the 2007/08 Global Financial Crisis, prompting market participants to incorporate it for over-the-counter derivatives.
- “CVA was introduced as a new requirement for fair value accounting during the 2007/08 Global Financial Crisis.”
- “Market participants started incorporating credit valuation adjustment when calculating the value of over-the-counter derivative instruments.”
- “The formula for calculating CVA is written with terms including maturity, discount factors, loss given default, default probability, and exposure over time.”
- The context states CVA was introduced as a fair value accounting requirement during the 2007/08 Global Financial Crisis, and market participants began including it in the valuation of over-the-counter derivatives.

---

### Sample 9: q09

**Question:** When was CVA introduced as a requirement?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not state when CVA was introduced as a requirement.
- Context only mentions revisions to the CVA framework: a revised framework published in 2017 and targeted revis...

**Unsupported Sentences:**
- Context only mentions revisions to the CVA framework: a revised framework published in 2017 and targeted revisions in July 2020.
- Capital requirements for CVA risk are meant to require banks to hold aside capital to account for losses.
- Because the information is insufficient, I do not know the introduction date.
- Suggested next action: consult the original Basel III text (e.g., BCBS 189, 2010) or earlier Basel committee publications to find the first mandatory CVA capital charge date.

---

### Sample 10: q10

**Question:** What is XVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define XVA.
- The context only shows a Wikipedia article structure with sections "Context," "Valuation adjustments," and "Accounting impact," and a bibliography...

**Unsupported Sentences:**
- The context only shows a Wikipedia article structure with sections "Context," "Valuation adjustments," and "Accounting impact," and a bibliography entry for "The Long and Short of It: An Overview of XVA" by GFMI.
- The Wikipedia article on XVA contains sections titled "Context," "Valuation adjustments," and "Accounting impact."
- I do not know what XVA is based on the provided context.
- To answer the question, I would need the actual content of the Wikipedia article sections or the referenced GFMI publication.
- Proposed next actions: retrieve the full text of the Wikipedia page or the GFMI article.

---

### Sample 11: q11

**Question:** What is the Basel Committee?

**Status:** ❌ FAIL

**Answer Preview:** I'm unable to answer that question because no relevant information was found in the indexed knowledge base.

**Next actions to find the answer:**
1. **Search official sources** – Visit the Bank for In...

---

### Sample 12: q12

**Question:** When was FRTB finalized?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not state a date when FRTB was finalized.
- The context mentions a May 2022 paper and references to December 2020 in file names, but neither is identified as the fi...

**Unsupported Sentences:**
- The context mentions a May 2022 paper and references to December 2020 in file names, but neither is identified as the finalization date.
- The context references a CRR3 paper dated May 2022 that discusses FRTB implementation in Europe.
- I would need a source that explicitly states the finalization date, such as a Basel Committee press release or final standard document.

---

### Sample 13: q13

**Question:** What is Basel III?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define Basel III.
- The context references a "Basel III Monitoring Report" from October 2018.
- The context discusses an explanatory note on minimum capital req...

**Unsupported Sentences:**
- The context discusses an explanatory note on minimum capital requirements for market risk, which relates to amendments to a market risk framework.
- The context includes an "Explanatory note on the minimum capital requirements for market risk."
- The data used for the analysis on the impact of the amended market risk framework were adjusted to account for amendments described in Section 3 of the note.
- For the standardised approach, amendments associated with the double-counting of FX curvature risk and the “base currency” approaches have not been captured in the impact analysis.
- The Committee expects that the impact of these amendments will result in reductions to FX risk capital requirements relative to the impact analyses set out.

---

### Sample 14: q14

**Question:** What is the difference between trading book and banking book?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context lists "Trading book vs banking book" as a common concept used in interviews and systems, but does not define the difference.
- No further details are provided.

Citations: [sourc...

---

### Sample 15: q15

**Question:** What is PnL attribution?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context does not define PnL attribution explicitly; it only lists it as a common concept used in interviews and systems under FRTB.
- The context mentions "Backtesting and PnL attributio...

---

### Sample 16: q16

**Question:** What is backtesting in market risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Backtesting is referenced alongside profit and loss (P&L) attribution test at the trading desk level.
- In the internal models approach, risk measurement uses end-of-day static portfolios to...

**Unsupported Sentences:**
- In the internal models approach, risk measurement uses end-of-day static portfolios to assess possible value change from price/rate movements over a holding period.
- MAR 99.1: “An additional consideration in specifying the appropriate risk measures and trading outcomes for profit and loss (P&L) attribution test and backtesting arises because the internally modelled risk measurement is generally based on the sensitivity of a static portfolio to instantaneous price shocks. That is, end -of-day trading positions are input into the risk measurement model, which assesses the possible change in the value of this static portfolio due to price and rate movements over the assumed holding period.”

---

### Sample 17: q17

**Question:** What is risk factor eligibility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define “risk factor eligibility.”
- The context only references market risk capital requirements, the simplified standardised approach, and a non-modellable ris...

**Unsupported Sentences:**
- The context only references market risk capital requirements, the simplified standardised approach, and a non-modellable risk factor overlay.
- [ctx 1] mentions “Minimum capital requirements for market risk,” “MAR40 Simplified standardised approach,” “Risk-weighted assets and capital requirements,” “Interest rate risk,” “Equity risk,” and “Foreign exchange risk.”
- Next actions: Review the full Basel Committee on Banking Supervision “Minimum capital requirements for market risk” framework (e.g., MAR30–MAR33) or the internal models approach documentation, where risk factor eligibility criteria are typically defined.

---

### Sample 18: q18

**Question:** What is DVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- DVA stands for Debit Valuation Adjustment, an increment to a derivative price due to the institution's own default risk.
- DVA is analogous to CVA but from the counterparty’s perspective; a ...

---

### Sample 19: q19

**Question:** What is FVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FVA is the Funding Valuation Adjustment.
- It arises from the funding implications of a trade that is not under a Credit Support Annex (CSA) or is under a partial CSA.
- It represents the fu...

**Unsupported Sentences:**
- FVA is the Funding Valuation Adjustment.
- It arises from the funding implications of a trade that is not under a Credit Support Annex (CSA) or is under a partial CSA.
- It represents the funding cost or benefit due to the difference (variation margin) between the funding rate of the bank's treasury and the collateral rate paid by a clearing house.
- FVA is explicitly defined as: “Funding Valuation Adjustment, due to the funding implications of a trade that is not under Credit Support Annex (CSA), or is under a partial CSA; essentially the funding cost or benefit due to the difference (variation margin) between the funding rate of the bank's treasury and the collateral rate paid by a clearing house.” (from context)

---

### Sample 20: q20

**Question:** What is KVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- KVA is not mentioned in the provided context.
- The context only covers XVA in general, valuation adjustments, and accounting impact without defining KVA.

Citations: [source=corpus/regulato...

**Unsupported Sentences:**
- KVA is not mentioned in the provided context.
- The context only covers XVA in general, valuation adjustments, and accounting impact without defining KVA.
- The context does not contain any facts about KVA.

---

### Sample 21: q21

**Question:** What is MVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- MVA stands for Margin Valuation Adjustment.
- It refers to the funding costs of the initial margin specific to centrally cleared transactions.
- It may be calculated according to the global ...

---

### Sample 22: q22

**Question:** What is ColVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CollVA is the value of the optionality embedded in a CSA to post collateral in different currencies.
- This definition is provided in the context of discussing various valuation adjustments....

**Unsupported Sentences:**
- This definition is provided in the context of discussing various valuation adjustments.
- The context does not discuss the relevance of CollVA.

---

### Sample 23: q23

**Question:** What is the default probability in CVA?

**Status:** ✅ PASS

**Answer Preview:** ## 1) TLDR
- The provided context does not state a specific numerical value or explicit definition for default probability in CVA.
- In one source, default probability is listed among the terms used i...

**Unsupported Sentences:**
- In one source, default probability is listed among the terms used in the CVA calculation formula.
- According to [ctx 1], the formula for calculating CVA is written with terms including maturity, discount factors, loss given default, default probability, and exposure over time.

---

### Sample 24: q24

**Question:** What is loss given default (LGD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- For calculating the gross jump-to-default (JTD), LGD is set as follows: equity instruments and non-senior debt instruments are assigned an LGD of 100%.
- Senior debt instruments are assigned...

**Unsupported Sentences:**
- For calculating the gross jump-to-default (JTD), LGD is set as follows: equity instruments and non-senior debt instruments are assigned an LGD of 100%.
- Senior debt instruments are assigned an LGD of 75%.
- Covered bonds, as defined within [MAR21.51], are assigned an LGD of 25%.
- Equity instruments and non-senior debt instruments are assigned an LGD of 100%.
- Senior debt instruments are assigned an LGD of 75%.

---

### Sample 25: q25

**Question:** What is exposure at default (EAD)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define exposure at default (EAD).
- The context only mentions "exposure over time" as a component in the CVA formula.

Citations: [source=corpus/acceptance/cva_...

**Unsupported Sentences:**
- The provided context does not define exposure at default (EAD).
- The context only mentions "exposure over time" as a component in the CVA formula.
- The CVA formula includes "exposure over time" (from ctx 2, ctx 3).
- No explicit definition or description of EAD is present in the context.
- The context does not discuss the relevance of EAD.

---

### Sample 26: q26

**Question:** What is the role of discount factors in CVA?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The CVA calculation formula includes discount factors as one of its terms.
- No further detail on the specific role of discount factors is provided in the context.

Citations: [source=corpus...

---

### Sample 27: q27

**Question:** What is CRR II?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- CRR II stands for the Revised Capital Requirements Regulation.
- It is referenced in the context alongside "related Banking Package proposals."

Citations: [source=corpus/acceptance/frtb_icm...

---

### Sample 28: q28

**Question:** What is the difference between FRTB and Basel II.5?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- FRTB is a comprehensive suite of capital rules developed as part of Basel III, while Basel II.5 is the existing framework it aims to improve.
- FRTB explicitly aims to address a number of id...

**Unsupported Sentences:**
- FRTB is a comprehensive suite of capital rules developed as part of Basel III, while Basel II.5 is the existing framework it aims to improve.
- The Fundamental Review of the Trading Book (FRTB) was finalised in January 2016 as the Minimum Capital Requirements for Market Risk.
- FRTB is part of Basel III and applies to banks' wholesale trading activities.

---

### Sample 29: q29

**Question:** Does FRTB increase bank capital costs?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- While FRTB was not intended to increase banks' capital costs beyond those imposed by Basel II.5, it is clear from both BCBS and industry analysis that banks will see significant incr [ctx 2]...

**Unsupported Sentences:**
- The context does not discuss why this matters.

---

### Sample 30: q30

**Question:** What is the BCBS?

**Status:** ❌ FAIL

**Answer Preview:** I’m unable to answer the question “What is the BCBS?” because no relevant evidence was found in the indexed corpus.

**Next actions you can take:**
1. Provide a more specific or expanded term (e.g., “...

---

### Sample 31: q31

**Question:** What is Theta in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Theta is the sensitivity of a derivative's value to the passage of time.
- Theta is also known as time decay.

Citations: [source=corpus/Background.md chunk_id=Background.md:222936993a67] [s...

---

### Sample 32: q32

**Question:** What is Rho in Greeks?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Rho is a Greek that measures the sensitivity of a derivative's value to changes in interest rates.
- It is listed among other first-order and second-order risk sensitivities.

Citations: [so...

**Unsupported Sentences:**
- It is listed among other first-order and second-order risk sensitivities.

---

### Sample 33: q33

**Question:** What is Volga?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Volga is a second-order Greek.
- It measures the sensitivity of Vega to changes in implied volatility.
- It is also called vomma.

Citations: [source=corpus/Background.md chunk_id=Background...

**Unsupported Sentences:**
- It measures the sensitivity of Vega to changes in implied volatility.
- It is also called vomma.
- Volga: second-order Greek measuring the sensitivity of Vega to changes in implied volatility (also called vomma).

---

### Sample 34: q34

**Question:** What is Vanna?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Vanna is a second-order Greek.
- It measures the sensitivity of Delta to changes in implied volatility.
- Equivalently, it measures the sensitivity of Vega to changes in the underlying price...

**Unsupported Sentences:**
- Vanna is a second-order Greek.
- It measures the sensitivity of Delta to changes in implied volatility.
- Equivalently, it measures the sensitivity of Vega to changes in the underlying price.
- Vanna: second-order Greek measuring the sensitivity of Delta to changes in implied volatility, equivalently the sensitivity of Vega to changes in the underlying price.

---

### Sample 35: q35

**Question:** What is Charm?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Charm is the sensitivity of Delta to the passage of time.
- It is also known as delta decay or DdeltaDtime.

Citations: [source=corpus/Background.md chunk_id=Background.md:402e6913648a] [sou...

---

### Sample 36: q36

**Question:** What is the difference between implied and historical volatility?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Implied volatility is the market's expectation of future volatility, derived from option prices and implied by the Black-Scholes model.
- Historical volatility is a backward-looking measure ...

---

### Sample 37: q37

**Question:** What is a delta-neutral portfolio?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define a delta-neutral portfolio or any concept related to it.
- The context only states a figure for a portfolio's delta risk plus DRC requirements: USD 122.7 ...

**Unsupported Sentences:**
- I do not know what a delta-neutral portfolio is based on the provided context.
- Proposed next actions: Seek a definition from a source that explains delta-neutral strategies (e.g., educational materials on options hedging or risk management).

---

### Sample 38: q38

**Question:** What is gamma hedging?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define or discuss "gamma hedging."
- The context fragments mention "hedging" only in incomplete statements, such as "hedging purposes given that the concept of ...

**Unsupported Sentences:**
- - The provided context does not define or discuss "gamma hedging."
- - The context fragments mention "hedging" only in incomplete statements, such as "hedging purposes given that the concept of hedging is difficult to administer," with no further details.
- - Gamma is defined as the "sensitivity of Delta to the underlying price." [ctx 1]
- - No definition, description, or factual statement about "gamma hedging" appears in any provided context.
- - The concept of hedging is mentioned only as being "difficult to administer" [ctx 2, ctx 3, ctx 4], but no relevance to gamma hedging is discussed.

---

### Sample 39: q39

**Question:** What is volatility skew?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define or discuss "volatility skew."
- It mentions Greeks, implied volatility (cut off), and risk weight settings for commodity volatilities, none of which desc...

**Unsupported Sentences:**
- Next actions: provide a definition from a reliable source (e.g., an authoritative finance textbook or regulatory document) that explicitly describes volatility skew, or broaden the context to include a section on volatility surfaces/skew.

---

### Sample 40: q40

**Question:** What is volatility smile?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Volatility smile is a pattern where both out-of-the-money and in-the-money options have higher implied v (the provided context ends mid-word; the full term appears to be “implied volatility”...

**Unsupported Sentences:**
- The provided context does not discuss why the volatility smile matters.

---

### Sample 41: q41

**Question:** What is a risk factor?

**Status:** ❌ FAIL

**Answer Preview:** I'm unable to answer that question based on the available retrieval context. No relevant evidence was found in the indexed corpus.

**Next actions:**
1. **Refine your query** – try rephrasing the ques...

---

### Sample 42: q42

**Question:** What is model risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define model risk.
- The context focuses on minimum capital requirements for market risk under a standardised approach, covering topics like interest rate risk,...

**Unsupported Sentences:**
- 1) TLDR
- - The context focuses on minimum capital requirements for market risk under a standardised approach, covering topics like interest rate risk, equity risk, foreign exchange risk, commodities risk, and treatment of options.
- 2) Key Facts
- - The context references “Minimum capital requirements for market risk” and a “Simplified standardised approach.”
- - Specific pages are noted for interest rate risk, equity risk, foreign exchange risk, commodities risk, and the treatment of options.

---

### Sample 43: q43

**Question:** What is counterparty credit risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- Counterparty risk is the risk that the counterparty defaults before final settlement.
- A Credit Valuation Adjustment (CVA) is an adjustment to the risk-free value that increases when counte...

---

### Sample 44: q44

**Question:** What is wrong-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context mentions wrong-way risk as a concept that interacts with CVA, collateral, and netting sets.
- The context does not provide a definition or description of wrong-way risk.

Citatio...

**Unsupported Sentences:**
- The context mentions wrong-way risk as a concept that interacts with CVA, collateral, and netting sets.
- The context does not provide a definition or description of wrong-way risk.
- The context states: "In practice, CVA often interacts with collateral, netting sets, and wrong-way risk."
- I do not know the definition of wrong-way risk based on the provided context.
- The context only mentions the term without defining it.

---

### Sample 45: q45

**Question:** What is right-way risk?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR  
- The provided context does not define or mention “right-way risk.”  
- The context only lists “wrong-way risk” as a key counterparty risk concept, with no further explanation.

Citations: [...

**Unsupported Sentences:**
- The provided context does not define or mention “right-way risk.”
- The context only lists “wrong-way risk” as a key counterparty risk concept, with no further explanation.
- [ctx 1] states: “Wrong-way risk:” is listed among key counterparty risk concepts, but no definition is given.
- No other content in [ctx 1] references right-way risk.
- Not addressed in the context.

---

### Sample 46: q46

**Question:** What is a credit support annex (CSA)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR  
- A CSA is a legal document that supplements the ISDA Master Agreement and governs collateral terms between counterparties to mitigate credit risk.

Citations: [source=corpus/Background.md c...

**Unsupported Sentences:**
- A CSA is a legal document that supplements the ISDA Master Agreement and governs collateral terms between counterparties to mitigate credit risk.
- CSA stands for Credit Support Annex.
- It is a legal document that supplements the ISDA Master Agreement.
- It governs the terms for posting and receiving collateral between counterparties.
- Its purpose is to mitigate credit risk.

---

### Sample 47: q47

**Question:** What is initial margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define initial margin; it only mentions initial margin as part of the baseline minimum margin requirements for non-centrally-cleared derivatives.
- The context ...

**Unsupported Sentences:**
- The provided context does not define initial margin; it only mentions initial margin as part of the baseline minimum margin requirements for non-centrally-cleared derivatives.
- The context discusses the need for a minimum amount of initial margin and the methodologies for calculating that amount, but no definition is offered.
- “A third key element of the margin requirements is the minimum, baseline amount of initial and variation margin that would be required to be collected for a non-centrally-cleared derivative and the methodologies by which that baseline amount would be calculated.”
- The context notes that the BCBS and IOSCO evaluated these baseline margin amounts by reference to systemic risk reduction and promotion of central clearing, indicating initial margin is considered relevant to those goals.

---

### Sample 48: q48

**Question:** What is variation margin?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The context discusses variation margin as part of baseline minimum amounts and methodologies for margin requirements for non-centrally-cleared derivatives.
- The BCBS and IOSCO evaluated the...

---

### Sample 49: q49

**Question:** What is value at risk (VaR)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not contain a definition of Value at Risk (VaR).
- The context only covers minimum capital requirements for market risk and defines terms like sensitivity, delta ri...

**Unsupported Sentences:**
- The provided context does not contain a definition of Value at Risk (VaR).
- The context only covers minimum capital requirements for market risk and defines terms like sensitivity, delta risk, vega risk, and curvature risk.
- The context defines sensitivity as “a bank’s estimate of the change in value of an instrument due to a small change in one of its underlying risk factors” and states that “Delta and vega risks are sensitivities.”
- Delta risk is defined as “the linear estimate of the change in value of a financial instrument due to a movement in the value of a risk factor.”
- Curvature risk is mentioned as “the additional potential loss beyond delta risk due to a change in a risk factor for financial instruments with option.”

---

### Sample 50: q50

**Question:** What is expected shortfall (ES)?

**Status:** ✅ PASS

**Answer Preview:** 1) TLDR
- The provided context does not define expected shortfall (ES).
- No information about ES is present in the given excerpts.

Citations: [source=corpus/regulatory_seed/pdf/en/bis_bcbs_d457_note...

**Unsupported Sentences:**
- The provided context does not define expected shortfall (ES).
- No information about ES is present in the given excerpts.
- The context defines only the following risk metrics: sensitivity, delta risk, vega risk, and curvature risk.
- No statement about expected shortfall appears in the provided text.
- If you need the definition of expected shortfall, I recommend consulting the full regulatory document...

---

## Recommendations

# Background

目标: 为 RiskAgent-RAG 的 Week 2 提供第一批可评测的金融衍生品与风险管理基础语料, 用于提升 retrieval 质量与 citations coverage.

## 1. Market risk basics

Market risk is the risk of losses due to changes in market factors such as interest rates, FX rates, equity prices, and credit spreads.

Common market risk factors:

- Interest rate level and curve shape
- FX spot and forwards
- Equity spot and volatility
- Credit spread and hazard rate

## 2. Derivatives and pricing basics

A derivative is a contract whose value depends on an underlying asset or reference rate.

Common examples:

- Options
- Swaps
- Futures

A pricing model maps risk factors to a present value.

## 3. Risk sensitivities (Greeks)

Greeks are sensitivities of a derivative value to small changes in risk factors.

Key Greeks:

- Delta: sensitivity to the underlying price level.
- Gamma: sensitivity of Delta to the underlying price.
- Vega: sensitivity to volatility.

In risk systems, Greeks are often aggregated by dimensions such as desk, book, trader, and risk factor.

## 4. FRTB overview

FRTB stands for Fundamental Review of the Trading Book.

High level goals:

- Improve market risk capital framework after 2008.
- Increase risk sensitivity and model risk governance.

Common concepts used in interviews and systems:

- Trading book vs banking book
- Risk factor eligibility
- Backtesting and PnL attribution

## 5. Counterparty risk and CVA

Counterparty risk is the risk that the counterparty defaults before final settlement.

CVA stands for Credit Valuation Adjustment.

A simplified intuition:

- CVA is an adjustment to the risk-free value.
- CVA increases when counterparty credit quality worsens.
- CVA depends on exposure profile over time.

In practice, CVA often interacts with collateral, netting sets, and wrong-way risk.

## 6. What makes citations useful for engineers

For engineers, citations are not a nice-to-have feature. Citations are a contract.

Why:

- Debugging: you can inspect the exact chunk that supported a conclusion.
- Reproducibility: you can rerun the same question and confirm the same evidence.
- Drift control: when data changes, you can detect that the evidence changed.

## 7. Minimal glossary

- Position: a holding or trade that creates exposure.
- Desk: a trading unit grouping positions.
- Exposure: a measure of sensitivity or value at risk.
- Limit: a threshold used to trigger alerts.

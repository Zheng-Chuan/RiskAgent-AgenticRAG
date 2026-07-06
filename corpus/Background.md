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
- Theta: sensitivity of a derivative's value to the passage of time (also known as time decay).
- Rho: sensitivity of a derivative's value to changes in interest rates.
- Volga: second-order Greek measuring the sensitivity of Vega to changes in implied volatility (also called vomma).
- Vanna: second-order Greek measuring the sensitivity of Delta to changes in implied volatility, equivalently the sensitivity of Vega to changes in the underlying price.
- Charm: sensitivity of Delta to the passage of time (also known as delta decay or DdeltaDtime).

Related concepts:

- Implied volatility: the market's expectation of future volatility, derived from option prices and implied by the Black-Scholes model.
- Historical volatility: a backward-looking measure based on past price movements of the underlying asset.
- Volatility smile: a pattern where both out-of-the-money and in-the-money options have higher implied volatility than at-the-money options.
- Volatility skew: the pattern where implied volatility varies across strike prices, typically with lower strikes having higher volatility (common in equity index options).
- Delta-neutral portfolio: a portfolio whose total delta is zero, making it insensitive to small changes in the underlying price; often used by market makers to hedge directional risk.
- Gamma hedging: adjusting a portfolio to reduce gamma exposure, making the hedge more stable to larger moves in the underlying asset price.

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

Key counterparty risk concepts:

- Netting set: a group of trades with a single counterparty that can be netted under a single master agreement (e.g., ISDA Master Agreement), reducing overall exposure by offsetting positive and negative mark-to-market values.
- CSA (Credit Support Annex): a legal document that supplements the ISDA Master Agreement, governing the terms for posting and receiving collateral between counterparties to mitigate credit risk.
- Wrong-way risk: occurs when exposure to a counterparty increases as the counterparty's credit quality deteriorates; for example, buying a put option from a bank on the bank's own stock.
- Right-way risk: the opposite of wrong-way risk; occurs when exposure to a counterparty decreases as the counterparty's credit quality deteriorates, reducing overall counterparty risk.

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

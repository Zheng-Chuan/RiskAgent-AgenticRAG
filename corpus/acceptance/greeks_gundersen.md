# Greeks overview(Gundersen)

Source: [https://gregorygundersen.com/blog/2023/10/08/greeks/](https://gregorygundersen.com/blog/2023/10/08/greeks/)

An option pricing model is a function that takes the price of the underlying asset, or spot price S, and other market inputs and outputs an option's fair value V.

An important way to understand an option-pricing model is to study the output price's sensitivity to the model's inputs. These partial derivatives are called the Greeks.

For example, the sensitivity of option price to spot is delta, written as dV/dS.

The most common choice for an option pricing model is the Black-Scholes equation, with inputs including spot price, strike price, time to expiry, volatility, and risk-free interest rate.

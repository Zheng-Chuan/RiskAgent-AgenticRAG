# Source

https://en.wikipedia.org/wiki/XVA

# Text









XVA - Wikipedia
























































Jump to content
















Main menu












Main menu


move to sidebar


hide







		Navigation
	






Main page
Contents
Current events
Random article
About Wikipedia
Contact us











		Contribute
	






Help
Learn to edit
Community portal
Recent changes
Upload file
Special pages








































Search
























Search














































Appearance


































Donate




Create account




Log in


















Personal tools












Donate
 
Create account
 
Log in


























































Contents


move to sidebar


hide










(Top)












1


Context


















2


Valuation adjustments


















3


Accounting impact


















4


References


















5


Bibliography






































Toggle the table of contents
















XVA








2 languages










Svenska
中文




Edit links
























Article
Talk












English




































Read
Edit
View history
















Tools












Tools


move to sidebar


hide







		Actions
	






Read
Edit
View history











		General
	






What links here
Related changes
Upload file
Permanent link
Page information
Cite this page
Get shortened URL
Download QR code











		Print/export
	






Download as PDF
Printable version











		In other projects
	






Wikidata item












































Appearance


move to sidebar


hide






















From Wikipedia, the free encyclopedia








Banking valuation adjustments


Part of a 
series
 on
Finance


Markets


Assets


Asset (economics)


Bond


Asset growth


Capital asset


Commodity


Derivatives


Domains


Equity


Foreign exchange


Money


Over-the-counter


Private equity


Real estate


Spot


Stock




Participants


Angel investor


Bull (stock market speculator)


Financial planner


Investor


institutional


Retail


Speculator




Locations


Financial centres


Offshore financial centres


Conduit and sink OFCs






Instruments


Bond


Cash


Collateralised debt obligation


Credit default swap


Time deposit
 (
certificate of deposit
)


Credit line


Deposit


Derivative


Futures contract


Indemnity


Insurance


Letter of credit


Loan


Mortgage


Option
 (
call
exotic
put
)


Performance bonds


Repurchase agreement


Stock


Security


Syndicated loan


Synthetic CDO






Corporate

General


Accounting


Audit


Capital budgeting


Capital structure


Corporate finance


Credit rating agency


Enterprise risk management


Enterprise value


Risk management


Financial statements



Transactions


Leveraged buyout


Mergers and acquisitions


Structured finance


Venture capital




Taxation


Base erosion and profit shifting
 (BEPS)


Corporate tax haven


Tax inversion


Tax haven


Transfer pricing






Personal


Credit
 / 
Debt


Employment contract


Financial planning


Retirement
Student loan




Public


Government spending


Final consumption expenditure


Operations
Redistribution


Transfer payment




Government revenue


Taxation
Deficit spending


Budget
 (
balance
)
Debt


Non-tax revenue


Warrant of payment






Banking


Central bank


Deposit account


Fractional-reserve


Full-reserve


Investment banking


Loan


Money supply




Lists of banks




Bank regulation


Banking license


Basel Accords


Bank for International Settlements


Financial Stability Board


Deposit insurance


Separation of investment and retail banking






Regulation
 
·
 
Financial law


International Financial Reporting Standards


ISO 31000


Professional certification


Fund governance






Economic history


Private equity and venture capital


Recession


Stock market bubble


Stock market crash


Accounting scandals




Outline


 
Business and Economics portal


 
Money portal
v
t
e


X-Value Adjustment
 (
XVA
, 
xVA
) is an 
umbrella term
 referring to a number of different "valuation adjustments" that banks must make when assessing the value of 
derivative contracts
 that they have entered into.
[
1
]
[
2
]
 The purpose of these is twofold: primarily to hedge for possible losses due to 
other parties' failures to pay amounts due on the derivative contracts
; but also to determine (and hedge) the amount of capital required under the 
bank capital adequacy rules
.  XVA has led to the creation of 
specialized desks
 in many banking institutions 
to manage
 XVA exposures.
[
3
]
[
4
]






Context
[
edit
]


Historically,
[
5
]
[
6
]
[
7
]
[
8
]
[
9
]
 (
OTC
) 
derivative pricing
 has relied on the 
Black–Scholes
 
risk neutral pricing framework
 which assumes that funding is available at the risk free rate and that traders can 
perfectly replicate derivatives
 so as to fully hedge.
[
10
]


This, in turn, assumes that derivatives can be traded without taking on credit risk. During the 
2008 financial crisis
, many financial institutions failed, leaving their counterparts with claims on derivative contracts that were paid only in part. Therefore it became clear that 
counterparty credit risk
 must also be considered in derivatives valuation,
[
11
]
 and 
the risk neutral value
 is to be adjusted correspondingly.



Valuation adjustments
[
edit
]


When a derivative's exposure is 
collateralized
, the "fair-value" is computed as before, but using the 
overnight index swap
 (OIS) curve for discounting. The OIS is chosen here as it reflects the rate for overnight secured lending between banks, and is thus considered a good indicator of the interbank credit markets.

When the exposure is not collateralized then a 
credit valuation adjustment
, or 
CVA
, is subtracted from this value
[
5
]
 (the logic: an institution insists on paying less for the option, knowing that the counterparty may default on its unrealized gain). This CVA is the discounted 
risk-neutral expectation
 value of the loss expected due to the counterparty not paying in accordance with the contractual terms, and is typically calculated under 
a simulation framework
;
[
12
]
[
13
]

see 
Credit valuation adjustment § Calculation
.

When transactions are governed by a 
master agreement
 that includes 
netting
-off of contract exposures, then the expected loss from a default depends on the net exposure of the whole portfolio of derivative trades outstanding under the agreement rather than being calculated on a transaction-by-transaction basis. The CVA (and xVA) applied to a new transaction should be the incremental effect of the new transaction on the portfolio CVA.
[
12
]


While the CVA reflects the market value of 
counterparty credit risk
, 
additional
 Valuation Adjustments for debit, funding cost, 
regulatory capital
 and 
margin
 may similarly be added.
[
14
]
[
15
]
 
As with CVA, these results are modeled via simulation as a function of the risk-neutral expectation of (a) the values of the underlying instrument and the relevant market values, and (b) the creditworthiness of the counterparty. This approach relies on an extension of the 
economic arguments underlying
 standard derivatives valuation.
[
13
]


These XVA include the following;
[
13
]
[
16
]

and will require
[
17
]
 careful and correct aggregation to avoid 
double counting
:



DVA
, Debit Valuation Adjustment: analogous to CVA, the adjustment (increment) to a derivative price due to the institution's own default risk. DVA is basically CVA from the counterparty’s perspective. If one party incurs a CVA loss, the other party records a corresponding DVA gain.
[
18
]
 (Bilateral Valuation Adjustment, BVA = DVA-CVA.
[
19
]
)


FVA
, Funding Valuation Adjustment, due to the funding implications of a trade that is not under 
Credit Support Annex
 (CSA), or is under a partial CSA; essentially the funding cost or benefit due to the difference (
variation margin
) between 
the funding rate
 of the 
bank's treasury
 and the collateral rate paid by a 
clearing house
.
[
20
]


MVA
, Margin Valuation Adjustment, refers to the funding costs of the 
initial margin
 specific to 
centrally cleared transactions
. It may be calculated according to the global rules for non-centrally cleared derivatives rules.
[
21
]


KVA
, the Valuation Adjustment for 
regulatory capital
 that must be held by the Institution against the exposure throughout the life of the contract (lately applying 
SA-CCR
).


Other adjustments are also sometimes made including
[
13
]
 TVA, for tax, and RVA, for replacement of the derivative 
on downgrade
.
[
14
]
 FVA may be decomposed into FCA for receivables and FBA for payables – where FCA is due to self-funded borrowing spread over Libor, and FBA due to self funded lending.  Relatedly, LVA represents the specific 
liquidity adjustment
, while CollVA is the value of the optionality embedded in a CSA to post collateral in different currencies. CRA, the collateral rate adjustment, reflects the present value of the expected excess of net interest paid on cash collateral over the net interest that would be paid if the interest rate equaled the risk-free rate.



Accounting impact
[
edit
]


See also: 
Credit valuation adjustment § Function of the CVA desk
, and 
Financial risk management § Banking


Per the 
IFRS 13
 
accounting standard
, 
fair value
 is defined as "the price that would be received to sell an asset or paid to transfer a liability in an orderly transaction between market participants at the measurement date."
[
22
]

Accounting rules thus mandate
[
23
]

the inclusion of CVA, and DVA, in 
mark-to-market accounting
. 

One notable impact of this standard, is that bank earnings are subject to XVA volatility,
[
23
]
 (largely) a function of changing counterparty credit risk. A major task of the XVA-desk, therefore,
[
4
]
[
24
]
 is to 
hedge
[
13
]
 this exposure; see 
Financial risk management § Banking
. This is achieved by buying, for example, 
credit default swaps
: this "CDS protection" applies in that its value is driven, also, by the counterparty's 
credit worthiness
.
[
25
]

Hedges can also counter the variability of the exposure component of CVA risk, offsetting 
PFE
 at a given quantile.

Under 
Basel III
 banks are required to hold specific 
regulatory capital
 on the net CVA-risk.
[
26
]

(To distinguish: this charge for CVA addresses the potential mark-to-market loss, while the 
SA-CCR
 framework addresses counterparty risk itself.
[
27
]
)
Two approaches are available for calculating the CVA required-capital: the standardised approach (SA-CVA) and the basic approach (BA-CVA). Banks must use BA-CVA unless they receive approval from their relevant 
supervisory authority
 to use SA-CVA.

The XVA-desk is then responsible for managing counterparty risk as well as (minimizing) the capital requirements under Basel.
[
28
]

The requirements of the XVA-desk differ from those of the 
Risk Control group
 and it is not uncommon to see institutions use 
different systems
 for risk exposure management on one hand, and XVA pricing and hedging on the other, with the desk employing its own 
quants
.



References
[
edit
]






^
 
"X-Value Adjustment"
. 
Association of Corporate Treasurers
.




^
 
"Valuation adjustments and their impact on the banking sector"
 
(PDF)
. 
PricewaterhouseCoopers
. December 2015.




^
 
"CVA traders left stranded as XVA becomes big new acroynm"
. 
eFinancialCareers
. 2014-06-20
. Retrieved 
2023-09-27
.




^ 
a
 
b
 
International Association of Credit Portfolio Managers (2018). 
"The Evolution of XVA Desk Management"




^ 
a
 
b
 
Derivatives Pricing after the 2007–2008 Crisis: How the Crisis Changed the Pricing Approach
, Didier Kouokap Youmbi, 
Bank of England
 – 
Prudential Regulation Authority




^
 
XVAs: Funding, Credit, Debit & Capital in pricing
 
Archived
 2016-01-22 at the 
Wayback Machine
. Massimo Morini, Banca IMI




^
 
Brigo, Damiano (November 2015), 
Nonlinear valuation and XVA under credit risk, collateral margins and Funding Costs
 
(PDF)
, 
Université catholique de Louvain
, [Course notes: Doctoral course, Université catholique de Louvain, 19–20 Nov 2015]
{{
citation
}}
:  CS1 maint: location missing publisher (
link
)




^
 
Claudio Albanese, Simone Caenazzo and Stephane Crepey (2016). 
Capital Valuation Adjustment and Funding Valuation Adjustment
. 
Risk Magazine
, May 2016.




^
 
Brigo, Damiano (November 5, 2011). 
"Counterparty Risk FAQ: Credit VaR, PFE, CVA, DVA, Closeout, Netting, Collateral, Re-hypothecation, WWR, Basel, Funding, CCDS and Margin Lending"
 
(PDF)
. 
Department of Mathematics, King's College, London
. 
arXiv
:
1111.1331
.




^
 
See 
Black–Scholes equation § Derivation of the Black–Scholes PDE
; 
Rational pricing § The replicating portfolio




^
 
Kjølhede, Christian; Bech, Anders. 
"Post-Crisis Pricing of Swaps using xVAs"
 
(PDF)
. 
Aarhus University
. Archived from 
the original
 
(PDF)
 on 2016-09-17
. Retrieved 
2017-02-02
.




^ 
a
 
b
 
John Hull
 (May 3, 2016). 
"Valuation Adjustments 1"
. 
fincad.com
.




^ 
a
 
b
 
c
 
d
 
e
 
John C. Hull and Alan White (2014). 
Collateral and Credit Issues in Derivatives Pricing
. Rotman School of Management Working Paper No. 2212953




^ 
a
 
b
 
XVA and Collateral: pricing and managing new liquidity risks
. Andrew Green




^
 
XVA: About CVA, DVA, FVA and Other Market Adjustments
, Discussion paper: Louis Bachelier Finance and Sustainable Growth Labex. Stephane Crepey




^
 
"XVAs Defined: The Profitability Puzzle"
. 
www.numerix.com
. 5 July 2018.




^
 
"Xva PDF | PDF | Hedge (Finance) | Arbitrage"
. 
Scribd
. Retrieved 
2023-09-25
.




^
 
"CVA, DVA And Hedging Earnings Volatility | Quantifi"
. 
www.quantifisolutions.com
. Retrieved 
2023-08-24
.




^
 
Christopher Foot. 
Credit Default Swaps




^
 
"Funding Valuation Adjustment (FVA), Part 1: A Primer | Quantifi"
. 2014-03-20.




^
 
Basel Committee on Banking Supervision; Board of the International Organization of Securities Commissions (March 2015), 
Margin requirements for non-centrally cleared derivatives
, Basel: Bank for International Settlements (BIS), 
ISBN
 
978-92-9197-063-6




^
 
"IFRS 13.9 and IFRS 13 Defined Terms"
. ifrs.org.




^ 
a
 
b
 
Ernst & Young
 (2014). 
Credit valuation adjustments for derivative contracts
 
Archived
 2024-01-26 at the 
Wayback Machine




^
 
James Lee (2010). 
Counterparty credit risk pricing, assessment, and dynamic hedging
, 
Citigroup Global Markets




^
 
"Components of CVA Hedging"
; §16.2 in John Gregory (2014). "Counterparty Credit Risk and Credit Value Adjustment: A Continuing Challenge for Global Financial Markets", 2nd Edition. Wiley. 
ISBN
 
9781118316672




^
 
Bank for International Settlements
 (2020). 
MAR 50 - Credit valuation adjustment framework




^
 
Bank for International Settlements (2018). 
Counterparty credit risk in Basel III - Executive Summary




^
 
Kenneth Kapner and Charles Gates (2016). 
"The Long and Short of It: An Overview of XVA"
. 
GFMI






Bibliography
[
edit
]


Andrew Green (2015). 
XVA: Credit, Funding and Capital Valuation Adjustments
. 
Wiley
. 
ISBN
 
978-1-118-55678-8
.


Jon Gregory (2015). 
The xVA Challenge: Counterparty Credit Risk, Funding, Collateral, and Capital
 (3rd ed.). Wiley. 
ISBN
 
978-1-119-10941-9
.


Chris Kenyon and Andrew Green (Eds) (2016). 
Landmarks in XVA: From Counterparty Risk to Funding Costs and Capital
. 
Risk Books
. 
ISBN
 
978-1782722557
.


Roland Lichters, Roland Stamm and Donal Gallagher (2015). 
Modern Derivatives Pricing and Credit Exposure Analysis: Theory and Practice of CSA and XVA Pricing, Exposure Simulation and Backtesting
. Palgrave Macmillan. 
ISBN
 
978-1137494832
.


Dongsheng Lu (2015). 
The XVA of Financial Derivatives: CVA, DVA and FVA Explained
. 
Palgrave Macmillan
. 
ISBN
 
978-1137435835
.


Ignacio Ruiz (2015). 
XVA Desks – A New Era for Risk Management
. Palgrave Macmillan UK. 
ISBN
 
978-1-137-44819-4
.


Antoine Savine and Jesper Andreasen (2021). 
Modern Computational Finance: Scripting for Derivatives and XVA
. Wiley. 
ISBN
 
978-1119540786
.


Donald J. Smith (2017). 
Valuation in a World of CVA, DVA, and FVA: A Tutorial on Debt Securities and Interest Rate Derivatives
. 
World Scientific
. 
ISBN
 
978-9813222748
.


Alexander Sokol (2014). 
Long-Term Portfolio Simulation: For XVA, Limits, Liquidity and Regulatory Capital
. 
Risk Books
. 
ISBN
 
978-1782720959
.


Osamu Tsuchiya (2019). 
A Practical Approach to XVA
. 
World Scientific
. 
ISBN
 
978-9813272750
.










Retrieved from "
https://en.wikipedia.org/w/index.php?title=XVA&oldid=1322941580
"


Categories
: 
Mathematical finance
Credit risk
Derivatives (finance)
Financial risk modeling
Monte Carlo methods in finance
Hidden categories: 
Webarchive template wayback links
CS1 maint: location missing publisher
Articles with short description
Short description is different from Wikidata














 This page was last edited on 18 November 2025, at 18:56
 (UTC)
.


Text is available under the 
Creative Commons Attribution-ShareAlike 4.0 License
;
additional terms may apply. By using this site, you agree to the 
Terms of Use
 and 
Privacy Policy
. Wikipedia® is a registered trademark of the 
Wikimedia Foundation, Inc.
, a non-profit organization.






Privacy policy


About Wikipedia


Disclaimers


Contact Wikipedia


Legal & safety contacts


Code of Conduct


Developers


Statistics


Cookie statement


Mobile view






























Search




























Search




















Toggle the table of contents
















XVA


























































2 languages






Add topic



































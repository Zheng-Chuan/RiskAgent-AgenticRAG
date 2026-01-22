# Source

https://en.wikipedia.org/wiki/Credit_valuation_adjustment

# Text









Credit valuation adjustment - Wikipedia






















































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


Calculation










Toggle Calculation subsection












1.1


Risk-neutral expectation


















1.2


Exposure, independent of counterparty default


















1.3


Approximation


















1.4


Accounting treatment






















2


Function of the CVA desk


















3


See also


















4


Notes


















5


References


















6


External links






































Toggle the table of contents
















Credit valuation adjustment








6 languages










Deutsch
Français
日本語
Polski
Português
Svenska




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








Economics term






CVA related concepts:







The mathematical concept as defined below;


A part of the regulatory Capital and RWA (
risk-weighted asset
) calculation 
[
1
]
 introduced under 
Basel 3
;


The CVA internal department of an investment bank, whose purpose is to:

hedge for possible losses due to counterparty default;


hedge to reduce the amount of capital required under the CVA calculation of 
Basel 3
;


The "CVA charge". The hedging of the CVA desk has a cost associated to it, i.e. the bank has to buy the hedging instrument. This cost is then allocated to each business line of an investment bank (usually as a contra revenue). This allocated cost is called the "CVA Charge".




A 
Credit valuation adjustment
 (
CVA
), 

[
a
]

in 
financial mathematics
, is an "adjustment" to a 
derivative's
 price, as charged by a bank to a 
counterparty
 to compensate it for taking on the 
credit risk of that counterparty
 during the life of the transaction. 
"CVA" can refer more generally to several related concepts, as delineated aside.
The most common transactions attracting CVA involve 
interest rate derivatives
, 
foreign exchange derivatives
, and combinations thereof. 
CVA has a specific 
capital charge
 under 
Basel III
, and may also result in earnings volatility under 
IFRS 13
, and is therefore managed by a specialized desk.
CVA is one of a family of related valuation adjustments, collectively 
xVA
;  for further context here see 
Financial economics § Derivative pricing
.





Calculation
[
edit
]


Further information: 
XVA § Valuation adjustments


In 
financial mathematics
 one defines CVA as the difference between the risk-free portfolio value and the true 
portfolio value
 that takes into account the possibility of a 
counterparty
's default. 
In other words, CVA is the 
market value
 of 
counterparty credit risk
. 
This price adjustment will depend on counterparty 
credit spreads
 as well as on the market risk factors that drive derivatives' values and, therefore, exposure. 
It is typically calculated under 
a simulation framework
.
[
4
]


[
5
]


[
6
]

(Which can become computationally intensive; see 
[
b
]
.)



Risk-neutral expectation
[
edit
]


Unilateral CVA is given by the 
risk-neutral
 expectation of the discounted loss. The risk-neutral expectation can be written 

[
2
]


[
8
]

as













C


V


A


(


T


)




=




E




Q






[




L




∗






]


=




∫




0






T








E




Q








[










L


G


D








B




0








B




t










E


(


t


)






|






t


=


τ




]




d




P


D




(


0


,


t


)






{\displaystyle \mathrm {CVA(T)} =E^{Q}[L^{*}]=\int _{0}^{T}E^{Q}\left[\left.LGD{\frac {B_{0}}{B_{t}}}E(t)\;\right|\;t=\tau \right]d\mathrm {PD} (0,t)}






where 








T






{\displaystyle T}




  is the 
maturity
 of the longest transaction in the portfolio, 










B




t










{\displaystyle B_{t}}




 is the future value of one unit of the 
base currency
 invested today at the prevailing interest rate for maturity 








t






{\displaystyle t}




, 








L


G


D






{\displaystyle LGD}




 is the 
loss given default
, 








τ






{\displaystyle \tau }




 is the time of default, 








E


(


t


)






{\displaystyle E(t)}




 is the exposure at time 








t






{\displaystyle t}




, and 










P


D




(


s


,


t


)






{\displaystyle \mathrm {PD} (s,t)}




 is the risk neutral probability of counterparty default between times 








s






{\displaystyle s}




 and 








t






{\displaystyle t}




.
These probabilities can be obtained from the term structure of 
credit default swap
 (CDS) spreads.



Exposure, independent of counterparty default
[
edit
]


Assuming independence between exposure and counterparty's 
credit quality
 greatly simplifies the analysis. Under this assumption this simplifies to













C


V


A




=


L


G


D




∫




0






T










E


E






∗






(


t


)


 


d




P


D




(


0


,


t


)






{\displaystyle \mathrm {CVA} =LGD\int _{0}^{T}\mathrm {EE} ^{*}(t)~d\mathrm {PD} (0,t)}






where 












E


E






∗










{\displaystyle \mathrm {EE} ^{*}}




 is the risk-neutral discounted expected exposure (EE):















E


E






∗






(


t


)


=




E






[










B




0








B




t










 


E


(


t


)




]








{\displaystyle \mathrm {EE} ^{*}(t)=\mathbb {E} \left\lbrack {{\frac {B_{0}}{B_{t}}}~E(t)}\right\rbrack }






Approximation
[
edit
]


The full calculation of CVA, as above, is via a 
Monte-Carlo simulation
 on all risk factors; this is computationally demanding. 
There exists a simple 
approximation
 for CVA, sometimes referred to as the "net current exposure method".
[
5
]
 This consists in: buying default protection, typically a 
credit default swap
, netted for each counterparty; and the CDS price may then be used to 
back out
 the CVA charge.
[
5
]
[
9
]




Accounting treatment
[
edit
]


The CVA charge may be seen as an 
accounting adjustment
 made to 
reserve
 a portion of profits on uncollateralized financial derivatives. These reserved profits can be viewed as the 
net present value
 of the 
credit risk
 embedded in the transaction. Thus, as outlined, under 
IFRS 13
 changes in counterparty risk will result in earnings volatility; see 
XVA § Accounting impact
 and next section.



Function of the CVA desk
[
edit
]


Further information: 
XVA § Accounting impact
, and 
Financial risk management § Banking


In the course of trading and investing, Tier 1  
investment banks
  generate counterparty 
EPE
 and 
ENE
 (expected positive/negative 
exposure
). Whereas historically, this exposure was a concern of both the 
front office
 trading desk and 
middle office finance teams
, increasingly CVA pricing and hedging is under the "ownership" of a centralized CVA lending and treasury desk.
[
10
]
[
11
]


In particular, this desk addresses volatility in earnings due to the abovementioned 
IFRS 13
 
accounting standard
 requiring that CVA be considered in 
mark-to-market
 accounting. The 
hedging
 here focuses on addressing changes to the counterparty's 
credit worthiness
, offsetting 
potential future exposure
 at a given quantile. Further, since under 
Basel III
, banks are required to hold specific 
regulatory capital
 on the net CVA-risk,
[
5
]
 the CVA desk is responsible also for managing (minimizing) the capital requirements under Basel.



See also
[
edit
]


Financial derivative


Potential future exposure


XVA


Notes
[
edit
]






^
 

A good introduction can be found in a paper by Michael Pykhtin and Steven Zhu.
[
2
]

Karlsson et al. (2016) present a numerical efficient method for calculating expected exposure, potential future exposure and CVA for interest rate derivatives, in particular Bermudan 
swaptions
.
[
3
]




^
 

According to the 
Basel Committee on Banking Supervision
's July 2015 consultation document regarding CVA calculations, if CVA is calculated using 100 timesteps with 10,000 scenarios per timestep, 1 million 
simulations
 are required to compute the value of CVA. Calculating CVA risk would require 250 daily market risk scenarios over the 12-month stress period. CVA has to be calculated for each market risk scenario, resulting in 250 million simulations. These calculations have to be repeated across 6 risk types and 5 liquidity horizons, resulting in potentially 8.75 billion simulations.
[
7
]






References
[
edit
]






^
 
Basel Committee
 (2020). 
Credit valuation adjustment framework




^ 
a
 
b
 
Pykhtin, M.; Zhu, S. (July 2007). 
"A Guide to Modeling Counterparty Credit Risk"
. 
GARP Risk Review
. 
SSRN
 
1032522
.




^
 
Patrik Karlsson, Shashi Jain. and Cornelis W. Oosterlee (2016). 
"Credit Exposures for Interest Rate Derivatives using the Stochastic Grid Bundling Method"
. 
Applied Mathematical Finance
.




^
 
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
 
Harvey Stein (2012). 
"Counterparty Risk, CVA, and Basel III"




^
 
CVA calculation example: 
Monte-Carlo with Python




^
 
Alvin Lee (17 August 2015). 
"The Triple Convergence Of Credit Valuation Adjustment (CVA)"
. Global Trading. Archived from 
the original
 on 11 September 2015
. Retrieved 
19 August
 2015
.




^
 
European Banking Authority
 (25 February 2015). 
"EBA Report on CVA"
 
(PDF)
. EBA. Archived from 
the original
 
(PDF)
 on 2015-06-07.




^
 
"Example calculation"
. 7 October 2013. Archived from 
the original
 on 2023-06-03.




^
 
Kenneth Kapner and Charles Gates (2016). 
"The Long and Short of It: An Overview of XVA"
. 
GFMI




^
 
James Lee (2010). 
Counterparty credit risk pricing, assessment, and dynamic hedging
, 
Citigroup Global Markets










External links
[
edit
]


Corporate Finance Institute
 (N.D.). 
Credit Valuation Adjustment (CVA)


Laura Ballotta, Gianluca Fusai and Marina Marena (2016). 
"A Gentle Introduction to Default Risk and Counterparty Credit Modelling"
. 
SSRN
 
281635










Retrieved from "
https://en.wikipedia.org/w/index.php?title=Credit_valuation_adjustment&oldid=1318191211
"


Categories
: 
Actuarial science
Mathematical finance
Credit risk
Monte Carlo methods in finance
Hidden categories: 
Articles with short description
Short description matches Wikidata














 This page was last edited on 22 October 2025, at 13:00
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
















Credit valuation adjustment


























































6 languages






Add topic



































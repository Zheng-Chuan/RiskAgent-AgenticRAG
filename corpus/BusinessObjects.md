# Business Objects Dictionary

目标: 用工程师能落地的方式解释风险系统里常见业务对象
这些对象会出现在数据模型 API 字段 风控规则与报表里

## Position

Position 是头寸
可理解为一笔交易或一组交易在某个维度上的持仓/敞口表示

常见字段

- position_id
- security_id
- quantity / notional
- price / pv
- greeks: delta gamma vega theta
- desk book trader
- as_of

## Security

Security 是金融工具标的
例如股票 债券 期权 掉期

常见字段

- security_id
- type (equity bond option swap)
- currency
- maturity
- underlying

## Desk

Desk 是交易台
用于组织管理一组书本或交易员的交易活动

常见字段

- desk_id / desk_name
- business_line
- risk_limits

## Trader

Trader 是交易员
对应具体的人或席位 归属到 desk

常见字段

- trader_id
- desk_id

## Book

Book 是账本
用于进一步聚合/归集头寸
常用于风险归因与报表切片

常见字段

- book_id
- desk_id

## Exposure

Exposure 是敞口
一种风险度量 可以来自 PV Greeks VaR 等
通常会对多个 risk factors 求聚合

## Limit

Limit 是阈值
当 Exposure 超过 Limit 时触发 breach
用于风险监控与告警


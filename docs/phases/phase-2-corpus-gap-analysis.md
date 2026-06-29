# Phase 2 Corpus Gap Analysis

## 目标

记录当前 `qrels` 升级过程中发现的语料缺口.  
这些缺口不是评测脚本问题.  
而是当前索引语料里没有足够硬的一跳证据.

## 已完成

- `tests/data/qrels.json` 已有第一批 `chunk_id backed qrels`
- FRTB
- Greeks 基础三项
- CVA
- XVA 子项
- VaR
- Expected Shortfall
- Initial margin
- Variation margin

## 当前缺口

### 1. Greeks 扩展概念缺口

这些问题在当前索引语料中缺少稳定的一跳定义 chunk.

- `q31` Theta
- `q32` Rho
- `q33` Volga
- `q34` Vanna
- `q35` Charm
- `q36` implied vs historical volatility
- `q37` delta-neutral portfolio
- `q38` gamma hedging
- `q39` volatility skew
- `q40` volatility smile

### 2. Counterparty 风险扩展缺口

- `q45` right-way risk

当前语料里已经有 `wrong-way risk` 的提法  
但还没有足够稳定的 `right-way risk` 定义 chunk.

## 建议补语料方向

### A. 补一份 Greeks 扩展语料

最小覆盖下面这些概念.

- Theta
- Rho
- Volga
- Vanna
- Charm
- implied volatility
- historical volatility
- delta-neutral
- gamma hedging
- volatility skew
- volatility smile

### B. 补一份 Counterparty 风险术语语料

最小覆盖下面这些概念.

- wrong-way risk
- right-way risk
- CSA
- netting set
- initial margin
- variation margin

## 原则

- 不为了把 `qrels` 数字做漂亮而硬绑错误 chunk
- 先承认语料缺口
- 再补语料和重建索引
- 最后继续把 `text qrel` 升级成 `chunk_id qrel`

## 下一步

1. 补 `Greeks 扩展语料`
2. 补 `Counterparty 风险术语语料`
3. 重建索引
4. 继续硬化剩余 qrels

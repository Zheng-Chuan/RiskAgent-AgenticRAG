# Phase 2 Corpus Gap Analysis

## 目标

记录 `qrels` 升级过程中曾经发现的语料缺口以及当前回填状态.  
这些 gap 的重点不是把指标做漂亮.  
而是确保索引语料里真的有足够硬的一跳证据.

## 已完成

- `tests/data/qrels.json` 已有第一批 `chunk_id backed qrels`
- FRTB
- Greeks 基础三项
- Greeks 扩展概念
- CVA
- XVA 子项
- VaR
- Expected Shortfall
- Initial margin
- Variation margin
- right-way risk

## 当前状态

此前文档里列出的 Phase 2 gap 目前已经在仓库中完成了最小闭环.

- `corpus/Background.md` 已补入 `Theta` `Rho` `Volga` `Vanna` `Charm`
- 同一文件已补入 `implied volatility` `historical volatility` `delta-neutral portfolio` `gamma hedging`
- 同一文件已补入 `volatility skew` `volatility smile`
- `counterparty risk` 部分已补入 `right-way risk`
- `tests/data/qrels.json` 已为 `q31-q40` 和 `q45` 提供 `chunk_id` 级 qrels

## 已关闭的缺口

### 1. Greeks 扩展概念

下面这些问题现在都已经有稳定的一跳定义 chunk 和对应 qrels.

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

### 2. Counterparty 风险扩展概念

- `q45` right-way risk

## 收口说明 (2026-08-25)

- 语料 gap 已完成最小闭环, qrels 全部 chunk_id 级, `qrels_gap_allowlist.json` 保持清空
- `retrieval eval` 命中规则硬化与 fresh baseline 已完成 (v10b-v10f 全量评测落盘, 见 [评测台账](../evaluations/EVALUATION_LOG.md))
- 文档中的 gap 关闭必须以语料和 qrels 都已经落盘为前提
- gap 关闭后仍然要继续把 `retrieval eval` 做硬 不能靠旧 sample 掩盖问题
- 当前仓库里的 `tests/data/qrels_gap_allowlist.json` 已经清空
- 这表示当前数据集不再允许未审批的 text only qrel 直接混入评测
- 如果必须临时保留 text only qrel 仍然要同步白名单和原因 否则数据加载会失败

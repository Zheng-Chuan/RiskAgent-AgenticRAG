# Phase 3 Evaluation Hardening

## 目标

把 retrieval generation gate 三层评测口径继续做硬.

## 时间

2-3 周

## 本阶段重点

- retrieval metrics 和 citation diagnostics 继续拆清楚
- answer eval 和 domain consistency 继续固定口径
- gate 指标继续基于标注样本做统计
- 报告元信息继续完善到可复现级别

## P0 必须先做

### 1. retrieval eval 单位继续做硬

- 把 retrieval 指标和 evidence unit 继续对齐
- 明确 qrels 命中规则和边界
- 让 retrieval report 更能指导召回优化

### 2. metrics 分层继续做清楚

- retrieval metrics
- answer metrics
- gate metrics

这三层必须继续独立展示  
避免一个总分掩盖问题来源

### 3. 报告元信息补全

- dataset version
- retrieval pipeline version
- reranker model
- index version
- prompt version

确保任何一次报告都可以回溯配置上下文

### 4. gate 样本继续扩充

- refusal
- evidence mismatch
- numeric mismatch

让 gate benefit false kill miss rate 更有统计意义

## P1 随后做

### 5. 题型 slice 报告强化

- definition
- compare
- numeric
- regulation

按题型稳定输出 retrieval 和 answer 两层 slice 结果

### 6. retrieval cost latency 指标

- fanout 数量
- rerank pairs
- node latency
- estimated tokens

让召回优化不脱离成本视角

### 7. 数值题专项评测

- 更细地统计 numeric consistency
- 继续增强金融术语和数值口径的失败明细

## 建议交付

- 更强的数据集字段定义
- 更可信的基准报告
- 更清晰的阈值门禁和 regression 展示
- 更细的 slice 指标和运行成本指标

## 验收标准

- 评测报告可以直接支持发布判断
- 指标变化能定位到 retrieval 或 generation 或 gate
- 关键数字都能反查到具体报告

## 不做什么

- 不把评测重新退化成单一主观 LLM 分数
- 不让 demo 表现替代报告口径
- 不把 retrieval 和 generation 指标混成一个总分

## 退出标准

- 报告已经可以直接支持 release gate
- 关键题型的 retrieval 和 answer 指标都能单独下钻
- gate 样本统计不再过于单薄
- 后续任何 retrieval 改动都能被更可靠地评估

## 状态

In Progress

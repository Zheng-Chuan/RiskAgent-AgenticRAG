# ADR-002 Evidence First Validation

## 状态

Accepted

## 背景

如果系统只输出自然语言答案 而没有结构化证据链 后续的评测 排障 和发布门禁都会变弱.

## 决策

系统回答阶段除了 `answer` 以外 还要稳定输出:

- `citations`
- `claims`
- `evidence_set`
- `decision_log`

后置门禁默认使用:

- `refusal gate`
- `evidence gate`
- `numeric gate`

## 后果

### 正面

- 可追溯性明显增强
- 更适合做 release gate
- 更适合做金融领域问责和复盘

### 代价

- 生成和校验链路更复杂
- 需要维护 claims 和 evidence 的对齐质量

## 相关文件

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [gates.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_agenticrag/validators/gates.py)

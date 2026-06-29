# ADR-003 Evaluation First Release Gate

## 状态

Accepted

## 背景

如果发布验收只看 demo 或主观体验 项目会很快漂移到宣传口径大于真实能力.

## 决策

发布验收必须优先依赖评测报告和阈值判断.  
系统要把 `retrieval metrics` `answer metrics` `gate metrics` 分层输出.  
README 和对外口径只引用能映射到具体报告的结论.

## 后果

### 正面

- 对外可信度更高
- 方便做 regression 和基线比较
- 文档更容易和真实实现保持一致

### 代价

- 需要持续维护数据集和基准报告
- 评测口径不够硬时 会直接暴露系统短板

## 相关文件

- [PRD.md](../PRD.md)
- [run.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_agenticrag/evaluation/run.py)

# RiskAgent-AgenticRAG PRD

## 1. 文档目标

本文档是 `RiskAgent-AgenticRAG` 的产品总纲.  
详细的战略 技术决策 分阶段规划和运行时主链分别沉淀在独立文档中.

- 产品战略与长期方向: [docs/STRATEGY.md](./STRATEGY.md)
- 技术决策记录: [docs/decisions/](./decisions/)
- 分阶段规划: [docs/phases/](./phases/)
- 系统架构: [docs/ARCHITECTURE.md](./ARCHITECTURE.md)
- 对外表述: [docs/RESUME.md](./RESUME.md)

---

## 2. 项目定位

把 `RiskAgent-AgenticRAG` 做成一个非常强的高可信 RAG 项目.  
重点不在做巨无霸 Agent 平台.  
重点在把 `文档检索` `召回质量` `证据对齐` `评测可信度` `发布门禁` 做到顶级.

### 2.1 成功标准

- 主链固定为统一高可信 RAG 工作流 而不是不断切 mode
- 检索层必须在金融文档问答上稳定覆盖 `术语` `缩写` `条款` `数值条件` 这几类难点
- 每个回答都能回溯到 `citations` `claims` `evidence_set` 和 `decision_log`
- 评测必须把 `retrieval` `generation` `gate` 三层分开统计
- 任意一次结论都能追溯到 `数据集版本` `检索配置` `模型版本` `报告产物`

### 2.2 非目标

- 不做通用办公 Agent
- 不做重型多智能体协作平台
- 不做任务完成率导向的 workflow orchestration
- 不做无边界的工具调用扩张
- 不做和检索召回无关的功能堆砌

本项目只做一件事.  
把高可信文档问答里的检索和证据链做硬.

---

## 3. 核心用户与场景

### 3.1 核心用户

- 风控分析师
- Desk Risk Manager
- 监管与合规研究人员
- 金融知识库平台研发

### 3.2 核心场景

- 查询某监管条款或风险术语的定义与边界
- 比较两个规则口径 差异和适用条件
- 询问某个数值限制 是否 breach 以及证据来自哪里
- 对一份金融文档集合做高可信问答 并要求答案带引用
- 对一次回归改动判断 检索召回是否退化

---

## 4. 架构约束

系统始终保持 `高可信 RAG` 作为核心边界.  
可以有窄工具增强 但不能演化成无限扩张的 Agent 平台.

- 主链保持 `rewrite -> retrieve_and_critique -> revise_query loop -> synthesize_answer -> validate_and_save`
- 运行时统一走一条默认检索链 不再保留多套对外主模式
- 检索默认包含 `Hybrid Retrieval` `Query Intelligence` `Advanced Index`
- 输出必须包含结构化证据链
- 发布门禁必须以评测报告和阈值判断为准 不以主观演示为准

> 详见 [ADR-001](./decisions/ADR-001-unified-retrieval-pipeline.md)

---

## 5. 核心里程碑

| 阶段 | 目标 | 状态 | 详情 |
| :--- | :--- | :--- | :--- |
| Phase 0 | 对齐项目边界和文档口径 | ✓ 完成 | [phase-0-alignment.md](./phases/phase-0-alignment.md) |
| Phase 1 | 收敛统一高可信 RAG 主链 | ✓ 完成 | [phase-1-unified-rag-pipeline.md](./phases/phase-1-unified-rag-pipeline.md) |
| Phase 2 | 检索与召回强化 | △ 部分完成 | [phase-2-retrieval-hardening.md](./phases/phase-2-retrieval-hardening.md) |
| Phase 3 | 评测与门禁强化 | △ 部分完成 | [phase-3-evaluation-hardening.md](./phases/phase-3-evaluation-hardening.md) |
| Phase 4 | 发布与回归稳定化 | △ 部分完成 | [phase-4-release-readiness.md](./phases/phase-4-release-readiness.md) |

---

## 6. 关键技术决策

| 决策 | 状态 | 文档 |
| :--- | :--- | :--- |
| 统一默认检索主链 | Decided | [ADR-001](./decisions/ADR-001-unified-retrieval-pipeline.md) |
| 证据优先和后置 gate | Decided | [ADR-002](./decisions/ADR-002-evidence-first-validation.md) |
| 评测优先于演示口径 | Decided | [ADR-003](./decisions/ADR-003-evaluation-first-release-gate.md) |
| 下一阶段检索强化提案 | Proposed | [RFC-001](./decisions/RFC-001-retrieval-hardening-roadmap.md) |

---

## 7. 功能需求清单

| 编号 | 需求 | 关联阶段 |
| :--- | :--- | :--- |
| FR-1 | 系统必须支持统一检索主链和可控 revise loop | [Phase 1](./phases/phase-1-unified-rag-pipeline.md) |
| FR-2 | 系统必须支持 hybrid retrieval 与 rerank | [Phase 2](./phases/phase-2-retrieval-hardening.md) |
| FR-3 | 系统必须支持 query intelligence 和 advanced index | [Phase 2](./phases/phase-2-retrieval-hardening.md) |
| FR-4 | 系统必须支持 citations claims evidence_set decision_log | [Phase 1](./phases/phase-1-unified-rag-pipeline.md) |
| FR-5 | 系统必须支持 refusal evidence numeric 三类 gate | [Phase 3](./phases/phase-3-evaluation-hardening.md) |
| FR-6 | 系统必须支持 retrieval eval 与 answer eval 分离统计 | [Phase 3](./phases/phase-3-evaluation-hardening.md) |
| FR-7 | 系统必须支持离线回归和最小发布验收 | [Phase 4](./phases/phase-4-release-readiness.md) |

---

## 8. 非功能需求

- NFR-1: 检索结果必须可追溯到 source chunk 和 evidence
- NFR-2: 指标计算必须可复现
- NFR-3: 检索配置变化必须能反映到报告元信息
- NFR-4: 文档与代码口径必须同步
- NFR-5: 任何对外宣称的能力都必须能被测试或报告反查

---

## 9. 当前主要问题

- qrels 评测单位还不够硬 当前更偏 text 级匹配 不是严格 chunk gold
- Self-RAG 充分性判断还偏轻 主要是规则阈值和 prompt critique
- 索引一致性还不够强 embedding 和 chunking 版本没有做硬版本键
- reranker 还是通用 baseline 模型 领域适配不足
- 文档口径刚开始收口 还需要继续和实现保持同频

---

## 10. 发布准入标准

以下条件同时满足 才允许对外按强 RAG 项目来讲.

- 默认主路径和文档描述一致
- retrieval metrics answer metrics gate metrics 分离输出
- 仓库内有可复核基准报告
- 核心测试和最小发布验收命令通过
- README PRD ARCHITECTURE phases decisions 之间没有明显冲突表述

---

## 11. 最终交付物

- 统一高可信 RAG 架构代码和文档
- 检索评测数据和报告样例
- 结构化证据链输出
- 确定性 gate 模块
- 最小发布验收命令
- 和代码实现严格一致的对外表述

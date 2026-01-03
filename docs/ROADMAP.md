# 开发计划

采用最小可运行 demo -> 逐步扩充的策略. 目标是基于金融衍生品与风险管理资料, 为企业内部软件工程师提供通俗易懂且可追溯引用来源的业务解释, 降低理解门槛.

## 当前技术栈

- UI: Gradio
- Multi-agent orchestration: LangGraph
- RAG framework: LangChain
- Vector store: Chroma
- Runtime env: conda env LangChain

## 2026-01 1 个月交付目标

定位: 以 AI Agent 能力展示为第一优先级.

硬性验收口径:

- 端到端可复现: 清空索引 -> ingest -> 查询 -> 返回 answer + citations.
- 可控与可测: 至少 1 条 e2e smoke test, 评测脚本可一键运行并输出报告.
- 工程化底线: 无明文 secrets, 关键链路带 request id, 错误分层清晰.

### Week 1: baseline 跑通 + 工程化骨架

- 交付
  - requirements.txt 与 Python 版本固化
  - secrets 全部走环境变量
  - 最小 CLI 或 Gradio UI 启动
  - 最小 ingest -> retrieve -> answer 流程
- 验收
  - 1 条命令启动 demo
  - 返回 citations, 且可定位来源

### Week 2: RAG MVP 闭环与引用质量

- 交付
  - docs/sources 语料接入(至少包含 Background.md)
  - chunk 规则与 metadata schema 固化
  - 20 个种子问题集
- 验收
  - 20 个问题中, 80% 以上回答包含有效 citations

### Week 3: 多智能体编排与可控性

- 交付
  - LangGraph 编排最小多角色流程(例如 researcher -> writer -> reviewer)
  - guardrails: 无法从语料支持则拒答或要求补充资料
  - 评测脚本: 输出 citations coverage 与 groundedness 指标(可简化)
- 验收
  - 评测脚本可一键运行并输出报告
  - 失败路径可解释, 日志可定位

### Week 4: 收尾, 文档, Demo 固化

- 交付
  - README 一键运行, 常见问题与排障
  - demo 脚本: 1 条端到端演示路径
  - 3-5 条简历 bullet(量化指标优先)
- 验收
  - 新人按 README 10-15 分钟可跑通 demo

## 设计与阶段拆分(用于实现路径)

说明: 下述 Phase 用于组织工程工作, 但 2026-01 内按上面的 4 周计划完成交付.

## Phase 0: 基础强化与项目骨架

**目标**: 先把工程化基础打牢, 让后续迭代稳定可扩展.

- [ ] 确认 conda 环境 LangChain 可用, 固化 Python 版本
- [ ] 增加 requirements.txt, 不 pin 版本, 以当前环境为准
- [ ] 配置管理与 secrets 管理, 统一使用环境变量, 禁止明文 key
- [ ] 统一日志与错误分层, 关键链路打上 request id
- [ ] 增加最小测试框架, 至少覆盖 1 条端到端 smoke test
- [ ] 定义核心抽象
  - 文档源与元数据 schema
  - chunk schema
  - embedding provider 接口
  - vector store 接口(Chroma)
  - graph state schema(LangGraph)
  - retrieval 输出 schema, 必须包含 citations

**验收标准**:

- 项目可在本地一键启动或一键运行 demo
- 无明文 secrets
- 至少 1 条端到端测试可通过

## Phase 1: RAG MVP, 面向工程师的业务解释

**目标**: 跑通 ingest -> index -> retrieve -> generate 的闭环, 输出带引用的解释结果.

### 1.1 资料与数据接入

- [ ] 定义资料目录约定, 例如 docs/sources
- [ ] 接入第 1 批语料
  - Background.md
  - 可选: 公开可引用的 FRTB, CVA, Greeks, XVA 资料
- [ ] 文档解析
  - markdown 解析
  - 可选: pdf 解析

### 1.2 切分与索引策略

- [ ] chunk 策略
  - 以标题层级优先, 再按长度切分
  - chunk 必须携带 section path 与来源定位
- [ ] embeddings
  - 支持可插拔 provider, 默认采用 OpenAI compatible API
- [ ] vector store
  - 本地优先, 例如 Chroma

### 1.3 生成与引用

- [ ] 统一回答模板, 面向软件工程师
  - TLDR
  - 概念解释
  - 为什么重要
  - 在系统里的常见数据流与字段
  - 典型示例
  - citations
- [ ] 引用规则
  - 每个关键结论必须能对应到至少 1 个 chunk
  - 模型不确定时必须说明不确定并给出下一步建议

### 1.4 最小交互形态

- [ ] CLI
  - ingest
  - chat
  - ask
- [ ] 可选: 简单 Web UI, 例如 Gradio

**验收标准**:

- 给定 20 个种子问题, 80% 以上回答包含有效 citations
- 端到端流程可复现
  - 清空索引 -> ingest -> 查询 -> 返回答案

## Phase 2: 质量提升, 可评测与可控

**目标**: 降低幻觉, 提升检索命中与解释质量, 形成可迭代的评测体系.

- [ ] 建立评测集
  - 检索相关性
  - 事实一致性与引用覆盖
  - 工程师可读性
- [ ] 增加 RAG 诊断
  - top k 命中率
  - chunk 覆盖率
  - answer faithfulness
- [ ] 增加 guardrails
  - 无法从语料支持则拒答或要求补充资料
  - 敏感信息与合规提示
- [ ] 领域知识增强
  - 术语表与缩写表
  - 业务对象字典, 例如 position, security, desk, trader

**验收标准**:

- 评测脚本可一键运行并输出报告
- 相比 Phase 1, 事实一致性指标显著提升

## Phase 3: 内部服务化与企业落地

**目标**: 以内部服务形式提供能力, 支持权限, 审计, 可观测.

- [ ] 服务化接口
  - FastAPI REST
  - 可选: MCP server, 让 agent 可编排
- [ ] 身份与权限
  - authn
  - RBAC
- [ ] 可观测性
  - structured logs
  - metrics
  - tracing
- [ ] 部署
  - Docker
  - 可选: k8s

**验收标准**:

- 支持最小权限访问与审计日志
- 关键接口具备 p95 latency 与 error rate 指标

## 时间规划

| Phase | 预计时间 | 关键里程碑 |
| ----- | -------- | ---------- |
| Phase 0 | Week 1 | 项目骨架与工程化基础 |
| Phase 1 | Week 2 | RAG MVP 闭环与可复现 demo |
| Phase 2 | Week 3 | 评测体系与质量提升 |
| Phase 3 | Week 4 | 文档固化与最小服务化能力 |

**总计**: 4 周

## 开发建议

1. 每完成一个 Phase 就提交 Git, 保持可回溯
2. 以数据口径与引用为第一优先级, 宁可少答也不要编造
3. 每周至少 1 次 demo, 记录输入输出与问题清单
4. 先做 CLI 后做 UI, 降低早期复杂度

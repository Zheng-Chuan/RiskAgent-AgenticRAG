# 开发计划

采用最小可运行 demo -> 逐步扩充的策略. 目标是基于金融衍生品与风险管理资料, 为企业内部软件工程师提供通俗易懂且可追溯引用来源的业务解释, 降低理解门槛.

## 当前技术栈

- UI: Gradio
- Multi-agent orchestration: LangGraph
- RAG framework: LangChain
- Vector store: Chroma
- Runtime env: conda env LangChain

## MVP Sprint: <= 2026-01-01

**目标**: 可运行, 可用, 可演示. 不追求最佳效果.

- [ ] conda env LangChain 可用, pip 安装 requirements.txt
- [ ] Gradio 启动最小 chat UI
- [ ] 从 docs/sources 加载 markdown, 切分成 chunks
- [ ] 用任意可用 embeddings 建立 Chroma index
- [ ] LangGraph 编排最小流程: retrieve -> answer
- [ ] 输出 answer + citations

**验收标准**:

- 本地 1 条命令即可启动 UI
- UI 可 build index, 可提问, 可返回 citations
- 错误可见, 关键日志可定位

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
| MVP Sprint | 1-2 天 | Gradio + LangGraph + Chroma 端到端跑通 |
| Phase 0 | 1 周 | 项目骨架与工程化基础 |
| Phase 1 | 1-2 周 | RAG MVP 闭环与可复现 demo |
| Phase 2 | 2-3 周 | 评测体系与质量提升 |
| Phase 3 | 1-2 周 | 服务化与企业落地能力 |

**总计**: MVP 1-2 天 + 5-8 周

## 开发建议

1. 每完成一个 Phase 就提交 Git, 保持可回溯
2. 以数据口径与引用为第一优先级, 宁可少答也不要编造
3. 每周至少 1 次 demo, 记录输入输出与问题清单
4. 先做 CLI 后做 UI, 降低早期复杂度

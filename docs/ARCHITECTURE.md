# 系统架构

## 整体架构

RiskAgent-AgenticRAG 是一个面向金融风险领域的 Agentic RAG 系统，采用模块化设计，主要分为三大核心模块：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RiskAgent-AgenticRAG                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────────┐ │
│  │   Indexing   │  │   Querying   │  │        Evaluation             │ │
│  │   模块       │  │   模块       │  │        模块                   │ │
│  │              │  │              │  │                               │ │
│  - 文档预处理   │  - 多轮检索    │  - 指标计算                      │ │
│  - 分块         │  - Agentic Loop │  - 报告生成                      │ │
│  - 索引构建     │  - 答案合成    │  - 阈值门禁                      │ │
│  - 持久化       │  - 引用追踪    │  - 退化检测                      │ │
│  └──────────────┘  └──────────────┘  └───────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. Indexing 模块 (索引构建)

**职责**:
- 文档加载与预处理
- 文档分块 (Chunking)
- 向量化 (Embedding)
- 索引构建 (向量索引 + 关键词索引)
- 增量索引

**主要文件**:
- `src/riskagent_agenticrag/indexing/indexer.py` - 索引构建器
- `src/riskagent_agenticrag/indexing/milvus_store.py` - Milvus 存储
- `src/riskagent_agenticrag/rag/chunking.py` - 文档分块
- `src/riskagent_agenticrag/rag/embeddings.py` - 向量化
- `src/riskagent_agenticrag/rag/source_loader.py` - 文档加载

**详细文档**: [INDEX.md](./INDEX.md)

---

### 2. Querying 模块 (查询与推理)

**职责**:
- 多轮检索 (Agentic Loop)
- 查询改写
- 检索质量评估 (Self-RAG)
- 工具调用 (DataAgent)
- 答案合成
- 引用生成
- 响应验证

**主要文件**:
- `src/riskagent_agenticrag/orchestration/langgraph_runner.py` - LangGraph 编排
- `src/riskagent_agenticrag/orchestration/nodes.py` - Agentic Loop 节点
- `src/riskagent_agenticrag/rag/retriever_factory.py` - 检索器工厂
- `src/riskagent_agenticrag/rag/hybrid_retriever.py` - 混合检索
- `src/riskagent_agenticrag/rag/self_rag.py` - Self-RAG 评分
- `src/riskagent_agenticrag/agents/data_agent.py` - DataAgent 工具

**详细文档**: [QUERY.md](./QUERY.md)

---

### 3. Evaluation 模块 (评估)

**职责**:
- 多维度指标计算
- 评估报告生成
- 阈值门禁策略
- 退化检测与基线比较
- 指标计算工具

**主要文件**:
- `src/riskagent_agenticrag/evaluation/run.py` - 端到端评估入口
- `src/riskagent_agenticrag/evaluation/ragas_metrics.py` - RAGAS 指标
- `src/riskagent_agenticrag/evaluation/domain_consistency.py` - 领域一致性
- `src/riskagent_agenticrag/evaluation/citation_precision.py` - 引用精度
- `src/riskagent_agenticrag/evaluation/advanced_metrics.py` - 高级指标
- `src/riskagent_agenticrag/evaluation/compute_metric.py` - 指标计算工具
- `src/riskagent_agenticrag/evaluation/reporting.py` - 报告与退化检测
- `src/riskagent_agenticrag/evaluation/thresholds.py` - 阈值配置

**详细文档**: [EVALUATION.md](./EVALUATION.md)

---

## 数据流动

```
Corpus (PDF/Word/HTML/Markdown)
    ↓
[Indexing 模块]
    ├─→ Chunking (文档分块)
    ├─→ Embedding (向量化)
    └─→ Index (索引构建)
         ↓
    Milvus 索引
         ↓
[Querying 模块]
    ├─→ Query Rewrite (查询改写)
    ├─→ Retrieve (混合检索)
    ├─→ Self-RAG (质量评估)
    ├─→ Tool Use (工具调用)
    ├─→ Synthesize (答案合成)
    └─→ Validate (响应验证)
         ↓
    带引用的可验证回答
         ↓
[Evaluation 模块]
    ├─→ 检索质量指标
    ├─→ 引用精度指标
    ├─→ 领域一致性指标
    ├─→ RAGAS 指标
    ├─→ 可靠性与成本指标
    └─→ 退化检测
         ↓
    评估报告 + 阈值门禁
```

---

## 技术栈

| 层次 | 技术选型 | 说明 |
|------|----------|------|
| 编排层 | LangGraph | Agentic Loop 工作流 |
| LLM 接入 | OpenAI 兼容 (OpenRouter) | 支持多种模型 |
| 向量数据库 | Milvus | 支持 Docker/Lite 模式 |
| 嵌入模型 | BAAI/bge-large-zh-v1.5 | 默认中文嵌入 |
| Web 框架 | FastAPI | HTTP API |
| 评估框架 | RAGAS + 自研 | 多维度评估 |

---

## 目录结构

```
src/riskagent_agenticrag/
├── agents/           # 智能体 (DataAgent)
├── api/              # HTTP API 服务
├── artifacts/        # Artifacts 存储
├── cli/              # 命令行工具
├── config/           # 配置管理
├── contracts/        # 数据契约
├── evaluation/       # 评估模块 (Evaluation)
├── indexing/         # 索引模块 (Indexing)
├── llm/              # LLM 调用
├── orchestration/    # 编排层
├── rag/              # RAG 核心 (Querying 模块主要部分)
├── tools/            # 工具集
├── validators/       # 验证器 (Gates)
└── app.py            # 系统入口
```

---

## 设计原则

1. **模块化**: 三大核心模块相对独立，边界清晰
2. **可观测性**: 完整的 trace 记录和 artifacts 落盘
3. **可验证性**: 所有回答附带引用，可回溯到原文
4. **评测驱动**: 完善的评估框架，支持阈值门禁和退化检测
5. **领域特定**: 针对金融风险领域优化（数值、术语一致性）

---

## 详细文档

- [INDEX.md](./INDEX.md) - Indexing 模块详细文档
- [QUERY.md](./QUERY.md) - Querying 模块详细文档
- [EVALUATION.md](./EVALUATION.md) - Evaluation 模块详细文档
- [DATA.md](./DATA.md) - 数据说明

# Querying 模块

Querying 模块负责处理用户查询，通过 Agentic Loop 进行多轮检索、工具调用、答案合成，最终生成带引用的可验证回答。

## 模块职责

| 职责 | 说明 |
|------|------|
| 查询改写 | 优化用户问题以提高检索质量 |
| 混合检索 | Dense + Sparse 混合检索，重排优化 |
| 检索质量评估 | Self-RAG 评分，评估上下文质量 |
| 工具调用 | DataAgent 获取结构化数据 |
| 答案合成 | 基于上下文合成带引用的答案 |
| 引用生成 | 生成可追溯的引用标记 |
| 响应验证 | 验证响应质量，支持申诉机制 |

## 主要文件

| 文件 | 说明 |
|------|------|
| `orchestration/langgraph_runner.py` | LangGraph 工作流编排 |
| `orchestration/nodes.py` | Agentic Loop 节点实现 |
| `orchestration/state.py` | 工作流状态定义 |
| `rag/retriever_factory.py` | 检索器工厂 |
| `rag/hybrid_retriever.py` | 混合检索（Dense + Sparse） |
| `rag/self_rag.py` | Self-RAG 评分 |
| `agents/data_agent.py` | DataAgent 工具 |
| `app.py` | RiskAgentSystem 统一入口 |

## Agentic Loop 工作流

```
__start__
    ↓
[rewrite] 查询改写
    ↓
[retrieve_and_critique] 检索 + 质量评估
    ↓
[continue?]
    ├─→ yes → [revise_query] 修订查询
    │               ↓
    │         返回检索
    │
    └─→ no → [decide_tool_use] 决策是否调用工具
                     ↓
              [call_tool?]
                  ├─→ yes → [call_tool] 调用 DataAgent
                  │               ↓
                  │         [synthesize_answer] 答案合成
                  │
                  └─→ no → [synthesize_answer] 答案合成
                                   ↓
                          [validate_and_save] 验证与落盘
                                   ↓
                               __end__
```

## 节点说明

| 节点 | 职责 |
|------|------|
| `rewrite` | 查询改写，优化问题以提高检索质量 |
| `retrieve_and_critique` | 检索文档并进行 Self-RAG 质量评估 |
| `revise_query` | 基于检索评估结果修订查询 |
| `decide_tool_use` | 决策是否需要调用工具 |
| `call_tool` | 调用 DataAgent 获取结构化数据 |
| `synthesize_answer` | 合成最终答案并附加引用 |
| `validate_and_save` | 验证响应质量，保存 artifacts |

## 混合检索策略

Querying 模块采用高级检索策略：

| 层级 | 说明 |
|------|------|
| Dense Retrieval | 向量检索，语义相似性 |
| Sparse Retrieval | 关键词检索，BM25 |
| RRF Fusion | 混合排序融合 |
| Cross-Encoder Rerank | 重排优化 |

## 使用方式

### 1. CLI 方式

```bash
# 提问
python -m riskagent_agenticrag.cli ask \
  --question "what is FRTB" \
  --persist-dir .milvus
```

### 2. 代码方式

```python
from riskagent_agenticrag.app import RiskAgentSystem

system = RiskAgentSystem(persist_dir=Path(".milvus"))
response = system.chat(question="what is FRTB")
print(response.answer)
```

### 3. API 方式

```bash
# 启动服务
langgraph up --config langgraph.json

# 调用 API
POST /runs
```

## 可观测性

每次请求都会生成完整的 trace 和 artifacts：

- `trace.json` - 完整执行记录
- `artifacts/` - 落盘目录
- 节点级时延追踪

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统架构
- [EVALUATION.md](./EVALUATION.md) - 评估模块

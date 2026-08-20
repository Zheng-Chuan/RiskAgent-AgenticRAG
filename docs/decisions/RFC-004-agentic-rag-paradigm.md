# RFC-004 Agentic RAG 范式迁移

## 状态

Proposed (长期规划, P3)

## 目标

将 RAG 从 "预定义 pipeline" 迁移到 "模型自主检索" 范式.  
让 LLM 在推理过程中自主决定检索策略, 而不是走固定的 rewrite -> retrieve -> critique 链路.

## 背景

### 当前范式的局限

当前项目是预定义 pipeline:
```
rewrite -> retrieve_and_critique -> revise_query loop -> synthesize -> validate
```

问题:
- 所有查询走同一条链路, 简单查询过重, 复杂查询不够灵活
- query rewrite 是规则驱动的, 不是模型自主的
- 检索策略是固定的 (dense + BM25 + rerank), 不能根据问题类型动态选择
- 多跳推理靠 revise loop 迭代, 效率低且容易 context 膨胀

### 业界新范式

2025-2026 年学术界提出了多个 Agentic RAG 范式:

**A-RAG (arXiv 2602.03442, 2026.02)**:
- 层次化检索接口, 给模型三个工具: keyword_search / semantic_search / chunk_read
- 模型自主决定用哪个工具, 何时用, 用几次
- 论文证明即使最简单的 Naive Agentic RAG 也稳定优于 Naive RAG
- 随模型规模增长, 效果持续提升

**MARAG-R1 (arXiv 2510.27569, 2025.10)**:
- 用 RL 训练 LLM 动态协调 4 种检索工具
- 工具: semantic search / keyword search / filtering / aggregation
- 在 GlobalQA / HotpotQA / 2WikiMultiHopQA 上达到 SOTA
- 学会了 "何时用哪个工具" 的策略

**ReaLM-Retrieve (SIGIR 2026)**:
- 步级不确定性检测, 推理模型的感知检索
- 10.1% F1 提升, 47% 更少检索调用
- 核心思想: 模型在推理的每一步自己决定是否需要检索

## 提案

### 分阶段迁移

#### 阶段一: 工具化检索 (P3-1)

把现有检索能力封装为 LLM 可调用的工具:

```python
tools = [
    {
        "name": "semantic_search",
        "description": "基于语义相似度检索文档, 适合概念性查询",
        "params": {"query": str, "top_k": int}
    },
    {
        "name": "keyword_search",
        "description": "基于关键词检索文档, 适合术语/编号/精确匹配",
        "params": {"query": str, "top_k": int}
    },
    {
        "name": "structured_lookup",
        "description": "按 source/section/parent 精确定位文档块",
        "params": {"source": str, "section_path": str}
    },
    {
        "name": "chunk_read",
        "description": "读取指定 chunk_id 的完整内容和上下文",
        "params": {"chunk_id": str}
    }
]
```

模型在推理过程中自主决定:
- 用哪个工具
- 用什么参数
- 用几次
- 何时停止检索

#### 阶段二: 多跳推理优化 (P3-2)

引入 SEAL-RAG 的 "替换而非扩展" 策略:
- 多跳推理时, 维护固定 budget 的证据集 (如 top-5)
- 发现更好的证据时, 替换掉最弱的, 而不是无限追加
- 避免context dilution导致精度下降

#### 阶段三: 自适应门控 (P3-3)

引入 TARG 的免训练自适应检索门控:
- 用模型的 prefix logits 计算不确定性分数
- 简单查询 (低不确定性) 直接回答, 跳过检索
- 复杂查询 (高不确定性) 触发检索
- 预期减少 70-90% 的检索调用

### 架构变更

```
当前: LangGraph 固定节点链
  rewrite -> retrieve -> critique -> revise -> synthesize -> validate

目标: LangGraph Agent + Tool calling
  agent_reason -> [choose_tool] -> tool_execute -> agent_reason -> ... -> synthesize -> validate
```

关键变化:
- `rewrite` / `retrieve` / `critique` / `revise` 不再是固定节点
- 合并为 `agent_reason` 节点, 模型自主决定检索策略
- `synthesize` 和 `validate` 保持不变 (证据链和门控仍然需要)

## 不在本 RFC 范围内

- RL 训练 (MARAG-R1 方式), 成本太高, 暂用 prompt engineering
- 完全去掉 LangGraph 工作流, 仍保留工作流框架做编排
- 多模态检索

## 优先级

P3. 长期规划, 需要先完成 P0-P2.

前置条件:
- P0: Contextual Retrieval ([RFC-003](./RFC-003-contextual-retrieval.md)) 落地
- P1: 可观测性 ([RFC-002](./RFC-002-observability-full-chain-trace.md)) 落地
- P1: CRAG 纠错检索 (RFC-001 升级) 落地
- P2: GraphRAG 评估完成

## 预期收益

- 简单查询延迟降低 50%+ (跳过不必要的检索)
- 复杂多跳推理准确率提升 15-20%
- 检索调用减少 70-90% (TARG 门控)
- 系统更灵活, 能适应未见过的查询类型

## 预期风险

- Agent 自主性带来不可预测性, 需要更强的可观测性
- Tool calling 依赖模型能力, 弱模型效果可能不如固定 pipeline
- 从 pipeline 到 agent 的迁移是结构性变更, 回归测试成本高
- 可能出现 "检索不足" 导致的 hallucination

## 成功标志

- 简单查询平均延迟降低 30%+
- 多跳推理准确率提升 10%+
- 检索调用次数减少 50%+
- 评测指标不退化 (recall / faithfulness / answer_relevancy)

## 关联文档

- [RFC-001](./RFC-001-retrieval-hardening-roadmap.md) - 检索强化, 本 RFC 的前置条件
- [RFC-002](./RFC-002-observability-full-chain-trace.md) - 可观测性, Agent 范式的必要基础设施
- [RFC-003](./RFC-003-contextual-retrieval.md) - Contextual Retrieval, 索引层前置条件
- [RFC-005](./RFC-005-raptor-recursive-abstractive-tree.md) - RAPTOR, 可作为工具之一
- [A-RAG 论文](https://arxiv.org/abs/2602.03442)
- [MARAG-R1 论文](https://arxiv.org/abs/2510.27569)
- [TARG 论文](https://arxiv.org/abs/2511.09803)
- [SEAL-RAG 论文](https://arxiv.org/abs/2512.10787)

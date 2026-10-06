# RFC-004 Agentic RAG 检索工具化

## 状态

Closed (2026-08-25 项目收口): 阶段一检索工具化已实现且默认关闭; 完整范式迁移经评估后决定不做.

## 已实现 (阶段一: 工具化检索)

- 检索能力封装为 LLM 可调用的工具: semantic_search / keyword_search / structured_lookup / chunk_read, 见 [retrieval_tools.py](../../src/riskagent_agenticrag/agents/retrieval_tools.py)
- Agentic RAG 执行入口: 模型自主循环选择并调用工具, 见 [agentic_rag_runner.py](../../src/riskagent_agenticrag/agents/agentic_rag_runner.py)
- 配置开关 `settings.features.agentic_rag` (默认关闭), 开启后走 agentic 模式, 关闭走 LangGraph 预定义主链, 见 [app.py](../../src/riskagent_agenticrag/app.py)
- 单测覆盖: [test_retrieval_tools.py](../../tests/unit/test_retrieval_tools.py) / [test_agentic_rag_runner.py](../../tests/unit/test_agentic_rag_runner.py)

## 收口决策 (2026-08-25)

完整范式迁移 (把 rewrite/retrieve/critique/revise 合并为模型主控的 agent_reason 循环) 决定不做, 理由:

- 当前评测集 50 题以单跳定义/数值题为主, 预定义 pipeline + 岔路口决策已 50/50 通过 threshold gate, 模型自主策略的增量收益在现有评测上无法验证
- 原提案的阶段二 (SEAL-RAG 固定预算替换) 与阶段三 (TARG 自适应门控) 已以 pipeline 形态在 [RFC-001](./RFC-001-retrieval-hardening-roadmap.md) 落地并验收, 未采用 agent 形态 — 论文收益与 agentic 形态可解耦, 图编排即可获得大部分工程收益
- 生产默认路径保持 LangGraph 预定义主链; 已实现的工具化检索作为实验性分支保留, 默认关闭

## 背景 (历史提案依据)

原提案动机: 当前范式下所有查询走同一条链路, 简单查询过重, 复杂查询不够灵活; query rewrite 是规则驱动的, 检索策略是固定的 (dense + BM25 + rerank), 不能根据问题类型动态选择.

业界参考 (2025-2026):

- A-RAG (arXiv 2602.03442): 层次化检索接口 (keyword_search / semantic_search / chunk_read), 模型自主决定用哪个工具、何时用、用几次
- MARAG-R1 (arXiv 2510.27569): RL 训练 LLM 动态协调 4 种检索工具
- ReaLM-Retrieve (SIGIR 2026): 步级不确定性检测, 模型在推理每一步自己决定是否需要检索

## 关联文档

- [RFC-001](./RFC-001-retrieval-hardening-roadmap.md) - 检索强化总纲, 生产主链与 SEAL-RAG/TARG 的 pipeline 形态落地记录

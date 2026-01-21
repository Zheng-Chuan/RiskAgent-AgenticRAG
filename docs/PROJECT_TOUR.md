# 项目走读: RiskAgent-AgenticRAG

这份文档用于带你快速理解项目结构与关键设计决策
建议按“入口 -> 核心链路 -> 可解释性 -> 评测回归 -> 运维流水线”的顺序阅读

---

## 1. 从哪里开始读

建议从门面类开始 它把 UI/CLI/评测 的调用方式统一成同一套系统能力

- 系统门面: [app.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/app.py)
  - build_index: 索引流程入口
  - chat: 查询流程入口(支持 agentic_loop 与 langgraph 两种 runner)

然后看两条用户入口

- UI: [gradio_app.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/gradio_app.py)
- CLI: [demo_cli.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/demo_cli.py)

最后再看评测入口

- 离线评测 runner: [evaluation/run.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/run.py)

---

## 2. 索引(Index)流程是怎么跑的

目标: 把 corpus 目录里的 Markdown 变成可检索的 chunk 向量库

阅读顺序与关键点

- 语料加载: [source_loader.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/source_loader.py)
  - 递归读取 corpus/*.md
  - 把文件路径写入 Document.metadata.source
- 文本切分: [ingestion.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/ingestion.py)
  - 固定 chunk_size / chunk_overlap
  - 生成 chunk_id: (source + start_index + chunk_text) -> sha1 -> 前12位
  - 这样做是为了 citations 可追溯 且 rebuild 后仍可定位
- 向量库: [vectorstore.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/vectorstore.py)
  - 默认用 Milvus Lite 落盘到项目目录(或连接远端 Milvus)
  - build_milvus_vectorstore 的语义是 rebuild(drop_old=True)
- pipeline串联: [pipeline.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/pipeline.py)

---

## 3. 查询(Query)流程是怎么跑的

项目里有两条查询路径

### 3.1 Baseline RAG(最小闭环)

- Graph 定义: [workflow.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/graph/workflow.py)
  - retrieve_node: retriever.invoke(question) 得到 docs
  - answer_node: generate_answer(question, docs) 得到 answer
- LLM适配: [generate.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/llm/generate.py)
  - 有 key: 调用 OpenAI compatible 或 Ollama
  - 无 key: deterministic fallback 输出(用于验证链路与citations)

### 3.2 Agentic RAG(可自检/可工具化)

- 单Agent agentic loop: [agentic_loop.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/agentic_loop.py)
  - rewrite -> retrieve -> critique -> reretrieve -> tool decision -> tool call -> synthesize -> validate -> save artifacts
- LangGraph 编排版(可选): [langgraph_runner.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/orchestration/langgraph_runner.py)
  - 把相同的步骤拆成节点与state 便于可视化与扩展

---

## 4. 这个项目如何把“可解释性”做成工程能力

这里的可解释性不是“写得很像解释”
而是“答案可以被复盘 被验证 被量化”

### 4.1 citations: 让答案回到证据

- citations 不是模型写的 而是从 retriever 返回的 docs.metadata 抽取
- 抽取实现: [extract_citations](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/pipeline.py#L71-L87)

关键决策: citations 的可信来源必须是检索结果的元数据 而不是模型自述

### 4.2 结构化 contract: 让“解释”可被机器校验

- 结构化输入输出模型: [structured.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/contracts/structured.py)
- 关键字段
  - evidence_set: 证据集合(可定位 source/chunk_id/start_index/snippet)
  - claims: 可验证主张(每条绑定 evidence_ids)
  - tool_traces: 工具输入输出(用于数值一致性)
  - decision_log: 每一步决策理由
  - failure_reason: 失败类型与细节(用于治理与评测)

关键决策: output contract extra=forbid 避免无意扩展导致回归不可控

### 4.3 validator gates: 把解释约束变成确定性规则

- gates实现: [gates.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/validators/gates.py)
  - refusal_gate: 无证据就拒答并给下一步
  - evidence_gate: claim 必须绑定有效 evidence_id
  - numeric_consistency_gate: 出现数字必须能回指工具输出(目前是最小版本)

关键决策: gate尽量确定性 不用LLM当裁判 以降低成本与不稳定性

### 4.4 artifacts: 让每次运行可回放可归因

- artifact落盘: [storage.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/artifacts/storage.py)
  - 保存 request/response
  - bundle目录内额外输出 structured_response.json(可解析时)

关键决策: “先落盘再优化” 让调试与回归有抓手

---

## 5. 评测与回归体系是怎么搭起来的

### 5.1 离线评测 runner 与报告

- 评测入口: [evaluation/run.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/run.py)
- 报告写入/基线对比: [reporting.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/reporting.py)
- citations coverage(确定性): [citations.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/citations.py)

关键决策: 先上确定性指标(coverage)再引入LLM judge 保证离线可跑

### 5.2 RAGAS(可选)与LLM judge

- RAGAS集成: [ragas_integration.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/ragas_integration.py)

关键决策: 默认不开启 避免评测依赖外部服务 需要时再打开

### 5.3 Week6: citation precision 与幻觉检测

- citation precision judge: [citation_precision.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/citation_precision.py)
  - auto: 有LLM用LLM 否则用heuristic
  - heuristic: 用确定性规则离线打分 适合CI
- 单测(离线): [test_week6_citation_precision_quality.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/tests/test_week6_citation_precision_quality.py)

关键决策: Week6必须提供无key也可跑的评测路径 否则回归门禁落不了地

---

## 6. 运维与流水线(与业务代码隔离)

这些内容被刻意放在 .github / tools / deploy / docs
不侵入 src 下的业务链路 便于长期维护

- CI: [.github/workflows/ci.yml](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.github/workflows/ci.yml)
- nightly评测: [.github/workflows/nightly-eval.yml](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/.github/workflows/nightly-eval.yml)
- profiling: [PROFILING.md](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/docs/PROFILING.md)
- 部署compose: [DEPLOYMENT.md](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/docs/DEPLOYMENT.md)

---

## 7. 关键决策清单(为什么这么做)

1. 先可复现再谈质量: Week1的deterministic fallback确保链路可调试
2. citations来源必须可信: 只从检索docs元数据抽取 不让模型自造
3. chunk_id要稳定可追溯: 内容变了引用也该变
4. 解释要机器可检验: claim/evidence/tool_trace/failure_reason 结构化
5. 质量门禁先确定性后LLM: 让评测能离线跑且成本可控
6. 运维与评测尽量与业务隔离: 降低维护成本 避免影响主链路演进


# 项目走读: RiskAgent-AgenticRAG

这份文档用于快速理解项目结构与关键设计决策
建议按“入口 -> 索引与检索 -> 生成与可解释 -> 评测回归”的顺序阅读

---

## 1. 从哪里开始读

核心门面类统一 UI/CLI/评测 的调用方式

- 系统门面: [app.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/app.py)
  - build_index: 索引流程入口
  - chat: 查询入口(支持 agentic_loop 与 langgraph 两种 runner)

用户入口

- UI: [gradio_app.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/gradio_app.py)
- CLI: [demo_cli.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/demo_cli.py)

评测入口

- 离线评测 runner: [run.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/run.py)

---

## 2. 索引(Index)流程怎么跑

目标: 把 `corpus/` 里的资料变成可检索的 chunk 向量库

阅读顺序与关键点

- 语料加载: [source_loader.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/source_loader.py)
  - 递归读取 `corpus/**/*.md` 与 `corpus/**/*.pdf`
  - PDF 按页切成 Document, metadata 记录 page
- 分层切分 + chunk: [ingestion.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/ingestion.py)
  - Markdown 先按标题层级分段(生成 section_path), 再做长度切分
  - chunk metadata 包含 section_path/start_line/end_line/page 等定位信息
  - chunk_id 基于 (source + start_index + chunk_text) 生成, 便于回指
- 向量库: [vectorstore.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/vectorstore.py)
  - 默认 Milvus Lite(落盘在 `.milvus/`), 支持切换到远端 Milvus
- Pipeline 串联入口: [pipeline.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/pipeline.py)

---

## 3. 生成(Answer)与引用(Citations)

系统刻意把“答案生成”和“引用结构”分离

- 生成器: [generate.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/llm/generate.py)
  - 统一模板: TLDR/Concept/Why/Data flow/Example/Citations
  - 合规约束: 不泄露敏感信息 不提供投资建议 信息不足要拒答并给 next actions
- 引用提取: [extract_citations](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/pipeline.py#L71-L108)
  - citations 来自 retriever 返回 docs 的 metadata, 不允许模型自造引用

---

## 4. Agentic Loop 与工具调用

- 单 agent loop: [agentic_loop.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/agentic_loop.py)
  - query rewrite / retrieval critique / re-retrieve(max_rounds)
  - tool 决策与调用, 产出 tool_traces
- 工具侧 mock: [mock_risk_tool.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/tools/mock_risk_tool.py)

---

## 5. Validator 与 Failure taxonomy

输出可控的关键是“确定性 gate + 结构化 failure_reason”

- failure category 定义: [structured.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/contracts/structured.py)
- gate 实现: [gates.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/validators/gates.py)
  - evidence gate / evidence_not_supporting
  - numeric consistency gate(对齐 tool 输出)
  - refusal gate(信息不足必须拒答并给 next actions)

---

## 6. 评测与回归

- 评测 runner: [run.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/run.py)
  - citations coverage
  - citation precision judge
  - domain consistency(数值/术语)
- 报告与回归对比: [reporting.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/reporting.py)
- 数据集:
  - 最小集: [questions.json](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/tests/data/questions.json)
  - 扩展集: [eval_set.json](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/tests/data/eval_set.json)


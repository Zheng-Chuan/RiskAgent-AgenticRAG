# ARCHITECTURE

## 高层目标

- 面向企业内部软件工程师
- 用 RAG 基于语料回答
- answer 必须带 citations 方便回溯到原文
- 编排层用 LangGraph
- LLM provider 可插拔

## 开源大模型接入

原则 不绑定单一厂商 统一走 OpenAI compatible 接口

- 商业 API 配 `LLM_API_KEY` `LLM_BASE_URL` `LLM_MODEL`
- 开源模型 用 vLLM TGI Ollama 起一个 OpenAI compatible server 再配 `LLM_BASE_URL`

说明 没有 key 时会走 deterministic fallback 先把 RAG 链路和引用跑通
有 key 后再切换到真实 LLM

## 核心模块

- `riskagent_rag.rag`
  - ingest, chunk, index
  - retrieve
- `riskagent_rag.llm`
  - LLM 接入封装
  - OpenAI compatible client
  - fallback client
- `riskagent_rag.agents`
  - retrieval agent
  - explanation agent
  - coordinator

## 数据流

sources -> chunk -> embeddings -> milvus
query -> retrieve -> contexts -> multi-agent -> answer + citations

## LangGraph Agentic Loop 可视化

这是 RiskAgent 项目中 agentic RAG loop 的执行流程图.

### 流程图

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
  __start__([<p>__start__</p>]):::first
  rewrite(rewrite)
  retrieve_and_critique(retrieve_and_critique)
  revise_query(revise_query)
  decide_tool_use(decide_tool_use)
  call_tool(call_tool)
  synthesize_answer(synthesize_answer)
  validate_and_save(validate_and_save)
  __end__([<p>__end__</p>]):::last
  __start__ --> rewrite;
  call_tool --> synthesize_answer;
  decide_tool_use -.-> call_tool;
  decide_tool_use -.-> synthesize_answer;
  retrieve_and_critique -.-> decide_tool_use;
  retrieve_and_critique -.-> revise_query;
  revise_query --> retrieve_and_critique;
  rewrite --> retrieve_and_critique;
  synthesize_answer --> validate_and_save;
  validate_and_save --> __end__;
  classDef default fill:#f2f0ff,line-height:1.2
  classDef first fill-opacity:0
  classDef last fill:#bfb6fc
```

### 节点说明

- **查询改写 (rewrite)**: 将用户问题改写为更适合检索的 query
- **检索与评估 (retrieve_and_critique)**: 检索文档并评估质量
- **修订查询 (revise_query)**: 基于 critique 改进 query
- **决策工具调用 (decide_tool_use)**: LLM 决定是否需要调用工具
- **调用工具 (call_tool)**: 调用 DataAgent 获取结构化数据
- **合成答案 (synthesize_answer)**: 基于检索结果和工具输出生成最终答案
- **验证与落盘 (validate_and_save)**: 运行 validator gates 并保存 artifacts

### 查看方式

1. 在 GitHub 上直接查看 (GitHub 原生支持 Mermaid)
2. 使用 Mermaid 在线编辑器: https://mermaid.live/
3. 在支持 Mermaid 的 Markdown 编辑器中查看 (如 Typora, VS Code with Mermaid extension)
4. 在 Gradio UI 的 Inspector → Graph Tab 中查看

## 质量保障与开发方法论 (Quality Assurance & Methodology)

### Evaluation Driven Development (EDD)

本项目采用 **EDD (评测驱动开发)** 模式，即在开发功能之前，先定义评测样本与通过标准。

- **原则**: 先定义 "Bad Case" (坏样本)，再优化系统直到 Pass。
- **流程**:
  1.  发现问题或定义新需求。
  2.  在评测集 (`tests/data/eval_set.json` 或专用负样本集) 中添加对应的测试用例。
  3.  运行评测脚本，确认失败 (Red Phase)。
  4.  修改 Agent 逻辑或 Prompt。
  5.  再次运行评测，确认通过且无回归 (Green Phase)。

### 拒答机制 (Refusal Mechanism)

为了保证金融场景的可信度，系统必须具备**拒答能力**。

- **架构要求**:
  - **负样本集 (Negative Dataset)**: 评测集中必须包含 20%+ 的负样本（如库外知识、恶意提问、无意义输入）。
  - **Refusal Gate**: 在 Agentic Loop 中必须包含显式的拒答门控（Refusal Gate）。
    - 当检索结果 (`docs`) 为空或相关性 (`context_relevance`) 低于阈值时，必须拒答。
    - 当生成的 `claims` 无法被 `evidence` 强支撑时，必须拒答或标记为不确定。
  - **验收标准**:
    - 正样本拒答率 (False Refusal Rate) < 5%
    - 负样本拒答率 (True Refusal Rate) > 95%

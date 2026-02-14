# RiskAgent-AgenticRAG 可解释性与评估体系演进时间线

这份文档记录从 Week 1 到 Week 7 我们如何把一个“能回答”的 RAG demo
逐步推进成一个“可解释 可观测 可评估 可回归”的工程系统

注意
当前代码已经收敛为形态A 以真实用户路径为唯一主路径
编排只保留 LangGraph
不再保留 deterministic fallback
不再保留 agentic_loop 代码路径
当前实现请以 ROADMAP 与 ARCHITECTURE 为准

核心关注三件事

1. 可解释性: 输出为什么是这个答案 证据在哪里
2. 可观测性: 发生了什么 每一步怎么决策 有哪些中间产物
3. 可评估性: 质量怎么量化 怎么对比 baseline 怎么防止退化

---

## Week 1: 先把闭环跑通 让系统可复现

**目标**

- 端到端闭环: ingest -> retrieve -> answer
- 任何人拉下代码都能跑起来 能看到“答案 + 引用”

**做了什么**

- 固化最小可运行入口(UI/CLI)与回归测试入口
- 先把检索链路与引用链路跑通并固化输出结构

**可解释性推进点**

- 把“引用(citations)”作为输出 contract 的一部分: 不允许只给答案不告诉来源

**可观测性推进点**

- 最早期的可观测手段是“可复现”: 同一套语料与同一条命令能稳定得到同样结构的输出

**评估体系推进点**

- 建立 smoke test 作为最低门槛: 不是为了分数而是为了防止链路回归

**关键入口**

- 门面: [app.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/app.py)
- UI: [gradio_app.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/gradio_app.py)
- CLI: [demo_cli.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/demo_cli.py)
- 生成策略: [generate.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/llm/generate.py)

---

## Week 2: 把“引用”变成可量化指标 让证据链开始稳定

**目标**

- 让 citations 不只是展示 而是能统计 能回归
- 让 chunk 元数据稳定可追溯 便于定位与复查

**做了什么**

- 语料加载与切分规则固定 并为每个 chunk 生成 chunk_id
- 定义最小 citations schema: source + chunk_id
- 引入 citations coverage 作为确定性指标与门槛

**可解释性推进点**

- citations 从“可有可无”升级为“每条回答的硬输出”
- chunk_id 让引用从“文件级”推进到“片段级”

**可观测性推进点**

- metadata 里写入 source 与 chunk_id 形成可追溯链路

**评估体系推进点**

- 指标从“我感觉”变成“coverage = passed / total”
- 引入 baseline 评测用例 让引用质量能做回归对比

**关键实现**

- 语料加载: [source_loader.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/source_loader.py)
- 切分与 chunk_id: [ingestion.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/ingestion.py)
- citations 抽取: [pipeline.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/pipeline.py)
- citations coverage 指标: [citations.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/citations.py)

---

## Week 3: 引入 agentic loop 把“推理过程”显式化

**目标**

- 系统不只是“检索+生成” 而是能做自检 重试 工具调用
- 输出不只是文字 而是可被验证的结构化中间产物

**做了什么**

- 单 agent 的 agentic loop: rewrite -> retrieve -> critique -> reretrieve -> synthesize
- 引入 tool use: 数值事实用工具产出 不是靠模型编
- 引入 validator gates: 确定性规则 fail fast

**可解释性推进点**

- “答案为何成立”开始从“引用列表”升级为“claim -> evidence_set”的映射关系
- “数字为何可信”开始要求能回指 tool_traces

**可观测性推进点**

- decision_log: 每一步为什么这么做 选了什么 alternatives 是什么
- tool_traces: 工具输入输出与耗时轨迹可回放

**评估体系推进点**

- 校验从“离线指标”推进到“在线 gate”: 不满足规则就标记 failed 并返回 failure_reason

**关键实现**

- LangGraph 编排主流程: [langgraph_runner.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/orchestration/langgraph_runner.py)
- 结构化 contract: [structured.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/contracts/structured.py)
- validator gates: [gates.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/validators/gates.py)

---

## Week 4: 建立统一评测Runner 把“观测”固化成报告

**目标**

- 让评测变成一条命令 输出统一格式的 JSON 报告
- 支持 baseline 对比与退化检测
- 可选启用 LLM judge(RAGAS) 做更贴近人的质量度量

**做了什么**

- 评测 runner: 读取数据集 -> build index -> 执行查询 -> 汇总 metrics -> 写入报告
- 报告落盘到 .artifacts/reports 并支持取最新报告作为 baseline
- RAGAS 可选集成: faithfulness answer_relevancy context_precision context_recall

**可解释性推进点**

- 每条样本记录 question answer contexts citations
- 报告作为“证据包”: 可复盘每条失败样本发生了什么

**可观测性推进点**

- 报告结构固定: inputs/metrics/samples/baseline diff

**评估体系推进点**

- 质量门禁开始自动化: compare_reports 标记 regression

**关键实现**

- 评测入口: [evaluation/run.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/run.py)
- 报告落盘与对比: [reporting.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/reporting.py)
- RAGAS 集成: [ragas_integration.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/ragas_integration.py)
- 使用说明: [EVALUATION.md](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/docs/EVALUATION.md)

---

## Week 5: 引入拒答机制与负样本评测 把“不知道”标准化

**目标**

- 该拒答时必须拒答 并且拒答要可解释(为什么拒答 下一步是什么)
- 用负样本集验证拒答质量 避免“瞎编但有引用”的危险输出

**做了什么**

- refusal gate: docs/evidence不足时输出标准拒答并带 next actions
- 构建负样本用例并形成可运行测试

**可解释性推进点**

- 明确系统边界: 证据不足时拒答而非硬答

**可观测性推进点**

- failure_reason.category 让失败类型可统计 可治理

**评估体系推进点**

- refusal_rate 让“拒答质量”可量化并能回归

**关键实现**

- refusal 评测: [refusal.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/refusal.py)
- gates 中的 refusal gate: [gates.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/validators/gates.py)

---

## Week 6: 引用精准度(Citation Precision) 把“有引用”升级为“引用真的支持答案”

**目标**

- 解决 Week 2 coverage 的盲区: “有引用但引用不支持答案”
- 让“幻觉”在有 citations 的情况下也能被量化识别

**做了什么**

- 引入 citation precision judge(LLM 作为裁判)
- 指标进入报告并参与 baseline 对比(可选开启)

**可解释性推进点**

- 把答案拆成更细粒度的可验证单元(按句子)
- 把“支持/不支持”的判定输出为明细 便于定位具体问题句子

**可观测性推进点**

- 报告里增加 citation_judge.details: 每条样本的判定与错误信息

**评估体系推进点**

- 从“引用覆盖率”推进到“引用准确率” 使质量门禁更严格

**关键实现**

- citation precision judge: [citation_precision.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/citation_precision.py)
- judge LLM 选择: [judge_llm.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/judge_llm.py)
- runner 开关与报告写入: [evaluation/run.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/run.py)

---

## Week 7: 领域一致性(数值+术语) 让“解释”对齐金融事实

**目标**

- 让回答中的关键数字可追溯并与工具输出一致
- 让术语解释与语料定义一致 避免“概念解释错位”

**当前状态**

- numeric_consistency_gate 已有最小实现: 先检查“出现数字但没有 tool_traces”这一类硬错误
- 术语一致性暂未落地

**后续演进建议**

- 数字抽取: 从 report/claims 提取关键数字与单位
- 对齐策略: 将数字映射到 tool_output 的字段并允许误差带
- 术语检查: 与 Background.md(术语表)做一致性比对

**关键实现**

- numeric consistency gate: [gates.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/validators/gates.py)

---

## 一句话总结这条“可解释”路线

- Week 1 让系统可复现
- Week 2 让引用可追溯并可量化
- Week 3 让决策过程与证据结构化
- Week 4 让评测与回归自动化
- Week 5 让拒答可解释并可评测
- Week 6 让引用质量从“有”变成“对”
- Week 7 让数值与术语对齐领域事实

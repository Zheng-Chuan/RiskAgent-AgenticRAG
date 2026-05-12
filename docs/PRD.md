# Product Requirements Document

## 文档目标

本 PRD 用来定义 `RiskAgent-AgenticRAG` 的下一阶段建设方向.

本阶段目标不是把项目做成通用 Agent 平台.
本阶段目标是把项目收敛成一个顶尖的 RAG 项目.

明确约束如下:

- 不做 tool use 主路径
- 不做任务完成度评估
- 不做多智能体协作
- 不扩展为通用工作流编排平台
- 只聚焦高可信检索 高可信生成 高可信评测

---

## 一句话定位

面向金融风控与衍生品知识问答的高可信 RAG 系统.
核心卖点是 `检索可信` `答案有证据` `评测可复现` `回归可审计`.

---

## 当前项目现状

### 已有能力

- 已有完整的 LangGraph RAG 主流程, 包含 query rewrite retrieval critique revise synthesize validate artifact save
- 已有混合检索能力, 包含 Dense 检索 BM25 RRF Cross Encoder rerank
- 已有高级索引能力, 包含 Parent Child Summary HyDE
- 已有 Self RAG 风格的检索充足性判断与提前停止
- 已有 answer citations claims evidence_set decision_log trace artifact
- 已有离线评测入口, 支持 baseline diff threshold gate 与多种指标输出
- 已有 API CLI tests docs 等基本工程骨架

### 当前主要问题

#### 1. 项目边界还不够收敛

- 当前代码里仍然保留 tool decision 与 tool trace 相关路径
- 这会稀释项目作为顶尖 RAG 的核心叙事
- 后续应把主路径彻底收敛为 `rewrite -> retrieve -> rerank -> synthesize -> validate -> report`

#### 2. 检索评测不够独立

- 当前 retrieval metrics 使用 answer 里的 citations 反推 relevant docs
- 这会产生自举偏差
- 系统说自己引用了哪些 chunk, 不能等价于这些 chunk 就是 gold relevant chunk

#### 3. 数据集标注强度不够

- 当前评测集规模较小
- 不少题目缺少完整的 ground truth contexts
- 缺少 query 到 chunk 的显式 qrels 标注
- 缺少按题型划分的 slice 结果

#### 4. 门禁判定还不够硬

- 当前 gate benefit 与 false kill 更偏代理指标
- validate 之后还有 LLM appeal 覆盖失败结果
- 这会削弱门禁的确定性与审计性

#### 5. 结果证据链不够完整

- 当前仓库内缺少固定提交的评测报告样例
- 简历和文档中的部分提升数字无法直接在仓库内复核
- 报告产物与版本信息还没有形成强绑定

#### 6. 工程稳定性还不够顶尖

- 依赖兼容性仍可能影响测试稳定性
- 缺少环境锁定与复现实验基线
- 缺少面向 RAG 的专项回归集与固定验收入口

---

## 目标状态

项目升级后的目标状态如下:

- 对外定位清晰. 这是一个顶尖 RAG 项目, 不是 Agent 平台
- 主链路清晰. 不依赖 tool use, 不依赖任务执行
- 检索评测独立. retrieval 有人工或半人工 gold qrels
- 生成评测可信. answer grounding 与 citation support 可单独复核
- 门禁稳定可审计. 失败结果不能被隐藏覆盖
- 报告可复现. 任意一次结论都能追溯到数据集 代码版本 配置 产物
- 回归可比较. 任意改动都能看到总体指标和 slice 指标变化

---

## 非目标

本阶段明确不做以下事项:

- 不做 tool use 主路径设计
- 不做任务完成率 task success 评估
- 不做 planner executor reviewer 等多智能体拆分
- 不做数据库操作型 agent
- 不做长流程业务编排

---

## 改进方案

### 方案 A. 收敛为纯 RAG 主链路

目标是让项目叙事和代码主路径完全聚焦 RAG.

核心动作:

- 移除或降级 tool decision call_tool tool trace 在主链路中的地位
- 重写架构文档, 明确系统是高可信 RAG, 不是通用 Agent
- 将主流程统一表述为 `query understanding -> retrieval -> rerank -> synthesis -> validation -> evaluation`
- 保留 artifact trace report, 但删除与 tool use 绑定的核心卖点

预期收益:

- 项目定位更聚焦
- 面试叙事更一致
- 代码复杂度更低
- 评测对象更纯粹

### 方案 B. 建立独立的检索 gold 标注体系

目标是让 retrieval metrics 脱离 answer 自举.

核心动作:

- 为评测题补齐 `gold chunk ids` 或 `qrels`
- 支持一题多 relevant chunks
- 区分 strong relevant 与 weak relevant
- retrieval recall mrr ndcg 全部基于 gold qrels 计算
- 报告中显式区分 `gold retrieval metrics` 与 `answer derived diagnostics`

预期收益:

- 检索评测独立可信
- 检索改动的收益能被真实衡量
- 可以更稳地支撑简历和对外表述

### 方案 C. 建立高可信回答评测体系

目标是把答案质量评测从单一分数变成可解释的组合体系.

核心动作:

- 保留 faithfulness answer relevancy citation coverage
- 增加 sentence level support 标注或 judge 结果缓存
- 将 citation precision 与 unsupported sentences 落到样本报告
- 将 numeric consistency 与 glossary consistency 继续保留为金融专项指标
- 建立按题型的 slice 评测, 如 definition compare procedure regulation numeric

预期收益:

- 回答质量问题能定位到具体样本和具体句子
- 不同类型问题的优势和缺陷更清楚
- 金融领域专项能力有更强说服力

### 方案 D. 重做门禁逻辑为确定性发布门禁

目标是让 gate 真正成为发布门禁, 而不是软性建议.

核心动作:

- 移除正式评测中的 LLM appeal 覆盖逻辑
- 将 threshold failure 与 baseline regression 分开报告
- 将 gate block benefit gate false kill 改为基于 gold label 或人工复核样本计算
- 所有 gate failure 必须带 failure category 与对应证据

预期收益:

- 门禁结论更可审计
- 失败原因更稳定
- 评测报告更适合作为发布依据

### 方案 E. 固化报告与版本证据链

目标是让所有结果都可以被仓库复核.

核心动作:

- 固化标准评测命令与标准输出目录
- 报告中写入 dataset version retriever mode reranker model prompt version git commit
- 提交一组基准报告样例到仓库
- 文档中所有数字结论都要求引用具体报告文件

预期收益:

- 任意数字都能回溯
- 简历与文档更可信
- 后续优化可以沿用统一口径

### 方案 F. 提升工程稳定性与可复现性

目标是让项目从能跑提升到稳定可复现.

核心动作:

- 锁定关键依赖版本
- 修复 Milvus 与 protobuf 等依赖兼容问题
- 增加纯离线评测路径
- 增加最小 RAG 回归集与 CI 级 smoke tests
- 增加一键复现实验命令

预期收益:

- 新环境更容易复现
- 评测更稳定
- 项目更接近顶尖工程标准

---

## 版本范围

本阶段版本范围建议定义为 `RAG Excellence`.

版本内必须完成:

- 纯 RAG 主路径收敛
- gold qrels 数据集
- 独立 retrieval eval
- 高可信 answer eval
- 确定性 gate
- 可复现报告体系
- 稳定的回归入口

版本内不做:

- tool use
- task completion eval
- 多智能体

---

## 任务 checklist

### 1. 主路径收敛为纯 RAG

- [ ] 从主流程移除 `decide_tool_use` 与 `call_tool` 作为默认路径
  - 验收标准: 默认执行链路不再经过 tool 节点
  - 验收证据: 架构图更新. `langgraph_runner.py` 主流程代码. 对应单测或快照测试

- [ ] 删除或降级对 tool traces 的核心输出依赖
  - 验收标准: API 和 artifact 的核心 schema 不再把 tool 字段作为主能力宣传点
  - 验收证据: `docs/API.md` `docs/ARCHITECTURE.md` `docs/DATA.md` 中的字段说明更新. schema 测试通过

- [ ] 更新 README 与架构文档的项目定位
  - 验收标准: 所有主文档统一描述项目为高可信 RAG 系统
  - 验收证据: `README.md` `docs/ARCHITECTURE.md` `docs/PRD.md` 中不存在以 tool use 为主卖点的描述

### 2. 建立 gold qrels 标注集

- [ ] 为现有 50 题评测集补齐 qrels
  - 验收标准: 每题至少有 1 个 gold chunk id. 支持多 relevant chunk
  - 验收证据: 新增 `tests/data/qrels.json` 或等价数据文件. 数据校验脚本通过

- [ ] 为 qrels 增加标注约定文档
  - 验收标准: 明确 relevant 定义 chunk 粒度 边界样例 标注流程
  - 验收证据: 新增 `docs/EVAL_DATASET.md` 或等价章节. 示例样本可复核

- [ ] 为数据集增加题型 slice 标签
  - 验收标准: 每题至少包含 1 个 slice 标签, 如 definition compare numeric regulation
  - 验收证据: 数据文件新增 `tags` 字段. 数据加载测试通过

### 3. 重做 retrieval eval 为独立评测

- [ ] 用 qrels 重写 retrieval metrics 计算逻辑
  - 验收标准: retrieval_recall_at_k retrieval_mrr retrieval_ndcg_at_k 全部基于 qrels 计算
  - 验收证据: `advanced_metrics.py` 或新模块代码. 单测覆盖正例 反例 多 relevant case

- [ ] 在报告中分离 retrieval metrics 与 citation diagnostics
  - 验收标准: 报告明确区分 gold retrieval 指标和生成侧诊断指标
  - 验收证据: 新评测报告 JSON 和 Markdown 样例. `docs/EVALUATION.md` 更新

- [ ] 增加 retrieval slice report
  - 验收标准: 报告支持按题型输出 recall mrr ndcg
  - 验收证据: 样例报告中出现 slice 结果. 相关单测通过

### 4. 重做 answer eval 为高可信回答评测

- [ ] 保留并规范 citation coverage faithfulness answer relevancy
  - 验收标准: 三项核心指标定义 计算方式 阈值都有文档说明
  - 验收证据: `docs/EVALUATION.md` 指标定义章节更新. 阈值配置文件更新

- [ ] 增加 sentence level support 结果输出
  - 验收标准: 每个样本报告可看到 supported sentences 与 unsupported sentences
  - 验收证据: 报告样例. `citation_precision.py` 或新模块测试通过

- [ ] 保留金融专项指标并加入样本明细
  - 验收标准: numeric consistency glossary consistency 除聚合分数外, 还可下钻到样本级失败明细
  - 验收证据: 报告样例中包含专项失败详情. 对应单测通过

### 5. 重做 gate 为确定性发布门禁

- [ ] 关闭正式评测中的 LLM appeal 覆盖逻辑
  - 验收标准: 正式评测模式下, gate failure 不会被 appeal 自动清空
  - 验收证据: 配置项与代码路径更新. 单测覆盖 fail case 与 no appeal case

- [ ] 分离 threshold failure 与 baseline regression
  - 验收标准: 报告中两个概念独立展示, 不共用一个 regression 字段
  - 验收证据: `reporting.py` `thresholds.py` 更新. 样例报告与单测通过

- [ ] 将 gate benefit false kill 改为基于标注样本计算
  - 验收标准: benefit 与 false kill 使用人工标签或复核标签, 不再仅依赖 answer 空值和 citation 数
  - 验收证据: 标注样本文件. 指标代码. 单测覆盖 true positive false positive false negative

### 6. 固化可复现报告体系

- [ ] 提交至少 1 组基准评测报告到仓库
  - 验收标准: 仓库内可直接查看基准 JSON 与 Markdown 报告
  - 验收证据: `.artifacts/reports` 或 `docs/reports` 下存在基准报告样例

- [ ] 将版本元信息写入每份报告
  - 验收标准: 报告包含 dataset version prompt version retriever mode reranker model git commit
  - 验收证据: 报告样例字段. 对应测试通过

- [ ] 建立文档数字结论引用规范
  - 验收标准: README docs RESUME 中的关键数字均能映射到具体报告文件
  - 验收证据: 文档内新增报告引用清单. 搜索后找不到无来源数字

### 7. 提升工程稳定性与复现能力

- [ ] 锁定关键依赖并修复评测环境兼容问题
  - 验收标准: 新环境执行核心评测与核心测试不因 Milvus protobuf 版本冲突失败
  - 验收证据: 依赖文件更新. 环境说明更新. 相关测试通过

- [ ] 增加纯离线回归入口
  - 验收标准: 在无在线 judge 条件下仍可跑完最小回归集
  - 验收证据: 新命令文档. 回归脚本. 离线路径测试通过

- [ ] 建立最小发布验收命令
  - 验收标准: 1 条命令完成 index eval report gate 的标准验收流程
  - 验收证据: `Makefile` 或脚本命令. 文档示例. 本地执行日志

---

## 发布验收口径

只有同时满足以下条件, 才能认为本阶段完成:

- 默认主路径已经收敛为纯 RAG
- retrieval eval 已基于 qrels 独立计算
- answer eval 已支持句级证据分析
- threshold failure 与 baseline regression 已分离
- 仓库内已有可复核的基准报告
- 核心测试与最小验收命令稳定通过

---

## 里程碑建议

### Milestone 1. 纯 RAG 收敛

完成主路径裁剪 文档收敛 schema 收敛.

### Milestone 2. 评测独立化

完成 qrels 数据集 retrieval eval 重构 slice report.

### Milestone 3. 门禁与报告可信化

完成 deterministic gate 基准报告 数字引用规范.

### Milestone 4. 工程稳定化

完成依赖锁定 离线回归 一键验收.

---

## 最终交付物

本阶段完成后, 仓库应至少包含以下交付物:

- 纯 RAG 架构代码与文档
- qrels 标注数据集
- 独立 retrieval eval 模块
- 高可信 answer eval 模块
- 确定性 gate 模块
- 基准报告样例
- 一键验收命令
- 与报告绑定的 README 与简历表述

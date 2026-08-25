# RFC-001 Retrieval Hardening Roadmap

## 状态

Accepted (2026-08-21 回写, 2026-08-24 更正: P0/P1 大部分落地并验收, P2 中 SEAL-RAG 已实现且默认生效, RAPTOR 与 P3 未启动, 见下方落地情况)

## 落地情况 (2026-08-21 核实, 2026-08-24 增补 CRAG 验收与 SEAL-RAG 纠正)

| 提案项 | 状态 | 说明 |
|---|---|---|
| Contextual Retrieval (P0) | 实现但默认关闭 | Qwen3-Embedding-4B 下 briefs 稀释术语信号, 定论见 [RFC-003](./RFC-003-contextual-retrieval.md) |
| qrels 升级 (P0) | 已落地 | recall 口径修正为主 gold (relevance>=2), qrels 带 chunk_id 单位 |
| 索引一致性 (P0) | 已落地 | schema fingerprint 拆分 (索引期/查询期分离), 查询开关不再触发全量重建; 评测默认只读, 重建需显式 `--reindex` |
| TARG 自适应门控 (P1) | 已落地 | query_router 实现, 金融术语词表 (词边界正则) 修复 12 题误判 (XVA/DVA/FVA/MVA/ColVA 家族) |
| CRAG 纠错检索 (P1) | 已实现并调优 | 三组数据闭环 (2026-08-25): ON (v10d) / OFF (v10e) / 混合 (v10f); 混合策略 (sufficient 门槛 0.2 -> 0.7, A/B 校准) 已上线生产: faithfulness 0.982 历史新高, recall 0.80 保住, gate 阈值/基线全过; 详见 [EVALUATION_LOG](../evaluations/EVALUATION_LOG.md) v10f |
| retrieval observability (P1) | 已落地 | trace/retrieval_diag/latency 分位数, 见 [RFC-002](./RFC-002-observability-full-chain-trace.md) |
| reranker (P1) | 已落地 | 远程 bge-reranker-v2-m3 启用 (auto fallback), trace 记实际生效模型 |
| SEAL-RAG 替换式检索 (P2) | 已实现并修复 | evidence_budget 实现 capacity=5 预算制替换 (rag/evidence_budget.py); 2026-08-24 trace 实证 145 检索节点全部执行筛选; 2026-08-25 修复跨轮重复 chunk 占位挤掉 gold 的 bug (v10e recall 回归根因, 见 v10f 台账), dedup 后 50 题 0 重复 |
| RAPTOR (P2) | 未启动 | 见 [RFC-005](./RFC-005-raptor-recursive-abstractive-tree.md) |
| Agentic RAG 迁移 (P3) | 未启动 | 见 [RFC-004](./RFC-004-agentic-rag-paradigm.md) |

### 核心成果对照预期

- recall_at_5: 0.500 -> 0.82 (v10d 全量评测, v10b 为 0.78), **超过预期收益区间 0.65-0.75 的上限**; 修复路径与 RFC 预设不同 (TARG 路由修复 + reranker + 口径修正, 而非 Contextual Retrieval)
- threshold gate 全绿且全量 50/50 首次达成 (v10d: faithfulness 0.903 / citation 1.000 / recall@5 0.82, 见 [EVALUATION_LOG](../evaluations/EVALUATION_LOG.md))
- 成功标志中 "简单查询调用减少 50%" 与 "多跳 context 不膨胀" 未做专门统计验证, 属遗留观察项

## 目标

把项目的下一阶段投入集中到 retrieval 和 recall 强化上.  
不扩张为巨无霸 Agent 平台.  
同时引入业界最新范式: CRAG 纠错检索 / TARG 自适应门控 / SEAL-RAG 替换式检索.

## 背景

当前项目已经有比较完整的统一 RAG 主链.  
真正限制上限的瓶颈不再是有没有更多 agent 节点.  
而是下面这些更硬的问题.

- qrels 评测单位还不够硬
- Self-RAG 充分性判断还偏轻
- index manifest 和 retriever cache 版本治理不足
- query intelligence 和 advanced index 还不够自适应
- retrieval recall_at_5=0.500 不达标, 需要从索引层和检索策略层同时强化

### 2026-08 业界前沿对齐

2025-2026 年学术界提出了多个可直接提升检索质量的新范式:

| 范式 | 来源 | 核心思想 | 对本项目的价值 |
|------|------|----------|----------------|
| CRAG | arXiv 2401.15884 | 检索后评估质量, 差则纠错重检索 | 升级 critique 为三档评估 |
| TARG | TMLR 2026 | 免训练自适应检索门控, 70-90% 更少检索 | 简单查询跳过检索 |
| SEAL-RAG | arXiv 2512.10787 | 替换而非扩展, 避免 context 膨胀 | 改进 revise loop |
| Contextual Retrieval | Anthropic 2024 | 索引时注入上下文摘要 | 直接提升 recall (见 RFC-003) |

## 提案范围

- 把 qrels 从宽松 text 匹配升级到更硬的 evidence unit
- 把 Self-RAG 充分性判断升级为 CRAG 式三档纠错检索
- 把 index manifest 和 retriever cache 升级成版本化一致性机制
- 把 query intelligence 从固定全套 fanout 升级为 TARG 式自适应门控
- 把 advanced index 从静态补分继续升级为 query aware expand
- 把 revise loop 从追加式升级为 SEAL-RAG 式替换式
- 为 retrieval 主链补 token latency rerank pair 等运行观测 (见 RFC-002)
- 引入 Contextual Retrieval 从索引层提升召回 (见 RFC-003)

## 优先级

### P0 必须先做

- `Contextual Retrieval`
  - 在索引阶段为每个 chunk 注入文档级上下文摘要
  - Anthropic 数据: 检索失败率降低 49-67%
  - 详见 [RFC-003](./RFC-003-contextual-retrieval.md)
- `qrels 升级`
  - 从 text 级命中继续升级到 chunk_id 或更硬的 evidence unit
  - 目标是让 retrieval recall 真正反映召回质量
- `索引一致性`
  - 把 embedding model chunking policy advanced index config 纳入版本键
  - 目标是避免旧索引污染新实验

### P1 随后做

- `CRAG 纠错检索`
  - 把 Self-RAG 从轻量规则升级为 claim aware sufficiency scorer
  - 引入 CRAG 三档评估: sufficient / insufficient / irrelevant
  - insufficient 时自动触发 query rewrite + re-retrieve
  - irrelevant 时触发降级策略 (放宽过滤 / 扩大 top_k)
  - 来源: [CRAG 论文](https://arxiv.org/abs/2401.15884)
  - 目标: 让 stop continue 对 compare numeric multi-hop 问题更稳
- `query intelligence 自适应`
  - 不再默认每题跑全套 variants
  - 引入 TARG 式不确定性检测, 简单查询跳过重写和 fanout
  - 来源: [TARG 论文 (TMLR 2026)](https://arxiv.org/abs/2511.09803)
  - 目标: 减少 50%+ 的不必要 fanout 调用
- `advanced index query aware expand`
  - 对不同题型调不同 expand 强度
- `retrieval observability`
  - 记录 fanout 数量 rerank pairs latency token 预算
  - 详见 [RFC-002](./RFC-002-observability-full-chain-trace.md)

### P2 中期做

- `SEAL-RAG 替换式检索`
  - 把 revise loop 从无限追加升级为固定 budget 替换
  - 发现更好证据时替换最弱的, 而非继续追加
  - 来源: [SEAL-RAG 论文](https://arxiv.org/abs/2512.10787)
  - 目标: 避免 context dilution 导致精度下降
- `RAPTOR 递归摘要树`
  - 构建多层索引树, 支持宏观问题
  - 详见 [RFC-005](./RFC-005-raptor-recursive-abstractive-tree.md)

### P3 长期规划 (见 RFC-004)

- `Agentic RAG 范式迁移`
  - 从预定义 pipeline 迁移到模型自主检索
  - 详见 [RFC-004](./RFC-004-agentic-rag-paradigm.md)

### 暂时不要做

- 通用多智能体平台化
- 大规模工具生态扩展
- 前端和产品形态扩张
- 和检索召回关系不强的功能堆砌

## 不在本 RFC 范围内

- 通用多智能体平台化
- 大规模工具生态扩展
- 前端和产品形态扩张
- 知识图谱 (独立评估)
- 领域 embedding 微调 (独立评估)

## 建议实施顺序

1. Contextual Retrieval (RFC-003) + qrels 升级 + index 版本治理
2. CRAG 纠错检索 (sufficiency scorer 三档评估) + reranker 评估
3. TARG 自适应门控 + query intelligence 自适应 + advanced index 深化
4. SEAL-RAG 替换式检索 (改进 revise loop)
5. RAPTOR 递归摘要树 (RFC-005)
6. Agentic RAG 范式迁移 (RFC-004)
7. retrieval observability 和成本治理 (RFC-002, 跨阶段并行)

## 预期收益

- retrieval eval 更可信
- 检索回归更稳定
- 文档问答中的召回和证据链更硬
- recall_at_5 从 0.500 提升到 0.65-0.75 (Contextual Retrieval + CRAG)
- 简单查询延迟降低 50%+ (TARG 门控)
- 多跳推理避免 context 膨胀 (SEAL-RAG)

## 预期风险

- qrels 升级会暴露当前真实召回短板
- CRAG sufficiency scorer 收紧后, 可能先带来更多 revise loop
- index versioning 加强后, 会增加全量重建频率
- TARG 门控可能误判, 导致简单查询漏检
- SEAL-RAG 替换策略可能丢失长尾证据

## 成功标志

- retrieval_recall_at_5 >= 0.6 (threshold gate 通过)
- retrieval 指标能稳定区分真正有效和无效的改动
- 新旧索引结果不会因为缓存污染而混在一起
- compare numeric regulation 这些高难题型的召回和证据质量有稳定提升
- 简单查询平均检索调用次数减少 50%+
- 多跳推理 context 长度不再随 loop 迭代无限增长
- README PRD ARCHITECTURE INTERVIEW 对项目卖点的描述继续收敛到 retrieval first

## 关联文档

- [RFC-002](./RFC-002-observability-full-chain-trace.md) - 可观测性 (跨阶段基础设施)
- [RFC-003](./RFC-003-contextual-retrieval.md) - Contextual Retrieval (P0 子项)
- [RFC-004](./RFC-004-agentic-rag-paradigm.md) - Agentic RAG 范式迁移 (P3)
- [RFC-005](./RFC-005-raptor-recursive-abstractive-tree.md) - RAPTOR 递归摘要树 (P2)
- [phase-2-retrieval-hardening.md](../phases/phase-2-retrieval-hardening.md)
- [phase-3-evaluation-hardening.md](../phases/phase-3-evaluation-hardening.md)

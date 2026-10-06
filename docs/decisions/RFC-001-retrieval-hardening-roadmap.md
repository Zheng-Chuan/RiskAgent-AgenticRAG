# RFC-001 Retrieval Hardening Roadmap

## 状态

Closed (2026-08-25 项目收口): 本 RFC 范围内的提案全部落地、验收或取消, 无遗留待办. 落地明细见下表, 评测证据见 [EVALUATION_LOG](../evaluations/EVALUATION_LOG.md).

## 落地情况 (2026-08-25 终版)

| 提案项 | 状态 | 说明 |
|---|---|---|
| Contextual Retrieval (P0) | 已实现, 默认关闭 | Qwen3-Embedding-4B 下 briefs 稀释术语信号, 定论见 [RFC-003](./RFC-003-contextual-retrieval.md) |
| qrels 升级 (P0) | 已落地 | recall 口径修正为主 gold (relevance>=2), qrels 带 chunk_id 单位 |
| 索引一致性 (P0) | 已落地 | schema fingerprint 拆分 (索引期/查询期分离), 查询开关不再触发全量重建; 评测默认只读, 重建需显式 `--reindex` |
| TARG 自适应门控 (P1) | 已落地 | query_router 实现, 金融术语词表 (词边界正则) 修复 12 题误判 (XVA/DVA/FVA/MVA/ColVA 家族) |
| CRAG 纠错检索 (P1) | 已实现并调优 | 三组数据闭环 (2026-08-25): ON (v10d) / OFF (v10e) / 混合 (v10f); 混合策略 (sufficient 门槛 0.2 -> 0.7, A/B 校准) 已上线生产: faithfulness 0.982 历史新高, recall 0.80 保住, gate 阈值/基线全过; 详见 [EVALUATION_LOG](../evaluations/EVALUATION_LOG.md) v10f |
| retrieval observability (P1) | 已落地 | trace/retrieval_diag/latency 分位数, 见 [RFC-002](./RFC-002-observability-full-chain-trace.md) |
| reranker (P1) | 已落地 | 远程 bge-reranker-v2-m3 启用 (auto fallback), trace 记实际生效模型 |
| SEAL-RAG 替换式检索 (P2) | 已实现并修复 | evidence_budget 实现 capacity=5 预算制替换 (rag/evidence_budget.py); 2026-08-24 trace 实证 145 检索节点全部执行筛选; 2026-08-25 修复跨轮重复 chunk 占位挤掉 gold 的 bug (v10e recall 回归根因, 见 v10f 台账), dedup 后 50 题 0 重复 |
| precision 口径研究 (评测方法学) | 已完成归因 | v10f precision 0.511 的 slice 定量归因: 口径假象 0.08 (重复片段计分灌水) + 补位损耗 0.09 (真实但换来 faithfulness 新高), 不回滚, 见 [PRECISION_SLICE_ANALYSIS](../evaluations/PRECISION_SLICE_ANALYSIS.md); 口径对齐改动经评审后不做 (项目收口) |
| RAPTOR (P2) | 已取消 (未启动) | 2026-08-25 收口决策: 评测集 50 题无宏观题型, 收益无法验证, 不做 |
| Agentic RAG 范式迁移 (P3) | 阶段一已实现, 迁移已取消 | 检索工具化已实现 (默认关闭), 完整迁移决定不做, 理由见 [RFC-004](./RFC-004-agentic-rag-paradigm.md) |

### 核心成果

- recall_at_5: 0.500 -> 0.82 (v10d 全量评测, v10b 为 0.78), 超出预期收益区间 0.65-0.75 的上限; 修复路径与 RFC 预设不同 (TARG 路由修复 + reranker + 口径修正, 而非 Contextual Retrieval)
- threshold gate 全绿且全量 50/50 首次达成 (v10d: faithfulness 0.903 / citation 1.000 / recall@5 0.82)
- v10f 混合策略上线: faithfulness 0.982 / recall 0.80 / contradiction 清零
- 成功标志中 "简单查询调用减少 50%" 与 "多跳 context 不膨胀" 两项未做专项统计; SEAL 预算制实证 (capacity=5 恒定, 50 题 0 重复) 间接覆盖后者

## 目标 (历史)

把项目的下一阶段投入集中到 retrieval 和 recall 强化上.  
不扩张为巨无霸 Agent 平台.  
同时引入业界最新范式: CRAG 纠错检索 / TARG 自适应门控 / SEAL-RAG 替换式检索.

## 背景 (历史)

当时项目已有比较完整的统一 RAG 主链, 真正限制上限的瓶颈:

- qrels 评测单位不够硬
- Self-RAG 充分性判断偏轻
- index manifest 和 retriever cache 版本治理不足
- query intelligence 和 advanced index 不够自适应
- retrieval recall_at_5=0.500 不达标, 需要从索引层和检索策略层同时强化

### 2026-08 业界前沿对齐

| 范式 | 来源 | 核心思想 | 落地情况 |
|------|------|----------|----------|
| CRAG | arXiv 2401.15884 | 检索后评估质量, 差则纠错重检索 | 已落地 (self_rag.py 三档 + 混合门槛) |
| TARG | TMLR 2026 | 免训练自适应检索门控 | 已落地 (query_router) |
| SEAL-RAG | arXiv 2512.10787 | 替换而非扩展, 避免 context 膨胀 | 已落地 (evidence_budget.py) |
| Contextual Retrieval | Anthropic 2024 | 索引时注入上下文摘要 | 已实现默认关闭, 见 [RFC-003](./RFC-003-contextual-retrieval.md) |

## 提案范围 (历史)

- 把 qrels 从宽松 text 匹配升级到更硬的 evidence unit
- 把 Self-RAG 充分性判断升级为 CRAG 式三档纠错检索
- 把 index manifest 和 retriever cache 升级成版本化一致性机制
- 把 query intelligence 从固定全套 fanout 升级为 TARG 式自适应门控
- 把 revise loop 从追加式升级为 SEAL-RAG 式替换式
- 为 retrieval 主链补 token latency rerank pair 等运行观测 (见 RFC-002)

以上范围全部落地; 边界外的方向 (通用多智能体平台化 / 大规模工具生态 / 前端与产品形态扩张) 维持不做.

## 关联文档

- [RFC-002](./RFC-002-observability-full-chain-trace.md) - 可观测性 (已落地)
- [RFC-003](./RFC-003-contextual-retrieval.md) - Contextual Retrieval (已实现默认关闭)
- [RFC-004](./RFC-004-agentic-rag-paradigm.md) - Agentic RAG 检索工具化 (已收口)
- [phase-2-retrieval-hardening.md](../phases/phase-2-retrieval-hardening.md)
- [phase-3-evaluation-hardening.md](../phases/phase-3-evaluation-hardening.md)

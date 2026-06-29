# RFC-001 Retrieval Hardening Roadmap

## 状态

Proposed

## 目标

把项目的下一阶段投入集中到 retrieval 和 recall 强化上.  
不扩张为巨无霸 Agent 平台.

## 背景

当前项目已经有比较完整的统一 RAG 主链.  
真正限制上限的瓶颈不再是有没有更多 agent 节点.  
而是下面这些更硬的问题.

- qrels 评测单位还不够硬
- Self-RAG 充分性判断还偏轻
- index manifest 和 retriever cache 版本治理不足
- reranker 仍是通用 baseline
- query intelligence 和 advanced index 还不够自适应

## 提案范围

- 把 qrels 从宽松 text 匹配升级到更硬的 evidence unit
- 把 Self-RAG 充分性判断升级成更强的 sufficiency scorer
- 把 index manifest 和 retriever cache 升级成版本化一致性机制
- 评估更合适的中文和金融场景 reranker
- 把 query intelligence 从固定全套 fanout 升级为更自适应的策略层
- 把 advanced index 从静态补分继续升级为 query aware expand
- 为 retrieval 主链补 token latency rerank pair 等运行观测

## 优先级

### P0 必须先做

- `qrels 升级`
  - 从 text 级命中继续升级到 chunk_id 或更硬的 evidence unit
  - 目标是让 retrieval recall 真正反映召回质量
- `索引一致性`
  - 把 embedding model chunking policy advanced index config 纳入版本键
  - 目标是避免旧索引污染新实验
- `充分性判断`
  - 把 Self-RAG 从轻量规则升级为 claim aware sufficiency scorer
  - 目标是让 stop continue 对 compare numeric multi-hop 问题更稳
- `reranker 领域适配`
  - 重新评估更贴近中文金融场景的 reranker
  - 目标是直接提升 topk 质量

### P1 随后做

- `query intelligence 自适应`
  - 不再默认每题跑全套 variants
- `advanced index query aware expand`
  - 对不同题型调不同 expand 强度
- `retrieval observability`
  - 记录 fanout 数量 rerank pairs latency token 预算

### 暂时不要做

- 通用多智能体平台化
- 大规模工具生态扩展
- 前端和产品形态扩张
- 大规模 GraphRAG 范式迁移
- 和检索召回关系不强的功能堆砌

## 不在本 RFC 范围内

- 通用多智能体平台化
- 大规模工具生态扩展
- 前端和产品形态扩张

## 建议实施顺序

1. 先做 qrels 升级和 index 版本治理
2. 再做 sufficiency scorer 和 reranker 评估
3. 然后做 query intelligence 自适应和 advanced index 深化
4. 最后补 retrieval observability 和成本治理

## 预期收益

- retrieval eval 更可信
- 检索回归更稳定
- 文档问答中的召回和证据链更硬

## 预期风险

- qrels 升级会暴露当前真实召回短板
- reranker 更换后可能带来 latency 上升
- sufficiency scorer 收紧后 可能先带来更多 revise loop
- index versioning 加强后 会增加全量重建频率

## 成功标志

- retrieval 指标能稳定区分真正有效和无效的改动
- 新旧索引结果不会因为缓存污染而混在一起
- compare numeric regulation 这些高难题型的召回和证据质量有稳定提升
- README PRD ARCHITECTURE INTERVIEW 对项目卖点的描述继续收敛到 retrieval first

## 关联阶段

- [phase-2-retrieval-hardening.md](../phases/phase-2-retrieval-hardening.md)
- [phase-3-evaluation-hardening.md](../phases/phase-3-evaluation-hardening.md)

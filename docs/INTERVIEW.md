# INTERVIEW - 面试问答集

本文件整理了针对 RiskAgent-AgenticRAG 项目的高压面试问题与参考答案.

这不是通用 RAG 八股.
这是从严格的资深面试官视角出发, 专门拷打你是否真的做过这个项目, 是否真的理解 `LangGraph` `Hybrid Retrieval` `Query Intelligence` `Advanced Index` `Artifacts` `Evaluation` `Gate` 和 `Release Acceptance` 的一份问答手册.

如果你对其中一半问题都答不上来, 那说明你对项目的理解还停留在功能介绍层, 还没有真正进入架构设计层和评测闭环层.

---

## 目录

- [项目定位与架构收敛](#position)
- [检索与索引设计](#retrieval)
- [生成 证据链 与门禁](#grounding)
- [评测 可信性 与发布验收](#evaluation)
- [资深面试官会重点拷打的 corner cases](#corner)
- [当前项目最容易被问穿的 12 个点](#weakness)
- [外部高频深水题](#external)
- [面试时建议主动说出的 8 句话](#proactive)
- [附录](#appendix)

---

<a id="position"></a>
## 项目定位与架构收敛

### 面试官: 项目定位与架构收敛拷问

---

#### Q1: "你为什么把项目从 agentic RAG 收敛成纯 RAG"

- 面试官真正想看的是 你有没有明确的系统边界感
- 强回答要点
  - 当前问题域是金融知识问答 不是任务执行
  - tool use 会把正确性问题从证据 grounding 扩展到动作正确性 权限治理 参数约束 审批链路 复杂度会明显上升
  - 这个项目的核心卖点是高可信回答和可复现评测 所以先把 retrieval grounding evaluation 做硬
  - 主链收敛后 评测口径更稳定 也更容易做 regression gate
- 继续追问
  - 你砍掉了什么能力
  - 代价是什么
  - 如果以后要重新引入 tool use 你会怎么切边界

---

#### Q2: "为什么主链要做成 `rewrite -> retrieve_and_critique -> revise -> synthesize -> validate`"

- 面试官真正想看的是 你是否理解每个节点解决什么失效模式
- 强回答要点
  - `rewrite` 解决用户自然语言和索引表达不一致
  - `retrieve_and_critique` 把检索结果是否足够回答这个问题显式化
  - `revise` 解决首轮检索 miss 和 query 表达不佳
  - `synthesize` 强制只基于检索证据生成
  - `validate` 把 refusal evidence numeric 几类硬约束放到后置门禁
- 继续追问
  - 为什么不是一次检索后直接生成
  - 为什么 critique 放在 retrieval 后而不是生成后
  - 如果 `max_rounds` 太大会发生什么

---

#### Q3: "你为什么选 LangGraph 而不是普通链式代码"

- 面试官真正想看的是 你有没有把流程图映射到工程执行模型
- 强回答要点
  - 当前项目的核心不是多 agent 对话 而是有限循环状态机
  - LangGraph 比较适合表达 `retrieve -> critique -> revise` 这种可控 loop
  - 每一步都能写 trace 和 decision_log 更利于回放和评测
  - 以后要做更强的 release gate 时 状态图比自由 prompt 流更容易审计
- 继续追问
  - 这是不是过度设计
  - 直接 if else 能不能做
  - LangGraph 给你带来的独特收益是什么

---

#### Q4: "为什么现在把 query intelligence 和 advanced index 都收进默认主链了"

- 面试官真正想看的是 你是否知道什么时候该收口单一主链
- 强回答要点
  - 早期把能力拆成渐进实验阶段 是为了逐层验证收益与定位问题
  - 收口后默认主链直接变成 `hybrid + query intelligence + advanced index`
  - 这样文档 运行时行为 和发布口径更一致
  - 复杂度没有消失 但被压回到同一条可验收主链里
- 继续追问
  - 收口后如何避免 latency 失控
  - 统一主链后怎么继续做 ablation
  - 为什么不保留 mode 开关给线上配置

---

#### Q5: "为什么这个项目不做长期用户记忆"

- 面试官真正想看的是 你是否知道知识库检索和用户记忆是两个问题
- 强回答要点
  - 当前项目目标是知识 grounding 不是个性化对话代理
  - 当前 chat 只收敛最近几轮 history 用于当前 query rewrite
  - Milvus 存的是知识库 chunk 不是用户 profile
  - 过早引入长期记忆会把问题变成 memory contamination 和 tenant isolation
- 继续追问
  - 多轮污染怎么处理
  - 如果未来要加长期记忆 你会怎么隔离

---

<a id="retrieval"></a>
## 检索与索引设计

### 面试官: 检索与索引设计拷问

---

#### Q6: "你们为什么做 hybrid retrieval 而不是纯 dense"

- 强回答要点
  - 金融领域有大量缩写 条款名 数值 监管代号 纯 dense 容易 miss lexical exact match
  - sparse 更擅长 exact term 和 jargon
  - dense 更擅长语义同义改写
  - hybrid 能提升 recall 上界 然后再交给 reranker 压噪
- 继续追问
  - 你怎么融合 dense 和 sparse
  - 为什么用 RRF 而不是简单加权

---

#### Q7: "你们的 query intelligence 到底做了什么"

- 强回答要点
  - 当前主要是规则驱动的 query variant 构造
  - 包括 keywordize acronym expansion route recognition step back decomposition
  - compare 问题会拆子问题
  - background 和 procedure 问题会补更泛化的 step back query
  - 多个 variant 分别检索 再做 variant 级 RRF 融合
- 继续追问
  - 为什么不用 LLM 直接生成很多 rewrite
  - 规则路由在中英文混合和金融缩写上会不会误判
  - compare 拆分为什么上限是 4

---

#### Q8: "你们的 chunking 为什么是 parent child 两层"

- 强回答要点
  - child chunk 用于高精度检索
  - parent 用于回答时补更长上下文和 advanced index 扩展
  - 这比纯大 chunk 更利于召回 比纯小 chunk 更利于回答完整性
  - 对法规和长文档来说 parent expand 能减少证据碎片化
- 继续追问
  - parent expand 会不会把噪声也带回来
  - 什么时候 child 找到了但 parent 错了

---

#### Q9: "你们为什么额外存 `sparse_corpus.jsonl` `parent_corpus.jsonl` `summary_corpus.jsonl` `hyde_corpus.jsonl`"

- 强回答要点
  - dense 向量库不是唯一真相
  - sparse 语料服务 BM25
  - parent 语料服务 expand
  - summary 语料给主题级召回
  - hyde 语料给表达差异补偿
  - 这样每种索引能力都有可单独检查的物化产物
- 继续追问
  - 多份索引会不会一致性失控
  - 删除和更新时怎么保证一起更新

---

#### Q10: "你们的 rerank 为什么放在 hybrid retrieval 后"

- 强回答要点
  - cross-encoder 更准但更贵
  - 应该放在 recall 之后做 topN 精排
  - 先 hybrid 提 recall 上界 再 rerank 压噪是比较常见的多阶段 retrieval 结构
  - 这也让 latency 更可控
- 继续追问
  - rerank_k 怎么定
  - 如果 reranker 模型本地没预热怎么办

---

#### Q11: "你们做 diversity select 的收益和副作用是什么"

- 强回答要点
  - 收益是避免 topk 全部来自同一个 source 或同一 section
  - 这能减少 context redundancy 和 generation 偏置
  - 副作用是可能切掉同一法规中连续出现的关键证据
  - 所以它本质是 recall 和 diversity 的 trade-off
- 继续追问
  - `max_per_source=2` `max_per_section=1` 为什么这样配
  - 如果用户问非常细粒度条款 会不会被多样性约束伤害

---

#### Q12: "advanced index 的价值是什么"

- 强回答要点
  - summary index 补宏观主题信号
  - HyDE 补 query 和 doc 表达差异
  - parent expand 补回答上下文
  - 这几层的目标都是在不改主生成逻辑的前提下提升 evidence coverage
- 继续追问
  - 为什么 summary 和 hyde 都是 BM25 而不是向量
  - 打分怎么融合
  - 这些权重怎么校准

---

#### Q13: "如果面试官问 你们的打分融合为什么可靠 你怎么答"

- 强回答要点
  - 要先诚实说当前实现是启发式融合 不是 learned ranker
  - coarse_score 来自 `rrf_score + 0.5 * bm25_score + metadata_boost`
  - advanced_index_score 在 base_score 上再叠 summary 和 hyde
  - 这套方案的优点是可解释和易调
  - 缺点是不同分数项量纲不完全一致 需要后续做 calibration 或 learning to rank
- 继续追问
  - 为什么不是统一归一化后再学一个融合器
  - 现在这套启发式如何避免某一项 dominate

---

#### Q14: "你们的增量索引怎么保证一致性"

- 强回答要点
  - 当前增量索引以 source 文件 sha1 为主
  - 每次会删除该 source 对应旧 chunk 再重建 dense sparse parent summary hyde
  - manifest 会记录 embeddings provider model dim 和每个 source 的索引摘要
  - 但这里要诚实说明 目前跳过逻辑主要看文件 sha1 还没有把 embedding 版本变化纳入 skip 条件
- 继续追问
  - 如果 embedding 模型换了 但原文没变 会发生什么
  - 如果 collection 维度和新模型不一致 会怎么处理

---

#### Q15: "如果面试官问文档删除怎么做 你怎么答"

- 强回答要点
  - 当前最稳妥的路径是按 source delete 再 upsert
  - 这能保证同一个 source 的 dense 和多类 jsonl 语料一起更新
  - 但项目当前更偏本地实验和增量重建 还没有做严格的 tombstone 和后台 compaction 设计
- 继续追问
  - stale chunk 怎么清理
  - cache 和索引版本怎么同步

---

<a id="grounding"></a>
## 生成 证据链 与门禁

### 面试官: 生成 证据链 与门禁拷问

---

#### Q16: "为什么生成阶段严格只允许用检索上下文"

- 强回答要点
  - 这个项目的核心是高可信 grounding
  - 生成阶段如果再引入工具结果或自由世界知识 证据边界就会被打穿
  - 只有保持纯证据生成 评测和门禁才有清晰对象
- 继续追问
  - 如果检索结果不够但模型自己知道答案怎么办
  - 为什么不允许常识补全

---

#### Q17: "你们的 citation 是怎么挂到答案里的"

- 强回答要点
  - 当前是段落级启发式挂引用
  - 用 paragraph token 和 citation snippet token overlap 做匹配
  - 每个段落取 overlap 最强的 top 引用
  - 这让答案段落和 evidence 粒度可以对齐
  - 但要诚实说明 这还是 heuristic 不是 sentence-level exact attribution
- 继续追问
  - overlap >= 2 为什么合理
  - 语义支持但词面差异大怎么办
  - 语义相反但共享关键词会不会误判

---

#### Q18: "claims 和 evidence_set 是怎么构造的"

- 强回答要点
  - evidence_set 由最终 docs 构建 每条带 evidence_id source chunk_id start_index 等信息
  - claims 由答案段落切分得到 每条 claim 要绑定 evidence_ids
  - 如果正文里能解析到 `chunk_id=...` 就直接映射
  - 否则会 fallback 到 overlap 最大的 evidence
- 继续追问
  - 这个 fallback 会不会制造虚假的自洽
  - 你怎么证明 claim 真被 support

---

#### Q19: "evidence gate 的核心逻辑是什么"

- 强回答要点
  - 每条 claim 必须有 evidence_ids
  - evidence_id 必须存在于 evidence_set
  - evidence 必须有 `chunk_id`
  - claim statement 和 linked evidence snippet 至少有基本 token overlap
  - 这是一套确定性 hard gate 不是主观打分
- 继续追问
  - token overlap 过于弱怎么办
  - 如果 evidence 语义是反的 但词很像 怎么办

---

#### Q20: "numeric gate 为什么单独存在"

- 强回答要点
  - 金融问答里数字错误的风险远高于一般文本错误
  - 所以项目把 refusal evidence numeric 三类 gate 分开
  - 当前 numeric gate 对纯 RAG 路径比较保守
  - 没有 tool_traces 时 只检查数字是否有 evidence
  - 更强的数字真伪检查更多下放给离线评测的 numeric consistency
- 继续追问
  - 那线上是不是会放过错误数字
  - VaR ES capital ratio 这种数字问题现在真的安全吗

---

#### Q21: "为什么 LLM appeal 默认关闭"

- 强回答要点
  - 正式评测里 gate 失败如果还能被 LLM 覆盖 会破坏门禁的确定性
  - 这会让审计和回归对比变得不稳定
  - 所以默认关闭 只有显式环境变量才打开
- 继续追问
  - 那你为什么还保留这个能力
  - 在什么场景你会临时开 appeal

---

#### Q22: "refusal gate 的价值是什么"

- 强回答要点
  - 它确保 retrieval empty 或 evidence empty 时系统不硬编
  - 对高风险领域 不知道就拒答 比自信地错更重要
  - refusal 不是体验优化 而是风险控制
- 继续追问
  - 过度拒答怎么衡量
  - 你怎么区分 evidence 不足和 prompt 写得差

---

<a id="evaluation"></a>
## 评测 可信性 与发布验收

### 面试官: 评测 可信性 与发布验收拷问

---

#### Q23: "你们为什么把 retrieval eval 和 generation eval 拆开"

- 强回答要点
  - 不拆开就无法归因
  - retrieval 问题应该看 gold evidence 有没有被召回
  - generation 问题应该看答案是否被证据支持
  - 同一个 badcase 可能是 recall 不够 也可能是 answer hallucination
  - 这就是为什么项目引入 qrels 和 answer_eval 两条线
- 继续追问
  - 以前不拆开时有什么问题
  - citation 反推 retrieval 为什么会有自举偏差

---

#### Q24: "qrels 在这个项目里解决了什么问题"

- 强回答要点
  - qrels 把 retrieval 的 gold truth 从生成结果里独立出来
  - retrieval recall@k MRR nDCG 不再依赖模型最后怎么回答
  - 这让检索实验更像 search system evaluation
- 继续追问
  - qrels 的粒度应该是 doc 还是 chunk
  - 一题多 relevant chunk 怎么算

---

#### Q25: "你们的 answer_eval 包含哪些指标"

- 强回答要点
  - `citation_coverage`
  - `faithfulness`
  - `answer_relevancy`
  - 句级支持还会输出 supported 和 unsupported sentences
  - 金融专项还有 numeric 和 glossary consistency
- 继续追问
  - 这些指标哪个最重要
  - 哪个最容易被刷

---

#### Q26: "你们为什么不把 LLM as judge 当唯一标准"

- 强回答要点
  - judge 模型不稳定 成本高 且难审计
  - 同一答案不同 judge 或不同 prompt 可能给不同分
  - 当前项目把规则和可复核指标放在前面
  - LLM judge 只保留在 citation precision 的可选模式里
  - 离线回归默认走 heuristic 保证可复现
- 继续追问
  - heuristic 会不会过于粗糙
  - 那 faithfulness 现在到底有多可信

---

#### Q27: "threshold failure 和 baseline regression 为什么要分开"

- 强回答要点
  - threshold failure 解决的是达不达最低可发布标准
  - baseline regression 解决的是相对上一版本有没有退化
  - 两者语义不同 不能混成一个 fail 字段
  - 分开后才能清楚回答 是系统没及格 还是及格但比上个版本退化
- 继续追问
  - 如果 threshold pass 但 baseline regress 怎么办
  - warning 该不该挡发布

---

#### Q28: "你们的 offline regression 解决了什么工程问题"

- 强回答要点
  - 把共享环境里的无关 pytest 插件噪声隔离掉
  - 固定离线环境变量
  - 固定 `EMBEDDINGS_PROVIDER=hash`
  - 固定 `EVAL_CITATION_JUDGE_MODE=heuristic`
  - 让最小回归集可以在无在线 judge 条件下稳定执行
- 继续追问
  - hash embeddings 会不会让回归结果失真
  - 为什么不直接跑真实 embedding

---

#### Q29: "你们的 release acceptance 真的验收了当前代码吗"

- 强回答要点
  - 这里要诚实
  - 当前脚本先跑 offline regression
  - 然后加载仓库里的 baseline sample report 和 threshold config 做断言
  - 它验证了门禁流程和报告结构
  - 但没有重新跑一份当前版本评测报告
  - 所以它更像发布合规 smoke check 而不是 full end to end fresh eval
- 继续追问
  - 那你验收的是代码还是历史样例
  - 如果要升级成更严格的 release gate 你会怎么改

---

#### Q30: "如果面试官质疑你们的评测可不可信 你应该主动承认什么"

- 强回答要点
  - 当前 qrels 还是文本匹配驱动 不是严格 chunk_id 对齐
  - gate_labels 样本规模还偏小
  - answer_relevancy 在没有 ragas 时会退化成 heuristic overlap
  - release acceptance 目前依赖静态 baseline sample
  - 这几个点都是真实边界 但项目已经把问题显式化 并且有明确补强方向
- 继续追问
  - 下一步最优先补哪个
  - 为什么先补那个

---

<a id="corner"></a>
## 资深面试官会重点拷打的 corner cases

### 面试官: corner cases 拷问

---

#### Q31: "如果 embedding 模型换了 但文档没变 你们的增量索引会怎样"

- 当前真实风险
  - skip 条件主要看 source sha1
  - embedding provider model dim 会写进 manifest
  - 但不会强制因为 embedding 变更而重建所有 source
- 这道题的推荐回答
  - 先承认当前实现有索引一致性漏洞
  - 再给出补法
    - 把 embedding provider model dim 纳入 manifest version key
    - mismatch 时强制 full rebuild
    - 同时清 collection 和多类 jsonl 物化文件

---

#### Q32: "如果统一主链里某一层配置变了 会有什么风险"

- 当前真实风险
  - `RiskAgentSystem` 复用 retriever 只看 persist_dir
  - 如果 cache key 不纳入 reranker 和统一检索配置 会出现配置漂移
- 推荐回答
  - 这是典型配置漂移问题
  - 生产上应该把 retriever cache key 扩成 `(persist_dir, pipeline_config, reranker_model, dense_k, sparse_k, rerank_k, embeddings version)`

---

#### Q33: "如果文档解析失败 你们怎么知道 recall hole 出现了"

- 当前真实风险
  - loader 对解析失败更偏 warning 后 continue
  - 索引成功不等于语料完整
- 推荐回答
  - 当前项目更偏本地实验 这里确实还不够强
  - 生产化应补
    - source ingestion success rate
    - failed source inventory
    - manifest completeness check
    - publish gate on missing critical docs

---

#### Q34: "如果 compare 问题被错误拆分 会发生什么"

- 当前真实风险
  - decomposition 依赖 regex 和连接词切分
  - 金融复合问句容易误拆
- 推荐回答
  - 错拆会导致 variant 检索偏移 和 recall 噪声变高
  - 解决方向是
    - 加实体边界保护
    - 对缩写和产品名做 lexicon
    - 记录 variant-level ablation
    - 用 qrels 按题型看 compare slice 是否真实收益

---

#### Q35: "如果 topk 都来自同一篇法规 你们的多样性约束会不会伤害正确答案"

- 推荐回答
  - 会 有这个风险
  - 多样性约束不是无条件更好
  - 对 definition 或 broad background 问题它常常有帮助
  - 对 very local clause 问题可能会伤 recall
  - 所以最终应该按 tags 看 slice metrics 而不是看全局均值

---

#### Q36: "如果 evidence overlap 很高 但语义相反 你们现在会不会误判 support"

- 当前真实风险
  - 会 有可能
  - 当前 evidence gate 主要是 deterministic guardrail 不是高语义 NLI verifier
- 推荐回答
  - 先承认当前 evidence gate 是低成本 hard check
  - 真正更强的语义支持仍依赖 sentence-level citation diagnostics 和更强 judge
  - 如果要进一步生产化 可以引入 sentence claim verification 模块

---

#### Q37: "如果答案里数字有证据 但数字本身是错的 线上 gate 能挡住吗"

- 当前真实风险
  - 纯 RAG 路径下 numeric gate 主要看有无 evidence
  - 不足以判断数字真伪
- 推荐回答
  - 这是当前已知边界
  - 线上 gate 做的是 fail-fast
  - 更细的数字一致性现在主要在离线 eval
  - 下一步要做的是数字型问题识别扩展 和 evidence 数字重算

---

#### Q38: "如果离线环境没有 HF 模型缓存 会发生什么"

- 当前真实风险
  - 项目强制 offline
  - reranker 和 embeddings 默认都假设本地已有模型
- 推荐回答
  - 这是可复现性和冷启动便利性的 trade-off
  - 当前离线回归通过 hash embeddings 避开了一部分依赖
  - 但真实运行仍需要明确模型预热和环境安装文档

---

#### Q39: "如果用户持续追问 多轮历史越来越长 你们怎么避免污染当前检索"

- 当前真实情况
  - 只拼最近 3 轮 history
  - 没做 role aware summarization
- 推荐回答
  - 这是有意识地用硬截断控制污染
  - 当前先做简单稳定版
  - 后续如果要做更强 多轮摘要和 retrieval memory 会是下一步

---

#### Q40: "如果 API secret 忘了改 会有什么风险"

- 当前真实风险
  - 默认 secret 是 `change-me-in-production`
- 推荐回答
  - 直接承认这是开发默认值 生产必须由部署层覆盖
  - 更强做法是启动时检测默认 secret 并 fail fast

---

<a id="weakness"></a>
## 当前项目最容易被问穿的 12 个点

### 面试官: 薄弱点追问

---

### 1. `release_acceptance.sh` 只校验静态 baseline sample report

- 你要主动承认它不是 fresh eval
- 你要说明它当前的价值是发布 smoke check
- 你要给出后续整改方向
  - 先现跑 `evaluation.run`
  - 再加载当前 report 做 gate

### 2. `answer_eval.ok` 当前更多表示执行成功 不是达标通过

- 这里最容易被抓语义不清
- 你要主动把 `execution_ok` 和 `threshold_pass` 分开讲

### 3. qrels 目前更接近文本匹配 不是严格 chunk_id 对齐

- 这是 retrieval eval 可信度的第一风险点
- 正确应对方式不是硬辩
- 而是明确说下一步要改成 chunk_id 级 gold

### 4. gate_labels 样本太小 且正样本不足

- 这会导致 gate benefit false kill miss rate 统计意义偏弱
- 你要直接承认样本规模仍需扩

### 5. retriever cache key 太窄

- 只看 persist_dir 不看 mode 和配置
- 这是运行态一致性风险

### 6. 索引 skip 条件太弱

- 只看 source sha1 不看 embedding version
- 这是索引漂移风险

### 7. 分数融合是 heuristic 不是 calibrated fusion

- 优点是可解释
- 缺点是量纲未完全统一

### 8. citations 和 claims 绑定仍带 heuristic fallback

- 这会带来自洽假象风险

### 9. numeric gate 对纯 RAG 路径偏弱

- 有证据不等于数字真

### 10. loader 失败更偏 warning 而不是强门禁

- 这会造成 silent recall hole

### 11. offline regression 依赖 hash embeddings

- 它解决了可复现
- 但不是最终真实效果证明

### 12. 默认 API secret 需要部署层覆盖

- 这是基本安全 hygiene 问题

<a id="external"></a>
## 外部高频深水题

### 面试官: 系统设计与外部题型追问

---

#### Q41: "设计一个 p99 小于 1.5s 的 production RAG 你会怎么拆 latency budget"

- 推荐回答框架
  - rewrite
  - retrieve
  - rerank
  - assemble
  - generate
  - gate
  - logging
- 面试官继续会问
  - 哪一段最容易炸
  - 哪一段最先降级

---

#### Q42: "10 million docs 和 50 QPS 的 RAG 你怎么估算容量"

- 推荐回答框架
  - chunk 数量估算
  - embedding 维度和向量存储体积
  - BM25 倒排规模
  - rerank 每秒 pair 数
  - LLM token cost

---

#### Q43: "如果知识库文档更新和删除很频繁 你怎么做 safe upgrade"

- 推荐回答框架
  - versioned index
  - blue green 或 shadow index
  - tombstone
  - cache invalidation
  - rollback

---

#### Q44: "multi-tenant RAG 怎么避免数据串租户"

- 推荐回答框架
  - tenant level collection 或 filter
  - cache key 带 tenant
  - artifact trace 脱敏
  - evaluation 也要 tenant aware

---

#### Q45: "prompt injection 从向量库进入系统 你怎么防"

- 推荐回答框架
  - content sanitization
  - indexed content signing
  - retrieval result trust boundary
  - model prompt 中明确内容只作 evidence 不是 instruction

---

#### Q46: "你如何判断某次错误是 chunking 问题 还是 retrieval 问题 还是 generation 问题"

- 推荐回答框架
  - 先看 gold chunk 是否存在于索引
  - 再看 recall@k 是否命中
  - 再看 rerank 是否打掉正确 chunk
  - 再看 answer 是否正确使用了已召回证据

---

#### Q47: "你怎么定义 hallucination rate"

- 推荐回答框架
  - 没有证据支持的 claim 比例
  - 句级 unsupported sentence rate
  - 数字不一致也应纳入高风险 hallucination

---

#### Q48: "如果你只能保留 3 个 RAG 指标 你留什么"

- 推荐回答框架
  - retrieval recall@k
  - faithfulness
  - answer relevancy 或 task success
- 然后再说明在高风险领域为什么 numeric consistency 其实也很重要

---

<a id="proactive"></a>
## 面试时建议主动说出的 8 句话

- 这个项目最关键的设计不是多加一个 fancy retriever 而是把 retrieval generation gate evaluation 拆清楚
- 我们刻意把主链收敛成统一证据链路 默认固定走 hybrid query intelligence advanced index 数值型问题再按需补风险工具 这样评测口径和证据边界更稳定
- 当前线上口径不再切换 step mode advanced index 已经并入默认主链 Self-RAG 负责检索充分性判断和 early stopping 而不是单独代表另一套检索模式
- 当前 retrieval eval 已经比最早版本更可信 因为引入了 qrels 但它还没有走到 chunk_id 级 gold 这是下一步要补的
- 我们默认关闭 LLM appeal 是因为 release gate 必须 deterministic
- 离线回归真正解决的是可复现性 而不是证明真实线上效果已经最优
- 我知道当前代码里最脆弱的点是索引一致性 证据链 heuristic fallback 和发布验收还没现跑 fresh eval
- 如果要继续做强 我会优先补 release gate 绑定当前报告 qrels chunk_id 对齐 以及更强的数字真实性校验

---

<a id="appendix"></a>
## 附录. 这份文档参考过的外部口径

- Production RAG 的高频深水题来自近两年的工程化资料和题库 重点参考了 latency budget hybrid retrieval reranking evaluation observability security 这些方向
- 主要参考入口
  - https://prachub.com/interview-questions/design-a-low-latency-rag-system
  - https://www.elysiate.com/blog/rag-systems-production-guide-chunking-retrieval-2025
  - https://huru.ai/llm-engineer-interview-questions-rag-prompting-evaluation/
  - https://github.com/adongwanai/AgentGuide/blob/main/docs/04-interview/02-rag-questions.md
  - https://github.com/euronone/Gen-ai-interview-Questions-and-answers/blob/main/06-rag-retrieval/README.md

---

## 最后建议

- 先把前 10 题讲熟 因为它们几乎一定会连环追问
- 再把第六部分的 12 个薄弱点背熟 因为这是最容易被问穿的地方
- 如果你能把每个问题都答成 现状 -> trade-off -> 风险 -> 下一步 这轮面试基本就不会虚

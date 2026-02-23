# HIGHLIGHT

## 系统运行流程

**把ROADMAP的四块放到一条时间轴里**
- Week 9 查询理解与智能路由 先发生, 先决定用什么检索策略, 再把一个问题拆成多种问法并行跑
- Week 8 混合检索与重排序 接在后面, 对每个query变体做混合召回, 粗排, 精排, 多样性重排, 同时输出置信度信号
- Week 10 高级索引策略 在拿到候选chunk后发生, 用parent child回填长上下文, 再用summary和HyDE对同一parent做额外加权, 解决宏观问题与长文档问题
- Week 11 Self RAG与动态决策 贯穿检索到生成前后, 用显式打分和门控决定继续检索, 拒答, 或进入生成, 生成后再做一次质量门禁

**一条异常信号触发后的时间流程 先做什么后做什么**
1) 输入进入agentic loop
- 输入可以是用户问句也可以是你说的异常信号文本化, 比如 某desk delta超限 需要解释和证据
- 编排节点顺序固定, rewrite -> retrieve_and_critique -> revise_query可循环 -> decide_tool_use -> call_tool可选 -> synthesize_answer -> validate_and_save

2) rewrite 先把输入改写成更像检索query的形态
- 目标是把口语化表述压成关键词和领域术语, 提升后面混合检索的召回稳定性

```python
question = state["question"]
rewritten = agentic_primitives.rewrite_query(question)
state["current_query"] = rewritten
```

3) Week 9 查询理解与智能路由
- 先做semantic router, 给问题打意图标签, 例如 compare, background, procedure, default
- 再生成query variants, 包含关键词化, 缩写展开, step back背景query, 对比类拆子问题
- 这些variants不是为了让LLM更聪明, 是为了让检索侧覆盖更多表达, 避免只靠一次向量检索

```python
route = _route_name(q)
variants = generate_query_variants(question=q, base_query=q, config=self._config)
for v in variants:
    docs = list(self._base.invoke(v))[: self._config.per_query_k]
```

4) Week 8 混合检索与重排序
- 对每个variant做dense向量召回加sparse BM25召回, 用RRF融合
- 召回后先做citation aware filter和min chunk过滤, 再做coarse scoring压缩候选
- 然后cross encoder reranking精排
- 最后diversity rerank做多样性约束, 同时写入confidence gap信号给后续动态决策用

```python
rrf = _rrf_scores(ranked_lists=[dense_rank, sparse_rank], k=self._config.rrf_k)
for d in candidates:
    d.metadata["coarse_score"] = self._coarse_score(d)
scores = self._reranker.predict([(q, d.page_content or "") for d in rerank_candidates])
```

5) Week 10 高级索引策略
- Parent child indexing small to big, 命中child后回填parent文本, 给LLM更完整上下文
- Summary indexing, 对每个section摘要建索引, 宏观问题优先命中摘要对应的parent
- HyDE indexing, 为chunk生成假设性问题并建索引, 缓解query和原文表述不一致
- 这三者最后统一落到同一个parent_id维度上做加权, 把长文档问题从结构层面解决掉

```python
if self._config.expand_parent and pid and pid in self._parent_by_id:
    parent = self._parent_by_id[pid]
    meta["expanded_text"] = str(parent.page_content or "")[: self._config.max_expand_chars]
```

6) Week 11 Adaptive retrieval加Self RAG scoring 发生在检索完成后立刻门控
- grade_docs会产出IsRel, IsSup, IsUse三类信号
- IsUse会吃掉前面Week 8写入的confidence gap, 这是把检索侧置信度显式输送到决策侧
- 然后should_continue决定走不走下一轮检索, 或者直接进入tool决策与生成

```python
g = grade_docs(question=question, docs=docs)
self_sufficient = bool(g.sufficient)
should_continue = (not bool(sufficient or self_sufficient)) and (next_round < max_rounds)
```

7) 异常信号真正落地的位置
- 如果你的异常信号来自外部风险监控, 在这个项目里它会通过tool输出结构化进来
- tool返回breaches和alerts, 这就是异常信号进入系统状态的那一刻
- 后续生成答案时会把tool_output和检索到的上下文一起喂给LLM, 再在validate阶段做数值一致性门禁

```python
tool_output = monitor_desk_exposure(desk=desk, as_of=as_of_str, abs_delta_limit=request.abs_delta_limit)
breaches = tool_output.get("breaches", [])
```

8) 生成与落盘
- synthesize_answer会把docs加tool_output合成最终报告, 并附citation
- validate_and_save会抽claims, 构建evidence_set, 做校验并产出status和failure_reason
- Week 11的grade generation也在这里发生, 把生成质量结果写入decision_log

**按你举例的方式给两条具体时间链**
- 链A 风险异常类问题
  - 先触发 Hybrid search
  - 后触发 Cross encoder reranking
  - 后触发 Parent child indexing small to big
  - 后触发 Adaptive retrieval, grade docs, decide继续检索或停止
  - 后触发 tool调用产生 breaches, 这一步把异常信号结构化
  - 后触发 generate并在validate里做numeric consistency门禁

- 链B 宏观解释类或对比类问题
  - 先触发 Semantic router
  - 后触发 Query expansion加Step back prompting, 如果是对比类再触发 Sub question decomposition
  - 后触发 Hybrid search加Cross encoder reranking并行跑多个variants
  - 后触发 Summary indexing加HyDE indexing给parent加权
  - 后触发 Adaptive retrieval决定是否继续多轮检索, 不够就revise_query再回到检索

**两个开放问题 方便你把ROADMAP的解释写得更落地**
- 你希望异常信号的唯一标准是什么, tool breaches, 检索不足, 还是最终validate failed
- 你希望路由层只影响检索策略, 还是也影响后续tool决策和校验强度比如是否强制numeric backing

## 关键机制问答

1) Week 10 分别涉及哪些策略, 适用什么情况  
- Parent child indexing small to big  
  - 策略: 检索命中child chunk以后, 额外回填同一parent的更大上下文到expanded_text, 给LLM更完整上下文  
  - 适用: 长文档里某个细节命中但回答需要上下文, 或者需要跨段落解释因果和定义, 避免只拿到一小段导致断章取义  
  - 关键实现形态  

```python
if expand_parent and pid in parent_by_id:
    parent = parent_by_id[pid]
    meta["expanded_text"] = parent.page_content[:max_expand_chars]
```

- Summary indexing  
  - 策略: 每个section生成摘要并建稀疏索引, 用摘要命中来提升宏观问题的召回  
  - 适用: 概览, 背景, 定义, 总结类问题, 原文chunk太细会被细节噪音淹没  
  - 关键实现形态: summary_bm25给parent_id打分, 再加权进advanced_index_score  

```python
summary_map = parent_score_map(summary_bm25, summary_docs, query=q, k=summary_k)
adv = base_score + summary_weight * summary_map.get(pid, 0.0)
```

- HyDE indexing  
  - 策略: 为chunk生成假设性问题并建稀疏索引, 让question to question更容易匹配  
  - 适用: 用户问法和文档表述差异大, 例如文档用术语, 用户用口语, 或跨语言表达  
  - 关键实现形态: hyde_bm25给parent_id打分, 再加权进advanced_index_score  

```python
hyde_map = parent_score_map(hyde_bm25, hyde_docs, query=q, k=hyde_k)
adv = base_score + hyde_weight * hyde_map.get(pid, 0.0)
```

2) Week 9 智能路由依据什么路由, 查询改写策略有哪些, 适用什么情况  
- 路由依据  
  - 基于轻量规则做意图分类, 主要看关键词和中文触发词, 输出 compare, background, procedure, default  
  - compare: 含 vs, compare, difference, 对比, 区别  
  - background: 含 overview, background, define, definition, 是什么, 介绍  
  - procedure: 含 compute, calculation, formula, 怎么算, 公式  

```python
if "对比" in t or re.search(r"\b(vs|compare|difference)\b", t):
    return "compare"
if "是什么" in t or re.search(r"\b(overview|background|define|definition)\b", t):
    return "background"
if "怎么算" in t or re.search(r"\b(compute|calculation|calculate|formula)\b", t):
    return "procedure"
return "default"
```

- 查询改写策略, 以及适用场景  
  - keywordize  
    - 做法: 去掉停用词, 保留更像关键词的token  
    - 适用: 原问题很口语, 含大量功能词, 需要提升BM25召回稳定性  
  - expand abbrev  
    - 做法: 扩写常见缩写, 例如 frtb, cva, xva, var, es  
    - 适用: 专有名词缩写容易漏召回, 扩写能同时命中缩写和全称  
  - step back prompting  
    - 做法: 生成一个更抽象的背景query, 例如 overview definition background + head terms  
    - 适用: 问题需要定义和背景铺垫, 或用户问法太具体但缺上下文  
  - sub question decomposition  
    - 做法: 只对compare类问题拆分子问题, 并行检索后再融合  
    - 适用: 对比类问题天然是多子任务, 单次query很难同时命中两边证据  

```python
use_step_back = enable_step_back and route in {"background", "procedure", "compare"}
use_decomposition = enable_decomposition and route == "compare"
```

3) rewrite是怎么做的, 只是更改数据格式吗, 还是调用了LLM  
- rewrite不是改格式, 是调用LLM做query rewriting  
- 关键点  
  - prompt要求返回JSON, schema是 {"query": "..."}  
  - temperature固定0.0, 目标是稳定可复现  
  - 如果LLM没给出query就fallback原问题  

```python
data = call_llm_json(prompt, temperature=0.0)
query = str(data.get("query", "")).strip()
return query or question
```

4) Week 8 这些概念分别是什么, 代码里怎么做的  
- min chunk过滤是什么  
  - 这是citation aware filter的一个子集, 目标是过滤信息密度低的chunk, 降低噪音  
  - 当前实现包含  
    - 长度下限 min_chunk_chars  
    - 字母数字占比阈值, 防止全是符号或目录  
    - 少量硬编码噪音模式过滤  

```python
if len(text) < min_chunk_chars:
    return False
alnum = sum(1 for ch in text if ch.isalnum())
if alnum < max(10, int(len(text) * 0.15)):
    return False
if "table of contents" in lowered:
    return False
```

- RRF是什么  
  - Reciprocal Rank Fusion, 多路rank融合, 每条结果按名次贡献 1.0 / (k + rank + 1)  
  - 好处是对不同召回器的尺度不敏感, 易融合  

```python
scores[key] += 1.0 / float(k + rank + 1)
```

- BM25召回和dense向量召回是什么  
  - BM25是稀疏检索, 基于token匹配和词频统计, 擅长专有名词和精确词匹配  
  - dense向量是语义检索, 基于embedding相似度, 擅长同义改写和语义相近  
  - 代码里dense来自 dense_retriever.invoke, sparse来自 BM25Okapi.get_scores  

```python
dense_docs = dense_retriever.invoke(q)
scores = bm25.get_scores(tokenize(sparse_query))
```

- coarse scoring是什么  
  - 在RRF融合后做轻量打分, 把候选压缩到可控规模再进cross encoder  
  - 当前公式是 rrf_score + 0.5 * bm25_score + metadata_boost  

```python
def _coarse_score(d):
    return rrf + 0.5 * bm25 + boost
```

- cross encoder reranking是调用模型吗  
  - 是, 使用 sentence_transformers.CrossEncoder, 对每个 (query, doc_text) 输出一个相关性分数  
  - reranker_model来自配置, 空则跳过rerank  

```python
self._reranker = CrossEncoder(reranker_model)
scores = self._reranker.predict([(q, d.page_content or "") for d in rerank_candidates])
```

- diversity rerank是怎么做的  
  - 不是额外模型, 是规则式多样性选择  
  - 先按分数排序, 再按source配额和section配额挑选, 防止单篇文档霸榜, 最后再补齐  

```python
if source and per_source[source] >= max_per_source:
    continue
if section and per_section[section] >= max_per_section:
    continue
picked.append(d)
```

5) Week 11 三类信号是什么, isUse吃掉是什么意思  
- 三类信号来自SelfRAG的最小可计算版本  
  - IsRel: question tokens与doc tokens重叠比例, 越大越相关  
  - IsSup: 是否有最小支撑, 当前规则是重叠token至少2个就算支撑  
  - IsUse: 是否值得用, 优先用检索侧的置信度信号 confidence_gap_to_top1 来判断  
- isUse吃掉不是覆盖, 是优先使用更强的信号源  
  - 如果文档有confidence_gap_to_top1, 就用 gap阈值来算IsUse  
  - 如果没有gap, 才回退用 isrel阈值来算IsUse  

```python
if gap is not None:
    isuse = 1.0 if gap <= 0.4 else 0.0
else:
    isuse = 1.0 if isrel >= 0.15 else 0.0
```

6) 数值一致性门禁是什么  
- 这是validator里的 numeric_consistency_gate  
- 核心目的: 只要回答或claims里出现关键数字, 就必须能回指到tool_traces里的结构化输出, 防止LLM编数字  
- 当前规则是MVP但已经可用  
  - 如果 report或claims包含数字, 但没有tool_traces, 直接失败 numeric_inconsistent  
  - 如果有tool_traces, 就抽取tool_output里的所有数字, 对claims里的数字做匹配  
  - 匹配容差包含绝对误差和相对误差, 相对误差默认1 percent  

```python
if (report_numbers or claim_numbers) and not tool_traces:
    return {"category": "numeric_inconsistent", ...}

if abs((x - y) / y) <= 0.01:
    return True
```

7) 生成与落盘具体写下了哪些数据  
- 生成阶段产物  
  - answer, citations  
  - claims, evidence_set, decision_log, tool_traces  
  - status, failure_reason  
- 落盘阶段至少会保存两类payload  
  - response_data, 面向调试, 包含 answer, citations, claims, evidence_set带文本, decision_log, tool_traces, status, failure_reason, debug  
  - structured_payload, 面向契约与下游, 包含 report, breaches, evidence_set不带全文, claims, tool_traces, decision_log, status, failure_reason  

```python
response_data = {
    "answer": answer,
    "citations": citations,
    "claims": claims,
    "evidence_set": evidence_set,
    "decision_log": decision_log,
    "tool_traces": tool_traces,
    "status": status,
    "failure_reason": failure_reason,
    "debug": debug_info,
}

structured_payload = {
    "request_id": request_id,
    "report": answer,
    "breaches": breaches,
    "evidence_set": structured_evidence_set,
    "claims": claims,
    "tool_traces": tool_traces,
    "decision_log": decision_log,
    "status": status,
    "failure_reason": failure_reason,
}
```

你更想把Week 9到Week 11写成一条统一的可解释决策链么, 例如先路由再并行检索再融合再打分再门控, 还是你想突出异常信号场景, 例如breach触发后如何强制numeric gate和tool优先策略

## 业界痛点与对照评估

### 业界RAG系统痛点与解法

**业界RAG系统的核心痛点**
- 召回不稳, 同一个问题换种说法就找不到关键证据, 专有名词和缩写尤其明显
- 噪音太多, 检索到的chunk语义相关但事实无关, 反而污染生成
- 长文档难办, chunk切小丢上下文, 切大又模糊且成本高
- 复杂问题难办, 对比, 多跳, 多子任务, 单次query很难覆盖
- 事实对齐难, 有context也会编结论, 引用不精确或证据不支持
- 新鲜度和一致性难, 文档更新后旧向量残留, 增量索引和删除合规复杂
- 延迟和成本高, 多路检索加重排加多轮生成很容易超时或烧钱
- 安全与权限难, 多租户ACL过滤, 提示注入, 数据外泄风险

**常见解决思路 业界怎么做**
- 召回不稳 -> Query理解与多路召回  
  - Query rewrite, query expansion, multi query, step back, decomposition  
  - Hybrid search, BM25加dense向量, RRF或加权融合  
  - HyDE, 用生成的假设问题做匹配, 缓解表述差异
- 噪音太多 -> 两段式排序与过滤  
  - 先粗排过滤, min chunk过滤, 元信息过滤, 去重和配额  
  - 再精排, cross encoder reranking或LLM rerank, 最后做diversity约束
- 长文档难办 -> 结构化索引  
  - Parent child索引, 命中child后回填parent上下文  
  - Summary索引, 专门服务宏观总结与定义类问题  
  - Section级索引与层级导航, 先定位章节再下钻
- 复杂问题难办 -> 智能路由与多策略编排  
  - Semantic router按意图选择策略, 例如 compare走拆分, background走step back  
  - Agentic RAG, retrieve critique revise loop, 自适应决定是否继续检索
- 事实对齐难 -> 可验证生成与门禁  
  - Claim extraction, claim到evidence的绑定, 强制每条结论有证据  
  - Self RAG信号, IsRel IsSup IsUse, 先评docs再评generation  
  - Validator gates, 证据门禁, 数值门禁, 引用粒度门禁, 不过就拒答或回退
- 新鲜度和一致性难 -> 增量索引与生命周期管理  
  - 文档版本化, 增量embedding, 软删除与硬删除, 定期compact  
  - 可追溯元信息, source, section, chunk_id, version, timestamp
- 延迟和成本高 -> 预算化与缓存  
  - TopK预算, rerank budget, early exit, adaptive retrieval  
  - Cache, query cache, embedding cache, rerank cache, 结果缓存  
  - 小模型做路由和粗排, 大模型只在必要时介入
- 安全与权限难 -> 检索前过滤与对抗注入  
  - ACL过滤在检索前做, 只对可见文档建候选集  
  - Prompt injection检测与隔离, 工具调用白名单, 输出审计与脱敏

**你可以用两个问题检验一个RAG方案是否靠谱**
- 它如何保证每条关键结论都能回指到具体证据而不是只给一堆参考链接
- 它如何在延迟预算内处理长文档和对比类复杂问题同时维持可解释性

### 本项目覆盖情况与缺口

能解决一部分而且是很关键的一部分, 但还没有做到业界那种全栈闭环, 我按痛点逐条对照你就很直观了

**已经做得比较扎实的**
- 召回不稳  
  - 有Hybrid search BM25加dense向量  
  - 有RRF融合  
  - 有query aware sparse query和一些元信息boost  
  - 有Week 9的多query variants机制, 包括keywordize, 缩写扩写, step back, 对比类拆分  
- 噪音太多  
  - 有min chunk和信息密度过滤  
  - 有coarse scoring先压缩候选再精排  
  - 有cross encoder reranking  
  - 有diversity rerank做source和section配额, 防止单篇霸榜  
- 长文档难办  
  - 有Parent child回填expanded_text, 能把命中点拉回更大上下文  
  - 有Summary indexing和HyDE indexing, 用parent维度做加权, 覆盖宏观问题和表述差异问题  
- 事实对齐和可验证  
  - 输出里有claims和evidence_set的结构化合同  
  - 有evidence gate强制claim必须绑定evidence_id并且做最小token重叠校验  
  - 有numeric consistency gate, 数字必须能回指tool_traces, 这对金融风控场景很关键  
- 自适应决策  
  - 有retrieve critique revise loop  
  - 有SelfRAG的IsRel IsSup IsUse信号, 而且IsUse会吃检索侧confidence gap, 这是检索到决策的信号闭环  
  - 有Grade docs和Grade generation结果写入decision_log, 便于调试和回归

**目前明显缺口的**
- 新鲜度和一致性  
  - 代码里有增量索引入口, 但没有看到完整的版本化删除策略, 也没有多数据源同步一致性设计  
- 安全和权限  
  - 没有ACL过滤链路, 也没有明确的提示注入防护和数据隔离策略  
- 成本和延迟治理  
  - 目前更多是能力堆叠, 还缺少系统级预算控制, 缓存策略, 超时回退, 分层模型路由  
- 真实生产可观测闭环  
  - 有artifact落盘和decision_log, 但缺少系统化线上指标体系, 报警, A B实验和回归基线自动化闭环

**我的判断**
- 如果你的目标是做一个AgenticRAG作品集, 证明你理解并落地了检索增强, 重排序, 高级索引, 自适应门控, 可验证输出, 这个项目已经能有效覆盖主流痛点里最核心的检索质量和可控性部分
- 如果你的目标是可上线的企业级RAG系统, 还需要把权限安全, 成本延迟, 索引生命周期, 线上观测和灰度评测这几块补齐

给你一个开放问题  
你希望这个项目的下一阶段更像研究型SOTA能力展示, 还是更像生产化工程闭环展示

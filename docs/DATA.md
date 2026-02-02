# DATA 数据字典

这个文件用来描述项目里的关键中间数据结构和用途
目标是让你看到一份数据就能知道它从哪里来 用来做什么 影响什么指标

## Chunk

### 定义

Chunk 是 LangChain 的 Document 对象
它代表被切分后的最小可检索单元

- page_content: string 该 chunk 的文本内容
- metadata: dict 该 chunk 的结构化元数据

### 生成位置

- 语料加载: [source_loader.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/source_loader.py)
- 切分与元数据增强: [ingestion.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/ingestion.py)
- 增量写入向量库: [indexer.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/indexing/indexer.py) 与 [milvus_store.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/indexing/milvus_store.py)

### 主要用途

- 作为 embeddings 的输入 生成向量写入 Milvus
- 作为 BM25 稀疏检索的语料落盘到 sparse_corpus.jsonl
- 作为 citations evidence_set 的来源 支撑可解释性与校验

### chunk_id 的设计

chunk_id 用于稳定定位引用
它由 source start_index page_content 共同生成哈希摘要
实现位置在 [ingestion.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/ingestion.py#L128-L155)

关键影响

- 切分规则或语料内容变动会导致 chunk_id 变化
- 索引采用文件粒度增量更新 未变化文件会跳过 变更文件会重建该文件的 chunk

### 核心字段

下表按产生阶段划分字段

| 字段 | 类型 | 产生阶段 | 用途 |
| --- | --- | --- | --- |
| page_content | string | ingestion | embeddings 输入 生成 contexts 生成回答 |
| source | string | source_loader | 引用定位 文档去重 多样性约束 |
| file_type | string | source_loader | 区分 md 与 pdf 影响切分与定位 |
| page | int | source_loader pdf | pdf 引用定位 |
| section_path | string | ingestion md | 标题路径 用于引用定位 与多样性约束 |
| start_index | int | ingestion | 引用定位 evidence gate 的粒度要求 |
| start_line | int | ingestion md | md 引用定位 |
| end_line | int | ingestion md | md 引用定位 |
| chunk_index | int | ingestion | 调试 排查 |
| chunk_id | string | ingestion | citations evidence_set claim 绑定 |

检索阶段会追加一些排序相关字段

| 字段 | 类型 | 产生阶段 | 用途 |
| --- | --- | --- | --- |
| retrieval_sources | list[string] | retrieval | 标记 dense sparse 来源 便于分析 |
| dense_rank | int | retrieval | debug 与融合分析 |
| sparse_rank | int | retrieval | debug 与融合分析 |
| rrf_score | float | retrieval | 融合排序的主分数 |
| bm25_score | float | retrieval | 稀疏得分归一化 用于 coarse score |
| metadata_boost | float | retrieval | source 与 section 命中时的轻量加权 |
| coarse_score | float | retrieval | 候选压缩阶段的打分 |
| rerank_score | float | retrieval | cross encoder 精排分数 |
| confidence_gap_to_top1 | float | retrieval | 置信差距信号 用于后续自适应检索 |

## Sparse Corpus Row

该数据用于 BM25 稀疏检索
写入位置在 [sparse_index.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/sparse_index.py)

一行一个 JSON 对象

- page_content: string 同 chunk.page_content
- metadata: dict 同 chunk.metadata

文件默认路径是 .milvus/sparse_corpus.jsonl

## Citation

Citation 是 UI 和报告里展示的最小引用结构
它从 docs 的 metadata 提取而来
实现位置在 [pipeline.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/pipeline.py#L73-L110)

结构

- source: string
- chunk_id: string
- start_index: int optional
- section_path: string optional
- page: int optional
- start_line: int optional
- end_line: int optional

## Evidence Set Item

Evidence Set 用于 validator gate 的可执行校验
它由检索返回 docs 构建
实现位置在 [agentic_primitives.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/agentic_primitives.py#L296-L338)

结构

- evidence_id: string ev_0 ev_1
- source: string
- chunk_id: string
- start_index: int
- snippet: string 前 200 字符
- section_path: string optional
- start_line: int optional
- end_line: int optional
- page: int optional
- text: string optional 仅 include_text=true 时存在

## Claim

Claim 是对 answer 的段落级结构化切分
它必须携带 evidence_ids 以便 evidence_gate 可执行
实现位置在 [agentic_primitives.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/rag/agentic_primitives.py#L341-L396)

结构

- claim_id: string cl_0 cl_1
- statement: string
- evidence_ids: list[string] 指向 evidence_id

## Decision Log Entry

Decision Log 用于解释 agentic 决策过程
它是一个 dict 列表 贯穿 rewrite critique revise tool decision
常见字段在 [langgraph_runner.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/orchestration/langgraph_runner.py)

结构

- step_id: string
- agent: string
- rationale: string
- chosen: string
- alternatives: list[string]

## Tool Trace

Tool Trace 用于记录工具调用输入输出
它来自 data_agent 的输出 并被 numeric consistency gate 使用
相关入口在 [langgraph_runner.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/orchestration/langgraph_runner.py)

结构是 dict
字段取决于具体 tool 实现
至少应包含 tool_output 或 output 以便数字回指

## Evaluation Report

评测报告写入 .artifacts/reports
入口在 [evaluation/run.py](file:///Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG/src/riskagent_rag/evaluation/run.py)

核心结构

- inputs: corpus_dir dataset_path retriever_mode reranker_model
- metrics: citations_coverage citation_precision domain_consistency_score 等
- samples: 每条样本的 question answer contexts citations passed

# PROFILING

## 目标

提供一套和业务代码解耦的性能剖析脚本
用于观察索引构建 查询链路的延迟分布
并在可用时统计prompt token数量用于成本估算

## 脚本入口

文件位置

- tools/profiling/profile_e2e.py

运行示例

```bash
conda run -n LangChain python tools/profiling/profile_e2e.py \
  --corpus-dir corpus \
  --dataset tests/data/questions.json \
  --runs 1 \
  --k 4 \
  --out .artifacts/reports/profile_e2e.json
```

输出内容

- index_build: rebuild index耗时
- retrieve_plus_graph: graph.invoke含检索节点耗时
- generate_answer_only: answer生成耗时
- e2e_per_question: 每个问题端到端耗时
- tokens: 如果环境里有tiktoken会输出prompt token估算

## 设计约束

- 不修改业务代码
- 不依赖外部服务即可跑通
- 有LLM时自动走真实生成 无LLM时走deterministic fallback


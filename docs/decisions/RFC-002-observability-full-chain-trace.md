# RFC-002 Observability Full-Chain Trace

## 状态

Proposed

## 目标

为 RiskAgent-AgenticRAG 建立全链路可观测性能力.  
让每一次查询的 `rewrite -> retrieve -> critique -> revise -> synthesize -> validate` 全过程可追踪 可回放 可诊断.

核心问题: 出了一个 bad answer, 能不能一眼看到是检索召回不足还是生成幻觉.

## 背景

当前系统的可观测性几乎空白.

- `debug_stats` 只在 retriever 内部有零散统计, 不跨节点
- `decision_log` 只记录最终决策, 不记录中间状态
- 没有 trace ID 串联一次请求的所有节点
- 没有延迟分位数统计 (p50 / p95 / p99)
- 没有 token 消耗追踪
- 没有实时监控仪表盘
- 没有告警机制

这意味着当 faithfulness 下降或 recall 退化时, 无法快速定位是哪个环节出了问题.  
只能靠手工跑评测 对比报告 逐步排查, 效率极低.

### 业界对标

| 项目 | 能力 | 参考价值 |
|------|------|----------|
| Galileo | chunk 级 attribution 追踪, Context Adherence 反幻觉检测, Luna-2 评估模型 152ms | 评测 + trace 融合 |
| LangSmith | LangChain 原生全链路 trace, prompt 版本管理, 回归测试 | trace + 回归 |
| Langfuse | 开源 trace + prompt 管理 + 评分 API, 自部署 | 开源自部署 |
| Arize Phoenix | OpenTelemetry 原生, embedding 可视化 | OTel 标准兼容 |
| Morgan Stanley AI Assistant | 500 题回归 + 实时监控 + 人工 review 闭环 | 金融生产实践 |

## 提案范围

### P0 必须先做

- `trace ID 贯穿`
  - 每次请求生成唯一 `trace_id`
  - 所有节点 (rewrite / retrieve / critique / revise / synthesize / validate) 共享同一个 `trace_id`
  - 每个节点记录: 开始时间, 结束时间, 输入摘要, 输出摘要, 状态 (ok / error / timeout)
  - 目标: 一次请求的完整链路可以按时间线回放

- `节点级延迟和 token 统计`
  - 每个节点记录 `latency_ms` 和 `token_usage` (prompt_tokens / completion_tokens)
  - 汇总到请求级别的 `total_latency_ms` 和 `total_token_usage`
  - 目标: 能回答 "这次查询慢在哪, token 花在哪"

- `检索诊断埋点`
  - dense search: 返回数, 延迟, top-1 score, top-5 score 分布
  - sparse search: 返回数, 延迟, top-1 score
  - rerank: 输入数, 输出数, 延迟, reranker 模型名
  - MMR diversity: 过滤前数量, 过滤后数量, 被过滤的原因
  - 目标: 能回答 "dense 召回了多少, rerank 过滤了多少, 为什么最终只剩这几条"

### P1 随后做

- `trace 持久化和查询`
  - trace 数据写入本地 JSON 文件 (按 trace_id 命名)
  - 提供 `scripts/trace_inspect.py` 按 trace_id 查询完整链路
  - 目标: 离线也能复盘任意一次请求

- `延迟分位数统计`
  - 按节点维度统计 p50 / p95 / p99
  - 按查询类型 (term / compare / numeric / multi-hop) 分组统计
  - 目标: 发现长尾请求和性能瓶颈节点

- `退化告警`
  - 对比最近 N 次请求的 recall / faithfulness 趋势
  - 退化超过阈值时输出告警 (先做日志告警, 不做 webhook)
  - 目标: 自动发现质量退化, 不依赖人工跑评测

### P2 暂时不做

- 接入外部可观测性平台 (Langfuse / Arize Phoenix / Galileo)
- 实时监控仪表盘 (Grafana / Kibana)
- OpenTelemetry 标准化导出
- 分布式追踪 (跨服务 / 跨 Pod)

## 不在本 RFC 范围内

- 通用 APM (Application Performance Monitoring)
- 日志聚合和分析平台
- 分布式链路追踪标准 (OpenTelemetry / Jaeger / Zipkin)
- 前端可视化仪表盘

## 技术方案

### 数据模型

```python
@dataclass
class NodeTrace:
    """单个节点的 trace 数据."""
    node_name: str               # rewrite / retrieve / critique / revise / synthesize / validate
    start_time: str              # ISO 8601
    end_time: str                # ISO 8601
    latency_ms: float
    status: str                  # ok / error / timeout
    input_summary: dict          # 输入摘要 (避免存全量, 只存关键字段)
    output_summary: dict         # 输出摘要
    token_usage: dict | None     # {prompt_tokens, completion_tokens}
    error_message: str | None    # 仅 status != ok 时有值

@dataclass
class RequestTrace:
    """一次请求的完整 trace."""
    trace_id: str                # UUID
    query: str
    start_time: str
    end_time: str
    total_latency_ms: float
    total_token_usage: dict
    nodes: list[NodeTrace]
    final_status: str            # ok / blocked / error
    final_answer_preview: str    # 截断 200 字符
    retrieval_debug: dict        # 检索诊断埋点汇总
```

### 集成方式

- 在 LangGraph 的每个 node function 入口和出口自动埋点
- 通过 contextvar 传递 `trace_id`, 避免函数签名侵入
- trace 数据在 `validate_and_save` 节点统一持久化
- 不影响主链性能 (异步写入, 超时 100ms 自动跳过)

### 文件组织

```
src/riskagent_agenticrag/observability/
    __init__.py
    trace.py          # NodeTrace / RequestTrace 数据模型
    tracer.py         # 埋点装饰器和 contextvar 管理
    persistence.py    # trace 持久化 (JSON 文件)
    inspect.py        # 离线查询工具

scripts/
    trace_inspect.py  # CLI 查询入口
```

## 预期收益

- 出了 bad answer, 能在 1 分钟内定位是检索还是生成的问题
- 退化告警能自动发现问题, 不依赖人工跑评测
- 延迟分位数统计能发现长尾请求和性能瓶颈
- token 统计能支撑成本优化决策

## 预期风险

- 埋点过多可能影响主链性能 (需控制摘要大小和异步写入)
- trace 文件可能占用较多磁盘 (需设置保留策略, 默认 7 天)
- contextvar 在异步场景下可能有传递问题 (需测试验证)

## 成功标志

- 任意一次请求都能通过 `trace_id` 查到完整链路
- 每个节点的延迟和 token 消耗都有记录
- 检索诊断能回答 "dense 召回了多少, rerank 过滤了多少"
- 退化告警能在 10 次请求内发现 recall 或 faithfulness 退化

## 关联文档

- [ARCHITECTURE.md](../ARCHITECTURE.md) - 系统 Query 流程
- [RFC-001-retrieval-hardening-roadmap.md](./RFC-001-retrieval-hardening-roadmap.md) - retrieval observability 已在本 RFC 中覆盖
- [phase-3-evaluation-hardening.md](../phases/phase-3-evaluation-hardening.md) - 评测体系

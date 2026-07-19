# Debug Session: report-hang

Status: OPEN
Started: 2026-07-18

## Problem

`full baseline` 多次在 report 生成前后卡住, 导致需要重跑, 目前需要基于运行时证据确认真正阻塞点。

## Scope

- 只做调试和插桩
- 在拿到运行时证据前不改业务逻辑
- 优先定位 report 收尾阶段的阻塞点

## Initial Hypotheses

1. HTTPS 远端调用在 report 收尾阶段未正确超时或未释放连接, 导致主线程等待。
2. `citation_precision` 或 `answer_eval` 等后处理阶段存在单样本阻塞, 但没有输出到日志。
3. report 写盘前的 markdown 生成或 baseline diff 比较阶段读取了异常大的 payload, 导致长时间卡住。
4. 外层 `conda run | tee` 管道状态和 Python 子进程状态脱节, 实际评测已结束但壳进程未退出。
5. 某个 artifact 或 trace 文件句柄未关闭, 导致 report 写盘等待文件系统状态或锁释放。

## Evidence Log

- 已验证 `write_report` 和 `generate_markdown_report` 本地执行极快.
  - `json_s ~= 0.012`
  - `md_s ~= 0.001`
- focused probe 使用已有 50 题 report 的前 5 个样本重放 `citation_precision(mode="llm")`.
  - 总耗时 `172.47s`
  - `q01 ~= 59.8s`
  - `q02 ~= 14.6s`
  - `q03 ~= 0.9s`
  - `q04 ~= 36.9s`
  - `q05 ~= 56.6s`
- Debug log 证明卡点发生在 `judge_llm.invoke()` 前后, 而不是 report 写盘函数.
- focused probe 在 summary 输出后正常退出, 暂未复现 `tee` 或壳进程无法退出的问题.
- 已完成 fix 后 probe.
  - 增加 `LLM judge` 有界并行
  - 增加 heartbeat 与 completed progress 输出
  - 5 题 probe 从 `172.47s` 降到 `98.97s`
  - 运行中可持续看到 `heartbeat completed=x/y running=z`

## Hypothesis Status

1. HTTPS 远端调用未正确超时或未释放连接, 导致主线程等待.
   - 部分确认.
   - 已确认远端 Judge 调用存在显著长尾.
   - 尚未拿到“连接未释放”的直接证据.
2. `citation_precision` 或 `answer_eval` 等后处理阶段存在单样本阻塞.
   - 确认.
   - 阻塞点落在 `citation_precision -> judge_llm.invoke()`.
3. report 写盘前的 markdown 生成或 baseline diff 比较阶段读取了异常大的 payload.
   - 否定.
   - 本地重放写盘和 markdown 生成耗时毫秒级.
4. 外层 `conda run | tee` 管道状态和 Python 子进程状态脱节.
   - 当前证据不足.
   - focused probe 正常退出.
5. 某个 artifact 或 trace 文件句柄未关闭, 导致 report 写盘等待文件系统状态或锁释放.
   - 否定.
   - 本地写盘重放正常且极快.

## Fix Applied

1. `citation_precision` 从完全串行改为有界并行执行.
2. 保留 `LLM judge` 优先策略, 只在真实异常时才走 heuristic fallback.
3. 增加 heartbeat 和 per-sample completed progress, 便于区分正常慢和异常卡死.
4. `run_fresh_eval_with_current_env.py` 默认开启上述 progress 和保守并发配置.

## Next Step

- 用完整 `full baseline` 复验修复效果
- 根据真实吞吐再决定 `max_concurrency` 是否从 `4` 调到更高

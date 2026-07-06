# Phase 4 Release Readiness

## 目标

把环境 依赖 回归 发布验收这些工程项做稳定.

## 本阶段重点

- 锁定关键依赖
- 固定 conda 和 Makefile 入口
- 稳定离线回归和最小发布验收命令
- 收口 README PRD ARCHITECTURE 和报告引用

## 当前已落地

- 仓库已经固定了 `Makefile` `scripts/run_offline_regression.sh` `scripts/release_acceptance.sh` 这条最小发布链
- 本地 `docker-compose` 已定义 `Milvus` 和 `Redis` 两个依赖 并且仓库中存在历史数据卷快照
- 默认 conda 环境口径已经收口到 `agenticrag`

## 当前仍未完成

- GitHub CI 还没有和当前 pytest 测试树及 release gate 完全对齐
- release acceptance 当前会读取仓库内样例报告 还不是基于 fresh eval 产物的严格发布门禁
- 最近一次仓库审计时 Docker daemon 未连通 因此只能确认本地数据卷存在 不能确认容器正在运行

## 建议交付

- 一套稳定的环境口径
- 一条最小发布验收命令
- 可复核的样例报告和基线

## 验收标准

- 新环境能稳定跑核心测试
- 最小发布验收命令可用
- 对外文档和工程入口不再漂移

## 状态

In Progress

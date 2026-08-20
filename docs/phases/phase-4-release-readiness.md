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
- GitHub CI 已经和当前真实门禁链对齐 直接执行 `offline regression + release acceptance`
- 本地 `docker-compose` 已定义 `Milvus` 和 `Redis` 两个依赖 并且当前审计时已验证容器可 healthy 启动
- 默认 conda 环境口径已经收口到 `agenticrag`
- 发布门禁已经支持 `有 LLM key 跑 fresh eval 无 LLM key 回退 sample smoke`
- 已经验证 `RiskMonitor-MultiAgent` 的外部 `LLM` 配置能够打通当前统一主链 并生成 `5` 题 smoke 报告
- k8s 部署链路已落地 (`deploy/k8s/` + `Dockerfile`), 镜像已迭代到 `v10c-fix`, secret 以 template 形式管理不入库
- 2026-08-18 `v10b` 报告实现 threshold gate 首次全绿 PASS (此前 `2026-07-18` baseline 的 `retrieval_recall_at_5=0.500 < 0.6` 瓶颈已解决, 现 `0.78`)
- 2026-08-20 `v10c` FAIL 子集复跑 `3/3` 全 PASS, v10b 遗留的 3 个 FAIL 已闭环 (详见 [评测台账](../evaluations/EVALUATION_LOG.md))

## 当前仍未完成

- v10c 后的 `50` 题全量复评尚未执行 (预期 `50/50`), 需产出正式全量报告
- release acceptance 尚未用 `v10b`/`v10c` 最新结果重新执行
- release acceptance 在无 `LLM key` 环境下仍会回退到仓库内样例报告

## 建议交付

- 一套稳定的环境口径
- 一条最小发布验收命令
- 可复核的样例报告和基线

## 验收标准

- 新环境能稳定跑核心测试
- 最小发布验收命令可用
- 对外文档和工程入口不再漂移

## 状态

In Progress (2026-08-20 更新: gate 已全绿, 剩余全量复评 + release acceptance 重跑两项收尾)

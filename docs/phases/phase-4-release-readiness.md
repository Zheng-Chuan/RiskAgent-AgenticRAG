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
- 发布门禁要求 `LLM key` 跑 fresh eval, 无 key 直接报错终止 (2026-08-21 起样例回退已移除)
- 已经验证 `RiskMonitor-MultiAgent` 的外部 `LLM` 配置能够打通当前统一主链 并生成 `5` 题 smoke 报告
- k8s 部署链路已落地 (`deploy/k8s/` + `Dockerfile`), 镜像已迭代到 `v10d-fix`, secret 以 template 形式管理不入库
- 2026-08-18 `v10b` 报告实现 threshold gate 首次全绿 PASS (此前 `2026-07-18` baseline 的 `retrieval_recall_at_5=0.500 < 0.6` 瓶颈已解决, 现 `0.78`)
- 2026-08-20 `v10c` FAIL 子集复跑 `3/3` 全 PASS, v10b 遗留的 3 个 FAIL 已闭环 (详见 [评测台账](../evaluations/EVALUATION_LOG.md))
- 2026-08-21 `v10d` 全量复评 `50/50` PASS (recall@5 0.82 / citation 1.000 / gate 全绿), release acceptance 已用 v10d 报告重跑通过, 发布闭环
- 2026-08-21 release acceptance 移除样例报告回退: 无 `LLM key` 直接报错终止, 强制 fresh eval 口径

## 当前仍未完成

- (无)

## 建议交付

- 一套稳定的环境口径
- 一条最小发布验收命令
- 可复核的样例报告和基线

## 验收标准

- 新环境能稳定跑核心测试
- 最小发布验收命令可用
- 对外文档和工程入口不再漂移

## 状态

Completed (2026-08-21 更新: v10d 全量 50/50 + release acceptance 重跑通过 + 无 key 回退移除, 发布闭环)

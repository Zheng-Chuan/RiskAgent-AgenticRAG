# DOCS

本文档是 `docs/` 的统一导航页，按用途分层阅读。

## 01 上手与定位

- [OVERVIEW.md](./OVERVIEW.md): 一页读懂系统目标、边界和主链路
- [QUICKSTART.md](./QUICKSTART.md): 本地跑通 UI、CLI、API 的最短路径

## 02 架构与接口

- [ARCHITECTURE.md](./ARCHITECTURE.md): 模块边界、数据流、关键设计
- [API.md](./API.md): HTTP API 契约、调用方式、健康检查

## 03 评测与验收

- [EVALUATION.md](./EVALUATION.md): 指标含义、实验方案、历史数据、门禁策略
- [TRACE.md](./TRACE.md): trace 字段与排障路径
- [eval_thresholds.yaml](./eval_thresholds.yaml): 阈值门禁配置

## 04 数据与演进

- [DATA.md](./DATA.md): 核心数据结构与字段约定
- [ROADMAP.md](./ROADMAP.md): 里程碑、交付项、验收状态
- [INTERVIEW.md](./INTERVIEW.md): 面试速答卡与高频追问

## 文档维护约定

- 评测相关定义和方案仅在 `EVALUATION.md` 维护
- 新增文档前优先补充到现有文档章节，避免平行文档漂移
- `README.md` 只保留入口索引，不承载细节说明

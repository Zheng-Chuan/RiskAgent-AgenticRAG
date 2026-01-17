# RENAME

## 目标

把本地仓库目录名从 RiskAgent-MultiAgent 改为 RiskAgent-AgenticRAG

## 为什么需要手动执行

当前开发环境对目录操作有白名单限制
因此无法在这里直接把上级目录重命名

## 手动改名命令

在仓库上级目录执行

```bash
mv RiskAgent-MultiAgent RiskAgent-AgenticRAG
```

## 改名后验证清单

- 运行单测
  - conda run -n LangChain python -m unittest discover tests
- 启动docker compose
  - docker compose -f deploy/dev/docker-compose.yml up -d
  - 期望容器名 riskagent-agenticrag-milvus
- 启动UI
  - conda run -n LangChain python gradio_app.py
  - 页面标题 RiskAgent-AgenticRAG


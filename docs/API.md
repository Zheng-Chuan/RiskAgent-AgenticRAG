# API

## 启动服务

```bash
conda run -n LangChain python -m riskagent_rag.api.server
```

环境变量

- RISKAGENT_API_HOST 默认 0.0.0.0
- RISKAGENT_API_PORT 默认 8000
- RISKAGENT_API_KEY 可选 启用后必须传 X-API-Key 或 Authorization: Bearer
- RISKAGENT_CORPUS_DIR 可选 覆盖语料目录
- RISKAGENT_PERSIST_DIR 可选 覆盖索引目录
- RISKAGENT_ARTIFACTS_DIR 可选 覆盖落盘目录
- RISKAGENT_TRACE_SNIPPET_CHARS 可选 trace 原文片段长度 默认 240

## 健康检查

- GET /healthz
- GET /readyz
- GET /metrics

## v1 ask

POST /v1/ask

请求

```json
{
  "question": "what is frtb",
  "request_id": "optional",
  "max_rounds": 2
}
```

响应字段固定

- request_id
- status ok failed error
- answer
- citations
- claims
- evidence_set
- decision_log
- tool_traces
- failure_reason
- debug
- error

每次请求会落盘到 artifacts bundle 目录
bundle 目录里包含 request response structured_response trace

## v1 chat

POST /v1/chat

请求

```json
{
  "messages": [
    { "role": "user", "content": "what is frtb" },
    { "role": "assistant", "content": "ok" },
    { "role": "user", "content": "how is it related to basel" }
  ],
  "request_id": "optional",
  "max_rounds": 2
}
```

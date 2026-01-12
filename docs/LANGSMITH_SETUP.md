# LangSmith 追踪配置指南

LangSmith 是 LangChain 的官方追踪和可视化平台,可以实时查看 LangGraph 的执行过程.

## 功能特性

- ✅ **实时追踪**: 查看每个 node 的执行过程
- ✅ **State 可视化**: 查看 state 在每个 node 的变化
- ✅ **性能分析**: 分析每个 node 的执行时间和性能瓶颈
- ✅ **调试工具**: 调试 conditional edges 的决策逻辑
- ✅ **执行历史**: 查看完整的执行历史和对比
- ✅ **错误追踪**: 快速定位错误发生的位置

## 配置步骤

### 1. 注册 LangSmith 账号

访问 [https://smith.langchain.com/](https://smith.langchain.com/) 注册账号 (免费).

### 2. 获取 API Key

1. 登录 LangSmith
2. 点击右上角头像 → Settings
3. 在 API Keys 页面创建新的 API key
4. 复制 API key (只显示一次,请妥善保存)

### 3. 配置环境变量

在启动 Gradio 之前,设置以下环境变量:

```bash
# 启用 LangSmith 追踪
export LANGCHAIN_TRACING_V2=true

# 设置 API key
export LANGCHAIN_API_KEY=your-api-key-here

# 可选: 设置项目名称 (默认: RiskAgent-RAG)
export LANGCHAIN_PROJECT=RiskAgent-RAG

# 可选: 设置 endpoint (默认: https://api.smith.langchain.com)
export LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

### 4. 启动 Gradio

```bash
# 完整启动命令 (包含所有配置)
env LLM_PROVIDER=ollama \
    OLLAMA_MODEL=qwen3:8b \
    OLLAMA_BASE_URL=http://localhost:11434 \
    USE_LANGGRAPH=true \
    LANGCHAIN_TRACING_V2=true \
    LANGCHAIN_API_KEY=your-api-key-here \
    GRADIO_SERVER_NAME=127.0.0.1 \
    GRADIO_SERVER_PORT=7860 \
    conda run -n LangChain python gradio_app.py
```

## 使用方式

### 在 Gradio UI 中查看状态

启动 Gradio 后:

1. 在左侧 **Runtime** 面板查看 LangSmith 状态
2. 如果配置成功,会显示:
   - `langsmith=enabled`
   - `project=RiskAgent-RAG`
   - `追踪: https://smith.langchain.com/`

### 在 LangSmith 平台查看追踪

1. 访问 [https://smith.langchain.com/](https://smith.langchain.com/)
2. 选择项目 `RiskAgent-RAG`
3. 查看实时追踪:
   - **Traces**: 查看每次执行的完整追踪
   - **Timeline**: 查看执行时间线
   - **Inputs/Outputs**: 查看每个 node 的输入输出
   - **Metadata**: 查看 state 变化和决策信息

### 在 Gradio UI 中查看 Graph 结构

1. 在右侧聊天区域下方打开 **Inspector**
2. 切换到 **Graph** Tab
3. 查看 LangGraph 的 Mermaid 流程图
4. 复制 Mermaid 代码到 [Mermaid Live Editor](https://mermaid.live/) 查看交互式图表

## 追踪内容

LangSmith 会追踪以下内容:

### 1. Node 执行

- `rewrite`: 查询改写
- `retrieve_and_critique`: 检索与评估
- `revise_query`: 修订查询
- `decide_tool_use`: 决策工具调用
- `call_tool`: 调用工具
- `synthesize_answer`: 合成答案
- `validate_and_save`: 验证与落盘

### 2. Conditional Edges

- `should_continue_retrieval`: 是否继续检索
- `should_call_tool`: 是否调用工具

### 3. State 变化

- `question`: 用户问题
- `current_query`: 当前查询
- `docs`: 检索到的文档
- `critique_reason`: 评估原因
- `tool_output`: 工具输出
- `answer`: 最终答案
- `decision_log`: 决策日志

## 常见问题

### Q: 如何禁用 LangSmith 追踪?

A: 不设置 `LANGCHAIN_TRACING_V2` 环境变量,或设置为 `false`:

```bash
export LANGCHAIN_TRACING_V2=false
```

### Q: 追踪会影响性能吗?

A: 会有轻微影响 (通常 < 100ms),但对于开发和调试来说非常值得.

### Q: 可以在生产环境使用吗?

A: 可以,但建议:
- 使用采样追踪 (只追踪部分请求)
- 设置合适的数据保留策略
- 注意敏感数据的处理

### Q: 如何查看历史追踪?

A: 在 LangSmith 平台的 Traces 页面,可以:
- 按时间筛选
- 按状态筛选 (成功/失败)
- 按执行时间排序
- 搜索特定的 trace

### Q: 可以对比不同的执行吗?

A: 可以,在 LangSmith 平台:
1. 选择多个 traces
2. 点击 "Compare" 按钮
3. 查看并排对比

## 最佳实践

1. **开发阶段**: 始终启用 LangSmith,便于调试和优化
2. **测试阶段**: 使用 LangSmith 进行性能基准测试
3. **生产阶段**: 使用采样追踪,监控关键指标
4. **问题排查**: 使用 LangSmith 快速定位问题

## 相关链接

- [LangSmith 官方文档](https://docs.smith.langchain.com/)
- [LangSmith Python SDK](https://github.com/langchain-ai/langsmith-sdk)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [Mermaid Live Editor](https://mermaid.live/)

## 技术支持

如果遇到问题:

1. 检查环境变量是否正确设置
2. 检查 API key 是否有效
3. 查看 Gradio 启动日志中的 LangSmith 状态
4. 访问 LangSmith 文档查看详细说明

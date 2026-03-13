# 中文注释: LangSmith 配置模块
# 用途: 配置 LangSmith 追踪功能, 实时可视化 LangGraph 执行过程

import os
from typing import Optional


def setup_langsmith(
    project_name: str = "RiskAgent-RAG",
    enabled: Optional[bool] = None,
) -> bool:
    """
    配置 LangSmith 追踪.
    
    参数:
        project_name: LangSmith 项目名称
        enabled: 是否启用, None 则根据环境变量决定
    
    返回:
        是否成功启用 LangSmith
    
    环境变量:
        - LANGCHAIN_TRACING_V2=true: 启用追踪
        - LANGCHAIN_API_KEY: LangSmith API key
        - LANGCHAIN_PROJECT: 项目名称 (可选)
        - LANGCHAIN_ENDPOINT: API endpoint (可选, 默认 https://api.smith.langchain.com)
    
    使用方式:
        1. 在 https://smith.langchain.com/ 注册账号
        2. 获取 API key
        3. 设置环境变量:
           export LANGCHAIN_TRACING_V2=true
           export LANGCHAIN_API_KEY=your-api-key
        4. 运行程序, 在 LangSmith 平台查看追踪
    
    功能:
        - 实时追踪每个 node 的执行
        - 查看 state 变化
        - 分析性能瓶颈
        - 调试 conditional edges
        - 查看完整的执行历史
    """
    if enabled is None:
        enabled = os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1", "yes")
    
    if not enabled:
        return False
    
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("⚠️  LANGCHAIN_TRACING_V2=true 但未设置 LANGCHAIN_API_KEY")
        print("   请在 https://smith.langchain.com/ 获取 API key")
        return False
    
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    
    if project_name:
        os.environ["LANGCHAIN_PROJECT"] = project_name
    
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    os.environ["LANGCHAIN_ENDPOINT"] = endpoint
    
    print("✅ LangSmith 追踪已启用")
    print(f"   项目: {project_name}")
    print("   查看追踪: https://smith.langchain.com/")
    
    return True


def get_langsmith_status() -> dict[str, str]:
    """
    获取 LangSmith 配置状态.
    
    返回:
        配置状态字典
    """
    enabled = os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1", "yes")
    api_key = os.getenv("LANGCHAIN_API_KEY", "")
    project = os.getenv("LANGCHAIN_PROJECT", "")
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    
    return {
        "enabled": "true" if enabled else "false",
        "api_key_set": "true" if api_key else "false",
        "project": project or "default",
        "endpoint": endpoint,
        "url": "https://smith.langchain.com/" if enabled and api_key else "",
    }

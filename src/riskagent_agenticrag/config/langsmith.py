"""LangSmith 追踪配置 -- 可视化 LangGraph 执行过程."""

from __future__ import annotations

import os


def setup_langsmith(
    project_name: str = "RiskAgent-RAG",
    enabled: bool | None = None,
) -> bool:
    """配置并启用 LangSmith 追踪.

    Args:
        project_name: LangSmith 项目名称.
        enabled: 是否启用; None 时根据 LANGCHAIN_TRACING_V2 环境变量决定.

    Returns:
        是否成功启用.
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
    """返回当前 LangSmith 配置状态字典."""
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

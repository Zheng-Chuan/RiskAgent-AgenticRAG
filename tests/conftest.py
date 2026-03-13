"""pytest conftest -- 全局 fixture 与路径/警告配置."""

from __future__ import annotations

import os
import pathlib
import sys
import warnings

from dotenv import load_dotenv

# ---- 项目路径 & 环境变量 ----
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_env_path = _PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# ---- 全局抑制第三方库弃用警告 ----
try:
    from langchain_core._api.deprecation import LangChainDeprecationWarning
    warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
except ImportError:
    pass
warnings.filterwarnings("ignore", message=".*pydantic_v1.*")
warnings.filterwarnings("ignore", message=".*class-validator.*")
warnings.filterwarnings("ignore", message=".*pkg_resources.*")
warnings.filterwarnings("ignore", message=".*created with version.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*ARC4 has been moved.*")


def ensure_src_on_path() -> None:
    """兼容旧测试文件中的显式调用, 实际路径已在模块级别设置."""

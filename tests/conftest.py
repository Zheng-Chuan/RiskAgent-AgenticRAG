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
warnings.filterwarnings("ignore", message=".*allowed_objects.*")
warnings.filterwarnings("ignore", message=".*pydantic_v1.*")
warnings.filterwarnings("ignore", message=".*class-validator.*")
warnings.filterwarnings("ignore", message=".*pkg_resources.*")
warnings.filterwarnings("ignore", message=".*created with version.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*ARC4 has been moved.*")


def ensure_src_on_path() -> None:
    """兼容旧测试文件中的显式调用, 实际路径已在模块级别设置."""


import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def llm_mock():
    """Standardized LLM mock that patches both call_llm_text and call_llm_json."""
    def _fake_llm_json(prompt, temperature=0.0, **kwargs):
        p = str(prompt or "")
        if "\"query\"" in p:
            return {"query": "rewritten test query"}
        if "\"sufficient\"" in p:
            return {"sufficient": True, "improved_query": "", "reason": "ok"}
        if "\"should_call_tool\"" in p:
            return {"should_call_tool": False, "args": {}, "reason": "N/A"}
        if "\"isrel\"" in p:
            return {"isrel": 0.8}
        return {}

    def _fake_llm_text(prompt, temperature=0.0, **kwargs):
        return "This is a mock LLM response for testing purposes."

    with patch("riskagent_agenticrag.llm.generate.call_llm_text", side_effect=_fake_llm_text) as mock_text, \
         patch("riskagent_agenticrag.llm.generate.call_llm_json", side_effect=_fake_llm_json) as mock_json, \
         patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_text", side_effect=_fake_llm_text), \
         patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", side_effect=_fake_llm_json):
        yield {"text": mock_text, "json": mock_json}


@pytest.fixture
def temp_corpus(tmp_path):
    """Create a temporary corpus directory with a sample document."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    # Copy test corpus file
    project_root = Path(__file__).resolve().parent.parent
    src_file = project_root / "corpus" / "Background.md"
    if src_file.exists():
        shutil.copy(src_file, corpus_dir / "Background.md")
    else:
        (corpus_dir / "test_doc.md").write_text(
            "# FRTB Overview\n\nThe Fundamental Review of the Trading Book (FRTB) "
            "is a set of proposals by the Basel Committee on Banking Supervision.\n"
        )
    return corpus_dir


@pytest.fixture
def settings_override():
    """Override settings for testing (use hash embeddings, disable auth)."""
    overrides = {
        "EMBEDDINGS_PROVIDER": "hash",
        "RISKAGENT_API_AUTH_ENABLED": "false",
        "LLM_GOVERNANCE_RATE_LIMIT_TOKENS_PER_MIN": "60000",
        "LLM_GOVERNANCE_CACHE_ENABLED": "true",
    }
    with patch.dict(os.environ, overrides):
        yield overrides


@pytest.fixture
def test_client(settings_override):
    """FastAPI TestClient with auth disabled."""
    from fastapi.testclient import TestClient
    from riskagent_agenticrag.api.server import app, settings as server_settings

    # settings 是模块级别单例，环境变量在实例化后不再生效，需要直接 mock
    original_enabled = server_settings.api_auth.enabled
    object.__setattr__(server_settings.api_auth, 'enabled', False)
    try:
        yield TestClient(app)
    finally:
        object.__setattr__(server_settings.api_auth, 'enabled', original_enabled)

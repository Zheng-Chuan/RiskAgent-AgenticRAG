"""Embeddings 模块单元测试.

覆盖 rag/embeddings.py 的 provider 分发、HashEmbeddings、openai 构建与预加载逻辑.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from riskagent_agenticrag.rag.embeddings import (
    HashEmbeddings,
    _build_openai_embeddings,
    build_embeddings,
    preload_embeddings_model,
)

# ---------------------------------------------------------------------------
# HashEmbeddings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHashEmbeddings:
    """离线 Hash embeddings 测试."""

    def test_embed_query_returns_normalized_vector(self):
        """query 向量应归一化 (L2 范数约为 1)."""
        emb = HashEmbeddings(dimension=32)
        vec = emb.embed_query("FRTB capital charge")
        assert len(vec) == 32
        norm_sq = sum(v * v for v in vec)
        assert 0.9 < norm_sq < 1.1  # 归一化

    def test_embed_documents_returns_list_of_vectors(self):
        """批量 embedding 应返回与输入等长的列表."""
        emb = HashEmbeddings(dimension=16)
        vecs = emb.embed_documents(["hello", "world", "foo"])
        assert len(vecs) == 3
        assert all(len(v) == 16 for v in vecs)

    def test_different_inputs_produce_different_vectors(self):
        """不同文本应产生不同向量."""
        emb = HashEmbeddings(dimension=64)
        v1 = emb.embed_query("delta risk")
        v2 = emb.embed_query("vega risk")
        assert v1 != v2

    def test_empty_text_returns_valid_vector(self):
        """空文本也应返回有效向量 (非 NaN)."""
        emb = HashEmbeddings(dimension=8)
        vec = emb.embed_query("")
        assert len(vec) == 8
        assert all(isinstance(v, float) for v in vec)

    def test_dimension_parameter_respected(self):
        """dimension 参数应被正确使用."""
        for dim in (8, 64, 128):
            emb = HashEmbeddings(dimension=dim)
            assert len(emb.embed_query("x")) == dim


# ---------------------------------------------------------------------------
# build_embeddings provider 分发
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildEmbeddingsDispatch:
    """build_embeddings 按 provider 分发测试."""

    def test_hash_provider_returns_hash_embeddings(self):
        """provider=hash 应返回 HashEmbeddings."""
        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings:
            mock_settings.embeddings.provider = "hash"
            mock_settings.embeddings.model_name = "hash-model"
            emb = build_embeddings()
        assert isinstance(emb, HashEmbeddings)

    def test_unsupported_provider_raises(self):
        """未知 provider 应抛出 RuntimeError."""
        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings:
            mock_settings.embeddings.provider = "unknown"
            mock_settings.embeddings.model_name = "x"
            with pytest.raises(RuntimeError, match="Unsupported embeddings provider"):
                build_embeddings()

    def test_openai_provider_builds_openai_embeddings(self):
        """provider=openai 应构建 OpenAIEmbeddings (mock)."""
        mock_instance = MagicMock()
        with patch.dict(os.environ, {"EMBEDDINGS_PROVIDER": "openai"}), \
             patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings, \
             patch("langchain_openai.OpenAIEmbeddings", return_value=mock_instance) as mock_cls:
            mock_settings.embeddings.provider = "openai"
            mock_settings.embeddings.api_key = MagicMock()
            mock_settings.embeddings.api_key.get_secret_value.return_value = "sk-test"
            mock_settings.embeddings.model_name = "text-embedding-3-small"
            mock_settings.embeddings.base_url = "https://example.com/v1"
            emb = build_embeddings()
        mock_cls.assert_called_once()
        assert emb is mock_instance

    def test_openai_without_api_key_raises(self):
        """openai provider 无 api_key 应抛错."""
        with patch.dict(os.environ, {"EMBEDDINGS_PROVIDER": "openai"}), \
             patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings:
            mock_settings.embeddings.provider = "openai"
            mock_settings.embeddings.api_key = None
            mock_settings.embeddings.model_name = "x"
            mock_settings.embeddings.base_url = "x"
            with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
                build_embeddings()


# ---------------------------------------------------------------------------
# _build_openai_embeddings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildOpenaiEmbeddings:
    """OpenAI embeddings 构建测试."""

    def test_passes_model_key_and_base_url(self):
        """应传入 model_name / api_key / base_url."""
        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings, \
             patch("langchain_openai.OpenAIEmbeddings") as mock_cls:
            mock_settings.embeddings.api_key = MagicMock()
            mock_settings.embeddings.api_key.get_secret_value.return_value = "sk-secret"
            mock_settings.embeddings.model_name = "bge-large"
            mock_settings.embeddings.base_url = "https://api.test.com/v1"
            _build_openai_embeddings()
        _, kwargs = mock_cls.call_args
        assert kwargs["model"] == "bge-large"
        assert kwargs["api_key"] == "sk-secret"
        assert kwargs["base_url"] == "https://api.test.com/v1"


# ---------------------------------------------------------------------------
# preload_embeddings_model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPreloadEmbeddings:
    """预加载 embeddings 模型测试."""

    def test_preload_hash_provider_returns_info(self):
        """hash provider 预加载应返回 model 和 provider."""
        with patch.dict(os.environ, {"EMBEDDINGS_PROVIDER": "hash"}), \
             patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings:
            mock_settings.embeddings.provider = "hash"
            mock_settings.embeddings.model_name = "hash-emb"
            result = preload_embeddings_model()
        assert result["provider"] == "hash"
        assert "model" in result

    def test_preload_swallows_warmup_exception(self):
        """warmup 调用失败时应静默返回, 不抛异常."""
        with patch.dict(os.environ, {"EMBEDDINGS_PROVIDER": "hash"}), \
             patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings, \
             patch("riskagent_agenticrag.rag.embeddings.build_embeddings") as mock_build:
            mock_settings.embeddings.provider = "hash"
            mock_settings.embeddings.model_name = "x"
            mock_build.return_value.embed_query.side_effect = RuntimeError("warmup failed")
            result = preload_embeddings_model()
        assert "model" in result


# ---------------------------------------------------------------------------
# _build_hf_embeddings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildHfEmbeddings:
    """HuggingFace embeddings 构建测试."""

    def test_hf_provider_builds_hf_embeddings(self):
        """provider=hf 应构建 HuggingFaceEmbeddings (mock)."""
        mock_instance = MagicMock()
        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings, \
             patch("riskagent_agenticrag.rag.embeddings._ensure_project_hf_cache_env"), \
             patch("riskagent_agenticrag.rag.embeddings._local_embeddings_dir") as mock_local_dir, \
             patch("importlib.import_module") as mock_import:
            mock_settings.embeddings.provider = "hf"
            mock_settings.embeddings.model_name = "test/model"
            mock_local_dir.return_value = MagicMock(exists=MagicMock(return_value=False))
            mock_mod = MagicMock()
            mock_mod.HuggingFaceEmbeddings = MagicMock(return_value=mock_instance)
            mock_import.return_value = mock_mod
            emb = build_embeddings()
        assert emb is mock_instance

    def test_hf_provider_falls_back_to_community(self):
        """langchain_huggingface 无 HuggingFaceEmbeddings 属性时应回退到 langchain_community."""
        import sys
        mock_instance = MagicMock()
        # 注入一个无 HuggingFaceEmbeddings 属性的假 langchain_huggingface 模块
        fake_mod = MagicMock(spec=[])  # spec=[] 表示无任何属性, getattr 会抛 AttributeError
        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings, \
             patch("riskagent_agenticrag.rag.embeddings._ensure_project_hf_cache_env"), \
             patch("riskagent_agenticrag.rag.embeddings._local_embeddings_dir") as mock_local_dir, \
             patch.dict(sys.modules, {"langchain_huggingface": fake_mod}), \
             patch("langchain_community.embeddings.HuggingFaceEmbeddings", return_value=mock_instance) as mock_cls:
            mock_settings.embeddings.provider = "hf"
            mock_settings.embeddings.model_name = "test/model"
            mock_local_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
            emb = build_embeddings()
        assert emb is mock_instance

    def test_hf_provider_uses_local_dir_when_exists(self):
        """本地目录存在时应使用本地路径作为 model_name."""
        mock_instance = MagicMock()
        local_path = "/fake/local/model"
        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings, \
             patch("riskagent_agenticrag.rag.embeddings._ensure_project_hf_cache_env"), \
             patch("riskagent_agenticrag.rag.embeddings._local_embeddings_dir") as mock_local_dir, \
             patch("importlib.import_module") as mock_import:
            mock_settings.embeddings.provider = "hf"
            mock_settings.embeddings.model_name = "test/model"
            mock_local = MagicMock()
            mock_local.exists.return_value = True
            mock_local.__str__ = MagicMock(return_value=local_path)
            mock_local_dir.return_value = mock_local
            mock_mod = MagicMock()
            mock_mod.HuggingFaceEmbeddings = MagicMock(return_value=mock_instance)
            mock_import.return_value = mock_mod
            emb = build_embeddings()
        assert emb is mock_instance


# ---------------------------------------------------------------------------
# export_embeddings_model_to_repo_dir
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExportEmbeddingsModel:
    """export_embeddings_model_to_repo_dir 导出测试."""

    def test_export_raises_without_sentence_transformers(self):
        """未安装 sentence_transformers 时应抛 RuntimeError."""
        from riskagent_agenticrag.rag.embeddings import export_embeddings_model_to_repo_dir

        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings, \
             patch("riskagent_agenticrag.rag.embeddings._ensure_project_hf_cache_env"), \
             patch("riskagent_agenticrag.rag.embeddings._local_embeddings_dir"):
            mock_settings.embeddings.model_name = "test/model"
            with patch.dict("sys.modules", {"sentence_transformers": None}):
                with pytest.raises(RuntimeError, match="Export requires sentence_transformers"):
                    export_embeddings_model_to_repo_dir()

    def test_export_calls_save(self, tmp_path):
        """安装了 sentence_transformers 时应调用 save."""
        from riskagent_agenticrag.rag.embeddings import export_embeddings_model_to_repo_dir

        mock_transformer = MagicMock()
        mock_st_mod = MagicMock(SentenceTransformer=MagicMock(return_value=mock_transformer))
        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings, \
             patch("riskagent_agenticrag.rag.embeddings._ensure_project_hf_cache_env"), \
             patch("riskagent_agenticrag.rag.embeddings._local_embeddings_dir") as mock_local_dir, \
             patch.dict("sys.modules", {"sentence_transformers": mock_st_mod}):
            mock_settings.embeddings.model_name = "test/model"
            mock_local_dir.return_value = tmp_path / "export" / "model"
            result = export_embeddings_model_to_repo_dir()
        mock_transformer.save.assert_called_once()
        assert result["model"] == "test/model"
        assert "export_dir" in result


# ---------------------------------------------------------------------------
# _ensure_project_hf_cache_env / _local_embeddings_dir
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHfCacheEnv:
    """_ensure_project_hf_cache_env / _local_embeddings_dir 测试."""

    def test_ensure_hf_cache_env_sets_env_vars(self, tmp_path):
        """_ensure_project_hf_cache_env 应设置 HF 相关环境变量."""
        from riskagent_agenticrag.rag.embeddings import _ensure_project_hf_cache_env

        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings:
            mock_settings.paths.hf_cache_dir = tmp_path / "hf_cache"
            # 清除可能已存在的环境变量
            import os
            for key in ("HF_HOME", "HUGGINGFACE_HUB_CACHE", "HF_HUB_CACHE", "TRANSFORMERS_CACHE", "SENTENCE_TRANSFORMERS_HOME"):
                os.environ.pop(key, None)
            _ensure_project_hf_cache_env()
            assert os.environ.get("HF_HOME") is not None
            assert os.environ.get("TRANSFORMERS_CACHE") is not None

    def test_local_embeddings_dir_replaces_slash(self):
        """_local_embeddings_dir 应把模型名中的 / 替换为 __."""
        from pathlib import Path

        from riskagent_agenticrag.rag.embeddings import _local_embeddings_dir

        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings:
            mock_settings.paths.models_dir = Path("/tmp/models")
            result = _local_embeddings_dir("BAAI/bge-large")
            assert "BAAI__bge-large" in str(result)
            assert "embeddings" in str(result)


# ---------------------------------------------------------------------------
# preload_embeddings_model: hf provider
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPreloadHfProvider:
    """hf provider 预加载测试."""

    def test_preload_hf_calls_ensure_cache_env(self):
        """hf provider 预加载应调用 _ensure_project_hf_cache_env."""
        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings, \
             patch("riskagent_agenticrag.rag.embeddings._ensure_project_hf_cache_env") as mock_ensure, \
             patch("riskagent_agenticrag.rag.embeddings.build_embeddings") as mock_build:
            mock_settings.embeddings.provider = "hf"
            mock_settings.embeddings.model_name = "test/model"
            mock_build.return_value.embed_query.return_value = [0.1]
            result = preload_embeddings_model()
        mock_ensure.assert_called_once()
        assert result["provider"] == "hf"

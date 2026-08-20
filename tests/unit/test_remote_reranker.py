"""remote_reranker 模块单元测试 -- 远程 /rerank 端点封装."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from riskagent_agenticrag.rag.remote_reranker import RemoteReranker

# ---------------------------------------------------------------------------
# 构造辅助
# ---------------------------------------------------------------------------

def _make_reranker(transport: httpx.MockTransport) -> RemoteReranker:
    """构造带 mock transport 的 RemoteReranker, 不发真实网络请求."""
    rr = RemoteReranker(
        model="BAAI/bge-reranker-v2-m3",
        api_key="test-key",
        base_url="https://api.test.com/v1",
        timeout=5.0,
    )
    # 替换底层 client 为带 mock transport 的实例 (接口不变)
    rr._client = httpx.Client(transport=transport, timeout=5.0)
    return rr


def _ok_response(results: list[dict[str, Any]]) -> httpx.Response:
    """构造 200 响应, results 为 [{index, relevance_score}, ...]."""
    return httpx.Response(200, json={"results": results})


# ---------------------------------------------------------------------------
# predict 基本行为
# ===========================================================================

class TestPredict:

    @pytest.mark.unit
    def test_predict_empty_pairs_returns_empty(self):
        """空 pairs 直接返回空列表, 不发请求."""
        rr = _make_reranker(httpx.MockTransport(lambda req: _ok_response([])))
        assert rr.predict([]) == []

    @pytest.mark.unit
    def test_predict_maps_scores_by_index(self):
        """分数应按响应中的 index 映射回输入顺序, 而非响应顺序."""
        # 响应里 index=1 在前, index=0 在后 -- 输出必须按输入顺序 [0.9, 0.1]
        rr = _make_reranker(
            httpx.MockTransport(
                lambda req: _ok_response(
                    [
                        {"index": 1, "relevance_score": 0.1},
                        {"index": 0, "relevance_score": 0.9},
                    ]
                )
            )
        )
        scores = rr.predict([("What is XVA?", "doc-a"), ("What is XVA?", "doc-b")])
        assert scores == [0.9, 0.1]

    @pytest.mark.unit
    def test_predict_missing_index_defaults_zero(self):
        """响应中缺失的 index 对应分数为 0.0."""
        rr = _make_reranker(
            httpx.MockTransport(
                lambda req: _ok_response([{"index": 0, "relevance_score": 0.7}])
            )
        )
        scores = rr.predict([("q", "a"), ("q", "b"), ("q", "c")])
        assert scores == [0.7, 0.0, 0.0]

    @pytest.mark.unit
    def test_predict_ignores_out_of_range_index(self):
        """越界 index (负数或超长) 应被忽略, 不抛异常."""
        rr = _make_reranker(
            httpx.MockTransport(
                lambda req: _ok_response(
                    [
                        {"index": -1, "relevance_score": 0.5},
                        {"index": 99, "relevance_score": 0.8},
                        {"index": 0, "relevance_score": 0.3},
                    ]
                )
            )
        )
        scores = rr.predict([("q", "a")])
        assert scores == [0.3]

    @pytest.mark.unit
    def test_predict_batches_documents_of_32(self):
        """超过 32 个文档时分批请求, 分数按输入顺序拼接."""
        calls: list[dict[str, Any]] = []

        def handler(req: httpx.Request) -> httpx.Response:
            body = json.loads(req.read())
            calls.append(body)
            # 每批返回本批内 index 递增的分数
            n = len(body["documents"])
            return _ok_response(
                [{"index": i, "relevance_score": round(0.1 * i, 2)} for i in range(n)]
            )

        rr = _make_reranker(httpx.MockTransport(handler))
        pairs = [("q", f"doc-{i}") for i in range(70)]  # 32 + 32 + 6
        scores = rr.predict(pairs)

        assert len(calls) == 3
        assert [len(c["documents"]) for c in calls] == [32, 32, 6]
        assert len(scores) == 70
        # 分数按输入顺序拼接: 批内 index 连续递增
        assert scores[0] == 0.0
        assert scores[31] == pytest.approx(3.1)
        assert scores[32] == 0.0  # 第二批的第 0 个

    @pytest.mark.unit
    def test_predict_sends_expected_payload(self):
        """请求体应包含 model/query/documents/top_n 字段和 Bearer 头."""
        captured: dict[str, Any] = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["auth"] = req.headers.get("Authorization")
            captured["url"] = str(req.url)
            captured["body"] = json.loads(req.read())
            return _ok_response([{"index": 0, "relevance_score": 1.0}])

        rr = _make_reranker(httpx.MockTransport(handler))
        rr.predict([("What is FVA?", "FVA is funding valuation adjustment")])

        assert captured["auth"] == "Bearer test-key"
        assert captured["url"].endswith("/rerank")
        assert captured["body"]["model"] == "BAAI/bge-reranker-v2-m3"
        assert captured["body"]["query"] == "What is FVA?"
        assert captured["body"]["documents"] == ["FVA is funding valuation adjustment"]
        assert captured["body"]["top_n"] == 1
        assert captured["body"]["return_documents"] is False


# ---------------------------------------------------------------------------
# 错误路径
# ===========================================================================

class TestPredictErrors:

    @pytest.mark.unit
    def test_predict_raises_on_http_error(self):
        """HTTP 500 应抛 httpx.HTTPStatusError (由 raise_for_status 触发)."""
        rr = _make_reranker(
            httpx.MockTransport(lambda req: httpx.Response(500, text="boom"))
        )
        with pytest.raises(httpx.HTTPStatusError):
            rr.predict([("q", "a")])

    @pytest.mark.unit
    def test_predict_empty_results_field(self):
        """响应无 results 字段时返回全 0 分数, 不抛异常."""
        rr = _make_reranker(
            httpx.MockTransport(lambda req: httpx.Response(200, json={}))
        )
        assert rr.predict([("q", "a"), ("q", "b")]) == [0.0, 0.0]


# ---------------------------------------------------------------------------
# build_remote_reranker 工厂
# ===========================================================================

class TestBuildRemoteReranker:

    @pytest.mark.unit
    def test_build_uses_embeddings_config(self, monkeypatch):
        """工厂应优先用 embeddings 配置的 api_key/base_url."""
        from pydantic import SecretStr
        from riskagent_agenticrag.config import settings as settings_mod

        monkeypatch.setattr(
            settings_mod.settings.embeddings,
            "api_key",
            SecretStr("sk-emb-test"),
            raising=False,
        )
        monkeypatch.setattr(
            settings_mod.settings.embeddings, "base_url", "https://emb.test.com/v1", raising=False
        )
        from riskagent_agenticrag.rag.remote_reranker import build_remote_reranker

        rr = build_remote_reranker()
        assert rr.model == "BAAI/bge-reranker-v2-m3"
        assert rr._url == "https://emb.test.com/v1/rerank"
        assert rr._api_key == "sk-emb-test"

    @pytest.mark.unit
    def test_build_falls_back_to_llm_config(self, monkeypatch):
        """embeddings 缺 api_key/base_url 时回退到 LLM 配置.

        resolved_api_key 是 property, 故通过 patch llm.api_key (SecretStr) 生效.
        """
        from pydantic import SecretStr
        from riskagent_agenticrag.config import settings as settings_mod

        monkeypatch.setattr(
            settings_mod.settings.embeddings, "api_key", None, raising=False
        )
        monkeypatch.setattr(
            settings_mod.settings.embeddings, "base_url", "", raising=False
        )
        monkeypatch.setattr(
            settings_mod.settings.llm, "api_key", SecretStr("sk-llm-test"), raising=False
        )
        monkeypatch.setattr(
            settings_mod.settings.llm, "base_url", "https://llm.test.com/v1", raising=False
        )
        from riskagent_agenticrag.rag.remote_reranker import build_remote_reranker

        rr = build_remote_reranker()
        assert rr._url == "https://llm.test.com/v1/rerank"
        assert rr._api_key == "sk-llm-test"


# ---------------------------------------------------------------------------
# URL 拼接边界
# ===========================================================================

@pytest.mark.unit
def test_base_url_trailing_slash_normalized():
    """base_url 末尾多余的 / 不应产生 //rerank."""
    from riskagent_agenticrag.rag.remote_reranker import RemoteReranker

    rr = RemoteReranker(model="m", api_key="k", base_url="https://x.com/v1//")
    assert rr._url == "https://x.com/v1//rerank" or rr._url.endswith("/rerank")
    assert "//rerank" not in rr._url.replace("://", "")  # 仅协议分隔符允许 //

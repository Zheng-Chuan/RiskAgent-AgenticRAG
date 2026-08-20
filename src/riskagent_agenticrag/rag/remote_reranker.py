"""远程 Reranker: 调用 OpenAI 兼容生态的 /rerank 端点 (如硅基流动 BAAI/bge-reranker-v2-m3).

背景: 本地 CrossEncoder 需要 sentence_transformers + torch + 模型文件 (数 GB),
容器镜像未携带导致 rerank 从未生效 (评测 0/205 docs 有 rerank_score).
远程方案与 embedding 同一 API 生态, 零本地依赖.
"""

from __future__ import annotations

import threading
from typing import Any

import httpx

from riskagent_agenticrag.config.settings import settings


class RemoteReranker:
    """线程安全的远程 reranker, 接口与 CrossEncoder.predict(pairs) 对齐."""

    def __init__(self, *, model: str, api_key: str, base_url: str, timeout: float = 30.0) -> None:
        self.model = model
        self._api_key = api_key
        self._url = base_url.rstrip("/") + "/rerank"
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        self._lock = threading.Lock()

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        """对 (query, document) 对打分, 返回与 pairs 等长的分数列表 (输入顺序)."""
        if not pairs:
            return []
        query = pairs[0][0]
        documents = [d for _, d in pairs]
        # 分批: 单次请求文档数过多易触发 payload 限制
        scores: list[float] = []
        batch = 32
        for i in range(0, len(documents), batch):
            scores.extend(self._rerank_batch(query, documents[i : i + batch]))
        return scores

    def _rerank_batch(self, query: str, documents: list[str]) -> list[float]:
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": len(documents),
            "return_documents": False,
        }
        with self._lock:
            resp = self._client.post(
                self._url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        # 响应 results: [{index, relevance_score}, ...] index 指向请求中的文档位置
        out = [0.0] * len(documents)
        for item in data.get("results", []):
            idx = int(item.get("index", -1))
            if 0 <= idx < len(out):
                out[idx] = float(item.get("relevance_score", 0.0))
        return out


def build_remote_reranker() -> RemoteReranker:
    """从项目配置构建远程 reranker (与 embedding 同一 provider 生态)."""
    emb = settings.embeddings
    model = "BAAI/bge-reranker-v2-m3"
    api_key_obj = emb.api_key or settings.llm.resolved_api_key
    base_url = emb.base_url or settings.llm.base_url
    return RemoteReranker(
        model=model,
        api_key=api_key_obj.get_secret_value(),
        base_url=base_url,
        timeout=30.0,
    )

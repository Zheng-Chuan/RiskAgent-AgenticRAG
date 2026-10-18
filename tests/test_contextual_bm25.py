from __future__ import annotations

import importlib
import unittest

from langchain_core.documents import Document

hybrid_mod = importlib.import_module("riskagent_agenticrag.rag.hybrid_retriever")
bm25_effective_text = hybrid_mod.bm25_effective_text
HybridConfig = hybrid_mod.HybridConfig
HybridRetriever = hybrid_mod.HybridRetriever

utils_mod = importlib.import_module("riskagent_agenticrag.rag.utils")
_embedding_texts = utils_mod.embedding_texts


def _doc(text: str, **meta: object) -> Document:
    return Document(page_content=text, metadata=dict(meta))


class Bm25EffectiveTextTest(unittest.TestCase):
    def test_off_returns_plain_text(self) -> None:
        d = _doc("chunk body", context_brief="a brief", source="corpus/A.md", section_path="A / B")
        self.assertEqual(bm25_effective_text(d, mode="off"), "chunk body")

    def test_llm_brief_prepends_brief(self) -> None:
        d = _doc("chunk body", context_brief="from FRTB document about delta")
        self.assertEqual(
            bm25_effective_text(d, mode="llm_brief"),
            "from FRTB document about delta\nchunk body",
        )

    def test_llm_brief_without_brief_falls_back_to_plain(self) -> None:
        d = _doc("chunk body")
        self.assertEqual(bm25_effective_text(d, mode="llm_brief"), "chunk body")

    def test_short_brief_prepends_title_and_section(self) -> None:
        d = _doc("chunk body", source="corpus/d457.md", section_path="d457 / Delta risk / Weights")
        text = bm25_effective_text(d, mode="short_brief")
        self.assertTrue(text.startswith("[doc: d457 | section: d457 / Delta risk / Weights]"))
        self.assertTrue(text.endswith("chunk body"))

    def test_short_brief_without_metadata_falls_back(self) -> None:
        self.assertEqual(bm25_effective_text(_doc("chunk body"), mode="short_brief"), "chunk body")

    def test_unknown_mode_returns_plain(self) -> None:
        d = _doc("chunk body", context_brief="brief", source="corpus/A.md", section_path="s")
        self.assertEqual(bm25_effective_text(d, mode="bogus"), "chunk body")


class HybridRetrieverContextualBm25Test(unittest.TestCase):
    """端到端验证 config.bm25_context_mode 接线: brief 进 BM25 词表.

    target 的 chunk 文本不含查询词 (delta 只出现在 brief / section_path 里).
    invoke 排序受 metadata_boost 等因素干扰, 因此直接断言 BM25 分数.
    """

    def _make_retriever(self, mode: str) -> HybridRetriever:
        filler = "plain filler text about revenue and quarterly outlook statements "
        # 多个 distractor: BM25Okapi 的 IDF 在词覆盖 >=50% 文档时为 0,
        # 查询词只应出现在 target 的 brief 里
        sparse_docs = [
            _doc(
                "general overview of trading desk organisation and reporting lines",
                chunk_id="distractor",
                source="corpus/Overview.md",
                section_path="Overview / Org",
                context_brief="",
            ),
            _doc(
                "risk committee charter and escalation procedures across divisions",
                chunk_id="distractor2",
                source="corpus/Governance.md",
                section_path="Governance / Charter",
                context_brief="",
            ),
            _doc(
                "annual budget planning assumptions and headcount forecasts",
                chunk_id="distractor3",
                source="corpus/Planning.md",
                section_path="Planning / Budget",
                context_brief="",
            ),
            _doc(
                filler * 4,
                chunk_id="target",
                source="corpus/Report.md",
                section_path="Report / Delta sensitivity",
                context_brief="This chunk discusses delta hedging under FRTB.",
            ),
        ]
        cfg = HybridConfig(
            min_chunk_chars=20,
            max_per_source=4,
            max_per_section=4,
            reranker_model="",
            reranker_candidates=(),
            final_k=4,
            bm25_context_mode=mode,
        )
        return HybridRetriever(dense_retriever=_NoopDense(), sparse_docs=sparse_docs, config=cfg)

    def _target_bm25_score(self, mode: str) -> float:
        retriever = self._make_retriever(mode)
        assert retriever._bm25 is not None
        scores = retriever._bm25.get_scores(hybrid_mod.tokenize("delta hedging"))
        return float(scores[3])  # target 是 sparse_docs[3]

    def test_off_mode_target_scores_zero(self) -> None:
        self.assertEqual(self._target_bm25_score("off"), 0.0)

    def test_short_brief_mode_target_scores_positive(self) -> None:
        self.assertGreater(self._target_bm25_score("short_brief"), 0.0)

    def test_llm_brief_mode_target_scores_positive(self) -> None:
        self.assertGreater(self._target_bm25_score("llm_brief"), 0.0)


class _NoopDense:
    def invoke(self, query: str) -> list[Document]:
        return []


class EmbeddingTextsTest(unittest.TestCase):
    def test_inject_brief_prepends(self) -> None:
        chunks = [_doc("body", context_brief="brief text")]
        self.assertEqual(
            _embedding_texts(chunks, inject_brief=True),
            ["brief text\nbody"],
        )

    def test_no_inject_keeps_plain_text_even_with_brief(self) -> None:
        # RFC-006 C2 变体一: brief 只进元数据/BM25, embedding 纯 chunk 文本
        chunks = [_doc("body", context_brief="brief text")]
        self.assertEqual(_embedding_texts(chunks, inject_brief=False), ["body"])

    def test_missing_brief_keeps_plain(self) -> None:
        self.assertEqual(_embedding_texts([_doc("body")], inject_brief=True), ["body"])


if __name__ == "__main__":
    unittest.main()

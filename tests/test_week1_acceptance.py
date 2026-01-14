from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

from tests.conftest import ensure_src_on_path


# ROADMAP 验收映射表
# Week 1
# - 端到端可复现: 清空索引 -> ingest -> 查询 -> 返回 answer + citations
#   - test_week1_e2e_rebuild_query_answer_citations
# - 返回 citations, 且可定位来源
#   - test_week1_citations_point_to_sources
# - 至少 1 条 e2e smoke test 可通过
#   - test_week1_smoke_test_equivalent


def _is_valid_citation_source(source: str) -> bool:
    # 中文注释, 最小口径, citations source 必须回指到 docs/sources.
    normalized = "/" + source.replace("\\", "/").strip("/") + "/"
    return "/corpus/" in normalized


class Week1AcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_src_on_path()

    def setUp(self) -> None:
        # 中文注释, 默认使用 fake embeddings, 避免首次运行需要下载模型.
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "fake")

        # 中文注释: 默认连接本地 Docker Milvus.
        os.environ.setdefault("MILVUS_HOST", "localhost")
        os.environ.setdefault("MILVUS_PORT", "19530")

        self.project_root = pathlib.Path(__file__).resolve().parent.parent
        self.sources_dir = self.project_root / "corpus"
        self._tmp = tempfile.TemporaryDirectory()
        self.persist_dir = pathlib.Path(self._tmp.name) / "milvus"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_week1_e2e_rebuild_query_answer_citations(self) -> None:
        from riskagent_rag.graph.workflow import build_rag_graph
        from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index

        result = build_index(sources_dir=self.sources_dir, persist_dir=self.persist_dir)
        self.assertGreaterEqual(result.source_count, 1)
        self.assertGreaterEqual(result.chunk_count, 1)

        vectorstore = load_index(self.persist_dir)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        graph = build_rag_graph(retriever)

        question = "what is FRTB"
        out = graph.invoke({"question": question})

        answer = str(out.get("answer", ""))
        docs = out.get("docs", [])
        citations = extract_citations(docs)

        self.assertTrue(answer.strip(), "week1 e2e failed: empty answer")
        self.assertTrue(citations, "week1 e2e failed: empty citations")

        out_path = pathlib.Path(self._tmp.name) / "week1_smoke_result.json"
        out_path.write_text(
            json.dumps(
                {
                    "question": question,
                    "answer": answer,
                    "citations": citations,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def test_week1_citations_point_to_sources(self) -> None:
        from riskagent_rag.graph.workflow import build_rag_graph
        from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index

        build_index(sources_dir=self.sources_dir, persist_dir=self.persist_dir)

        vectorstore = load_index(self.persist_dir)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        graph = build_rag_graph(retriever)

        out = graph.invoke({"question": "what is FRTB"})
        citations = extract_citations(out.get("docs", []))

        self.assertTrue(citations, "week1 citations missing")

        first_source = str(citations[0].get("source", ""))
        self.assertTrue(
            _is_valid_citation_source(first_source),
            f"week1 citations invalid source: {first_source}",
        )

    def test_week1_smoke_test_equivalent(self) -> None:
        # 中文注释, 这个测试用于 Week 1 的 e2e smoke 验收.
        from riskagent_rag.graph.workflow import build_rag_graph
        from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index

        build_index(sources_dir=self.sources_dir, persist_dir=self.persist_dir)

        vectorstore = load_index(self.persist_dir)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        graph = build_rag_graph(retriever)

        out = graph.invoke({"question": "what is FRTB"})
        answer = str(out.get("answer", ""))
        citations = extract_citations(out.get("docs", []))

        self.assertTrue(answer.strip(), "week1 smoke failed: empty answer")
        self.assertTrue(citations, "week1 smoke failed: empty citations")

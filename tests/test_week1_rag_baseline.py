from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

from tests.conftest import ensure_src_on_path


def _is_valid_citation_source(source: str) -> bool:
    """
    验证引用来源是否合法
    Week 1 验收标准: 返回 citations, 且可定位来源
    """
    # 最小口径, citations source 必须回指到 docs/sources.
    normalized = "/" + source.replace("\\", "/").strip("/") + "/"
    return "/corpus/" in normalized


class Week1RAGBaselineTest(unittest.TestCase):
    """
    Week 1: Baseline RAG 跑通 + 工程化骨架
    
    Roadmap 对应验收项:
    - [x] 端到端可复现: 清空索引 -> ingest -> 查询 -> 返回 answer + citations
    - [x] 返回 citations, 且可定位来源
    - [x] 至少 1 条 e2e smoke test 可通过
    """
    
    @classmethod
    def setUpClass(cls) -> None:
        ensure_src_on_path()

    def setUp(self) -> None:
        # 默认使用真实 embeddings (HuggingFace), 用于锁定检索质量与 citations 行为.
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")

        # 单测默认走 Milvus Lite(本地文件), 避免依赖 Docker 中间件.
        # 如需切换到 Docker Milvus, 设置环境变量 RISKAGENT_USE_DOCKER_MILVUS=true.
        use_docker_milvus = os.getenv("RISKAGENT_USE_DOCKER_MILVUS", "").lower().strip() in ("true", "1", "yes")
        if not use_docker_milvus:
            os.environ.pop("MILVUS_URI", None)
            os.environ.pop("MILVUS_HOST", None)
            os.environ.pop("MILVUS_PORT", None)
            os.environ["MILVUS_WAIT_READY"] = "false"

        self.project_root = pathlib.Path(__file__).resolve().parent.parent
        self.sources_dir = self.project_root / "corpus"
        self._tmp = tempfile.TemporaryDirectory()
        self.persist_dir = pathlib.Path(self._tmp.name) / "milvus"
        
        # 报告输出目录
        self.report_dir = self.project_root / "tests" / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_baseline_e2e_rebuild_and_query(self) -> None:
        """
        测试 Roadmap: 端到端可复现 (清空索引 -> ingest -> 查询 -> 返回 answer + citations)
        """
        from riskagent_rag.graph.workflow import build_rag_graph
        from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index

        # 1. Ingest (Build Index in temp dir = Clean state)
        result = build_index(sources_dir=self.sources_dir, persist_dir=self.persist_dir)
        self.assertGreaterEqual(result.source_count, 1, "Should ingest at least 1 source file")
        self.assertGreaterEqual(result.chunk_count, 1, "Should create at least 1 chunk")

        # 2. Load and Build Graph
        vectorstore = load_index(self.persist_dir)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        graph = build_rag_graph(retriever)

        # 3. Query
        question = "what is FRTB"
        out = graph.invoke({"question": question})

        answer = str(out.get("answer", ""))
        docs = out.get("docs", [])
        citations = extract_citations(docs)

        # 4. Verify Answer and Citations
        self.assertTrue(answer.strip(), "Week 1 baseline failed: empty answer")
        self.assertTrue(citations, "Week 1 baseline failed: empty citations")

        # 5. Generate Report
        report_data = {
            "test_name": "test_baseline_e2e_rebuild_and_query",
            "question": question,
            "answer": answer,
            "citations": citations,
            "ingest_stats": {
                "source_count": result.source_count,
                "chunk_count": result.chunk_count
            }
        }
        
        out_path = self.report_dir / "week1_rag_baseline_report.json"
        out_path.write_text(
            json.dumps(report_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nWeek 1 Baseline Report saved to: {out_path}")

    def test_baseline_citations_validity(self) -> None:
        """
        测试 Roadmap: 返回 citations, 且可定位来源
        """
        from riskagent_rag.graph.workflow import build_rag_graph
        from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index

        build_index(sources_dir=self.sources_dir, persist_dir=self.persist_dir)

        vectorstore = load_index(self.persist_dir)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        graph = build_rag_graph(retriever)

        out = graph.invoke({"question": "what is FRTB"})
        citations = extract_citations(out.get("docs", []))

        self.assertTrue(citations, "Week 1 citations missing")

        first_source = str(citations[0].get("source", ""))
        self.assertTrue(
            _is_valid_citation_source(first_source),
            f"Week 1 citations invalid source format: {first_source}. Should contain '/corpus/'"
        )

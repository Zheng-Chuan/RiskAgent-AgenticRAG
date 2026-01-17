from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

from tests.conftest import ensure_src_on_path


def _is_valid_citation(c: dict) -> bool:
    source = str(c.get("source", ""))
    chunk_id = str(c.get("chunk_id", ""))
    if not source or not chunk_id:
        return False
    normalized = "/" + source.replace("\\", "/").strip("/") + "/"
    return "/corpus/" in normalized


class Week2RAGCitationQualityTest(unittest.TestCase):
    """
    Week 2: RAG MVP 闭环与引用质量
    
    Roadmap 对应验收项:
    - [x] 20 个问题中, 80% 以上回答包含有效 citations
    - [x] RAG MVP 闭环 (Ingest -> Index -> Retrieve -> Answer)
    """
    
    @classmethod
    def setUpClass(cls) -> None:
        ensure_src_on_path()

    def setUp(self) -> None:
        # 默认使用真实 embeddings, 用于锁定检索质量与 citations 行为.
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")

        # 单测默认走 Milvus Lite(本地文件), 避免依赖 Docker 中间件.
        use_docker_milvus = os.getenv("RISKAGENT_USE_DOCKER_MILVUS", "").lower().strip() in ("true", "1", "yes")
        if not use_docker_milvus:
            os.environ.pop("MILVUS_URI", None)
            os.environ.pop("MILVUS_HOST", None)
            os.environ.pop("MILVUS_PORT", None)
            os.environ["MILVUS_WAIT_READY"] = "false"

        self.project_root = pathlib.Path(__file__).resolve().parent.parent
        self.sources_dir = self.project_root / "corpus"
        self.questions_path = self.project_root / "tests" / "data" / "questions.json"
        self._tmp = tempfile.TemporaryDirectory()
        self.persist_dir = pathlib.Path(self._tmp.name) / "milvus"
        
        # 报告输出目录
        self.report_dir = self.project_root / "tests" / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_citation_coverage_ge_80pct(self) -> None:
        """
        测试 Roadmap: 20 个问题中, 80% 以上回答包含有效 citations
        """
        from riskagent_rag.graph.workflow import build_rag_graph
        from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index

        # Load questions
        items = json.loads(self.questions_path.read_text(encoding="utf-8"))
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 20, "Should have 20 seed questions")

        # Build Index
        build_index(sources_dir=self.sources_dir, persist_dir=self.persist_dir)

        # Init RAG
        vectorstore = load_index(self.persist_dir)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        graph = build_rag_graph(retriever)

        rows: list[dict] = []
        ok = 0

        print(f"\nRunning Citation Coverage Test on {len(items)} questions...")

        for item in items:
            qid = str(item.get("id", ""))
            question = str(item.get("question", ""))
            out = graph.invoke({"question": question})

            answer = out.get("answer", "")
            docs = out.get("docs", [])
            citations = extract_citations(docs)

            valid_citations = [c for c in citations if _is_valid_citation(c)]
            
            # Criterion: Answer is not empty AND has valid citations
            passed = bool(str(answer).strip()) and bool(valid_citations)
            if passed:
                ok += 1

            rows.append(
                {
                    "id": qid,
                    "question": question,
                    "passed": passed,
                    "answer_len": len(str(answer)),
                    "citation_count": len(citations),
                    "valid_citation_count": len(valid_citations),
                    "citations": citations,
                    "answer_preview": str(answer)[:100] + "..." if len(str(answer)) > 100 else str(answer)
                }
            )

        total = len(rows)
        coverage = (ok / total) if total else 0.0

        report = {
            "test_name": "test_citation_coverage_ge_80pct",
            "total": total,
            "passed": ok,
            "coverage": coverage,
            "settings": {
                "sources_dir": str(self.sources_dir),
                "persist_dir": str(self.persist_dir),
                "k": 4,
            },
            "results": rows,
        }

        out_path = self.report_dir / "week2_citation_quality_report.json"
        out_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Week 2 Citation Quality Report saved to: {out_path}")

        self.assertEqual(total, 20)
        self.assertGreaterEqual(coverage, 0.8, f"Coverage {coverage:.2%} < 80%. Report: {out_path}")

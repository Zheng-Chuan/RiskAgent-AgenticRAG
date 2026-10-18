from __future__ import annotations

import importlib
import os
import unittest
from unittest import mock

from langchain_core.documents import Document

loader_mod = importlib.import_module("riskagent_agenticrag.rag.source_loader")
table_to_markdown = loader_mod.table_to_markdown
_extract_pdf_tables = loader_mod._extract_pdf_tables
_pdf_tables_enabled = loader_mod._pdf_tables_enabled

ingestion_mod = importlib.import_module("riskagent_agenticrag.rag.ingestion")
split_documents = ingestion_mod.split_documents


class TableToMarkdownTest(unittest.TestCase):
    def test_basic_table(self) -> None:
        md = table_to_markdown([["Risk class", "Multiplier"], ["Delta", "1.5"], ["Vega", "1.5"]])
        lines = md.splitlines()
        self.assertEqual(lines[0], "| Risk class | Multiplier |")
        self.assertEqual(lines[1], "| --- | --- |")
        self.assertEqual(lines[2], "| Delta | 1.5 |")

    def test_ragged_rows_padded(self) -> None:
        md = table_to_markdown([["a", "b"], ["c"]])
        self.assertEqual(md.splitlines()[2], "| c |  |")

    def test_pipe_escaped(self) -> None:
        md = table_to_markdown([["h"], ["x | y"]])
        self.assertIn("x \\| y", md)

    def test_empty_header_uses_col_names(self) -> None:
        md = table_to_markdown([["", ""], ["v1", "v2"]])
        self.assertIn("| col1 | col2 |", md)

    def test_empty_input(self) -> None:
        self.assertEqual(table_to_markdown([]), "")
        self.assertEqual(table_to_markdown([[]]), "")


class PdfTablesEnabledTest(unittest.TestCase):
    def test_default_enabled(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RISKAGENT_PDF_TABLES", None)
            self.assertTrue(_pdf_tables_enabled())

    def test_env_disables(self) -> None:
        with mock.patch.dict(os.environ, {"RISKAGENT_PDF_TABLES": "false"}):
            self.assertFalse(_pdf_tables_enabled())


class ExtractPdfTablesFilterTest(unittest.TestCase):
    def _extract_with_fake_pdf(self, tables: list) -> list[Document]:
        fake_page = mock.Mock()
        fake_page.extract_tables.return_value = tables
        fake_pdf = mock.MagicMock()
        fake_pdf.pages = [fake_page]
        fake_pdf.__enter__.return_value = fake_pdf
        fake_pdf.__exit__.return_value = None
        with mock.patch.dict("sys.modules", {"pdfplumber": mock.MagicMock(open=lambda *a, **k: fake_pdf)}):
            return _extract_pdf_tables(loader_mod.pathlib.Path("corpus/x.pdf"))

    def test_single_row_detection_filtered(self) -> None:
        # 模拟 pdfplumber 误检: 单行文本被识别为 1 列表格
        docs = self._extract_with_fake_pdf([["97.5% ES = average of worst 2.5% of losses"]])
        self.assertEqual(docs, [])

    def test_real_table_passes_filter(self) -> None:
        rows = [
            ["Risk class", "Multiplier", "Correlation"],
            ["Delta", "1.5", "0.6"],
            ["Vega", "1.5", "0.6"],
        ]
        docs = self._extract_with_fake_pdf([rows])
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].metadata["chunk_type"], "table")
        self.assertEqual(docs[0].metadata["page"], 1)
        self.assertEqual(docs[0].metadata["table_index"], 1)
        self.assertIn("| Delta | 1.5 | 0.6 |", docs[0].page_content)


class SplitDocumentsTablePassThroughTest(unittest.TestCase):
    def test_table_chunk_not_split(self) -> None:
        table_doc = Document(
            page_content="| a | b |\n| --- | --- |\n| 1 | 2 |",
            metadata={"source": "corpus/x.pdf", "file_type": "pdf", "chunk_type": "table", "page": 3},
        )
        long_text = "word " * 400
        text_doc = Document(
            page_content=long_text, metadata={"source": "corpus/y.md", "file_type": "md"}
        )
        chunks = split_documents([table_doc, text_doc], use_llm_chunking=False)
        table_chunks = [c for c in chunks if str(c.metadata.get("chunk_type", "")).lower() == "table"]
        self.assertEqual(len(table_chunks), 1)
        self.assertIn("| a | b |", table_chunks[0].page_content)
        self.assertEqual(table_chunks[0].metadata["page"], 3)
        # 非 table 文档正常被切分
        self.assertGreater(len([c for c in chunks if str(c.metadata.get("chunk_type", "")).lower() != "table"]), 1)

    def test_table_chunk_exempt_from_junk_filter(self) -> None:
        # 年份密度高的监管表格不应被参考文献启发式误杀
        rows = "| Year | 2019 | 2020 | 2021 | 2022 |\n| --- | --- | --- | --- | --- |\n"
        rows += "| Floor | 2019 | 2020 | 2021 | 2022 |\n"
        table_doc = Document(
            page_content=rows,
            metadata={"source": "corpus/x.pdf", "file_type": "pdf", "chunk_type": "table", "page": 1},
        )
        chunks = split_documents([table_doc], use_llm_chunking=False)
        self.assertEqual(len(chunks), 1)


class ChunkingConfigTest(unittest.TestCase):
    """schema fingerprint 里的 pdf_tables 开关与 policy_version 升级 (触发全量重建).

    indexer 依赖 pymilvus, 环境缺依赖时跳过.
    """

    def setUp(self) -> None:
        try:
            self.indexer_mod = importlib.import_module("riskagent_agenticrag.indexing.indexer")
        except Exception as exc:
            self.skipTest(f"indexer import failed: {exc}")

    def test_pdf_tables_flag_in_fingerprint(self) -> None:
        with mock.patch.dict(os.environ, {"RISKAGENT_PDF_TABLES": "false", "RISKAGENT_USE_LLM_CHUNKING": "false"}):
            cfg_off = self.indexer_mod._chunking_config()
        with mock.patch.dict(os.environ, {"RISKAGENT_PDF_TABLES": "true", "RISKAGENT_USE_LLM_CHUNKING": "false"}):
            cfg_on = self.indexer_mod._chunking_config()
        self.assertFalse(cfg_off["pdf_tables"])
        self.assertTrue(cfg_on["pdf_tables"])
        # 开关变化应改变 policy_version, 触发 schema fingerprint 不一致 -> 全量重建
        self.assertNotEqual(cfg_off["policy_version"], cfg_on["policy_version"])
        self.assertIn("v2", cfg_on["policy_version"])


if __name__ == "__main__":
    unittest.main()

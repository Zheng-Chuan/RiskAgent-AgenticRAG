"""语料加载器多格式测试.

覆盖 source_loader.py 中的 PDF / DOCX / Excel / HTML 加载器及 get_supported_formats.
PDF/DOCX/Excel 通过 mock 第三方库实现, HTML 使用真实小文件 (bs4 已安装).
"""

from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, patch

import pytest
from riskagent_agenticrag.rag.source_loader import (
    _load_docx,
    _load_excel,
    _load_html,
    _load_pdf,
    _load_single_document,
    get_supported_formats,
    load_sources,
)

# ---------------------------------------------------------------------------
# get_supported_formats
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSupportedFormats:
    """支持的格式清单."""

    def test_returns_md_pdf_docx_excel_html(self):
        """应包含 md / pdf / docx / xlsx / xls / html / htm."""
        fmts = get_supported_formats()
        assert ".md" in fmts
        assert ".pdf" in fmts
        assert ".docx" in fmts
        assert ".xlsx" in fmts
        assert ".xls" in fmts
        assert ".html" in fmts
        assert ".htm" in fmts

    def test_all_values_are_strings(self):
        """所有描述应为字符串."""
        fmts = get_supported_formats()
        for v in fmts.values():
            assert isinstance(v, str)
            assert len(v) > 0


# ---------------------------------------------------------------------------
# _load_single_document
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadSingleDocument:
    """单个文本文件加载."""

    def test_loads_text_with_metadata(self, tmp_path: pathlib.Path):
        """应返回带 source/file_type/_source_text 元数据的 Document."""
        f = tmp_path / "note.txt"
        f.write_text("hello world", encoding="utf-8")
        docs = _load_single_document(f, "txt")
        assert len(docs) == 1
        assert docs[0].page_content == "hello world"
        assert docs[0].metadata["file_type"] == "txt"
        assert docs[0].metadata["source"] == str(f)


# ---------------------------------------------------------------------------
# _load_html (真实小文件)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadHtml:
    """HTML 加载器测试 (使用真实小文件)."""

    def test_loads_html_with_title_and_body(self, tmp_path: pathlib.Path):
        """应提取 title 和正文内容."""
        html = """<!DOCTYPE html>
<html><head><title>FRTB Overview</title></head>
<body>
<nav>navigation</nav>
<main><h1>FRTB</h1><p>The Fundamental Review of the Trading Book.</p></main>
</body></html>"""
        f = tmp_path / "page.html"
        f.write_text(html, encoding="utf-8")
        docs = _load_html(f)
        assert len(docs) == 1
        assert docs[0].metadata["file_type"] == "html"
        assert "FRTB" in docs[0].page_content
        assert docs[0].metadata["title"] == "FRTB Overview"

    def test_html_strips_script_and_style(self, tmp_path: pathlib.Path):
        """应移除 script 和 style 元素."""
        html = """<html><head><title>T</title>
<style>.x { color: red; }</style></head>
<body><script>alert(1)</script><p>real content</p></body></html>"""
        f = tmp_path / "p.htm"
        f.write_text(html, encoding="utf-8")
        docs = _load_html(f)
        assert "real content" in docs[0].page_content
        assert "alert" not in docs[0].page_content
        assert "color" not in docs[0].page_content

    def test_html_fallback_to_body_when_no_main(self, tmp_path: pathlib.Path):
        """无 main/article 容器时应回退到 body."""
        html = "<html><head><title>X</title></head><body><p>fallback content</p></body></html>"
        f = tmp_path / "no_main.html"
        f.write_text(html, encoding="utf-8")
        docs = _load_html(f)
        assert "fallback content" in docs[0].page_content

    def test_html_headings_extracted(self, tmp_path: pathlib.Path):
        """应提取标题层级结构."""
        html = """<html><head><title>T</title></head><body>
<h1>Main</h1><h2>Sub</h2><p>text</p></body></html>"""
        f = tmp_path / "headings.html"
        f.write_text(html, encoding="utf-8")
        docs = _load_html(f)
        assert "Headings" in docs[0].page_content
        assert "Main" in docs[0].page_content


# ---------------------------------------------------------------------------
# _load_pdf (mock pypdf)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadPdf:
    """PDF 加载器测试 (mock pypdf)."""

    def test_loads_pdf_pages(self, tmp_path: pathlib.Path):
        """应按页返回 Document."""
        fake_page1 = MagicMock()
        fake_page1.extract_text.return_value = "Page one content"
        fake_page2 = MagicMock()
        fake_page2.extract_text.return_value = "Page two content"

        fake_reader = MagicMock()
        fake_reader.pages = [fake_page1, fake_page2]

        with patch("pypdf.PdfReader", return_value=fake_reader):
            docs = _load_pdf(tmp_path / "fake.pdf")
        assert len(docs) == 2
        assert docs[0].page_content == "Page one content"
        assert docs[0].metadata["page"] == 1
        assert docs[1].metadata["page"] == 2
        assert docs[0].metadata["file_type"] == "pdf"

    def test_pdf_page_with_no_text(self, tmp_path: pathlib.Path):
        """空页应返回空字符串内容."""
        fake_page = MagicMock()
        fake_page.extract_text.return_value = None
        fake_reader = MagicMock()
        fake_reader.pages = [fake_page]
        with patch("pypdf.PdfReader", return_value=fake_reader):
            docs = _load_pdf(tmp_path / "empty.pdf")
        assert len(docs) == 1
        assert docs[0].page_content == ""


# ---------------------------------------------------------------------------
# _load_docx (mock python-docx)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadDocx:
    """DOCX 加载器测试 (mock python-docx)."""

    def test_loads_paragraphs_and_tables(self, tmp_path: pathlib.Path):
        """应提取段落和表格内容."""
        fake_para1 = MagicMock()
        fake_para1.text = "Heading One"
        fake_para1.style.name = "Heading1"

        fake_para2 = MagicMock()
        fake_para2.text = "Normal paragraph text"
        fake_para2.style.name = "Normal"

        fake_empty = MagicMock()
        fake_empty.text = "   "
        fake_empty.style.name = "Normal"

        fake_cell = MagicMock()
        fake_cell.text = "cell1"
        fake_row = MagicMock()
        fake_row.cells = [fake_cell]
        fake_table = MagicMock()
        fake_table.rows = [fake_row, fake_row]

        fake_doc = MagicMock()
        fake_doc.paragraphs = [fake_para1, fake_para2, fake_empty]
        fake_doc.tables = [fake_table]

        with patch("docx.Document", return_value=fake_doc):
            docs = _load_docx(tmp_path / "fake.docx")
        assert len(docs) == 1
        assert "Heading One" in docs[0].page_content
        assert "Normal paragraph" in docs[0].page_content
        assert "Tables" in docs[0].page_content
        assert docs[0].metadata["file_type"] == "docx"


# ---------------------------------------------------------------------------
# _load_excel (mock pandas)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadExcel:
    """Excel 加载器测试 (mock pandas)."""

    def test_loads_sheets_with_columns_and_rows(self, tmp_path: pathlib.Path):
        """应按 sheet 返回 Document, 包含列名与行数据."""
        import pandas as pd

        df = pd.DataFrame({"Risk": ["Delta", "Vega"], "Charge": [100, 200]})
        fake_sheets = {"Sheet1": df}

        with patch("pandas.read_excel", return_value=fake_sheets):
            docs = _load_excel(tmp_path / "fake.xlsx")
        assert len(docs) == 1
        assert "Sheet1" in docs[0].page_content
        assert "Delta" in docs[0].page_content
        assert docs[0].metadata["file_type"] == "excel"
        assert docs[0].metadata["sheet_name"] == "Sheet1"

    def test_excel_xls_uses_xlrd_engine(self, tmp_path: pathlib.Path):
        """xls 后缀应使用 xlrd 引擎."""
        import pandas as pd

        df = pd.DataFrame({"A": [1]})
        with patch("pandas.read_excel", return_value={"S": df}) as mock_read:
            _load_excel(tmp_path / "data.xls")
        _, kwargs = mock_read.call_args
        assert kwargs.get("engine") == "xlrd"

    def test_excel_xlsx_uses_openpyxl_engine(self, tmp_path: pathlib.Path):
        """xlsx 后缀应使用 openpyxl 引擎."""
        import pandas as pd

        df = pd.DataFrame({"A": [1]})
        with patch("pandas.read_excel", return_value={"S": df}) as mock_read:
            _load_excel(tmp_path / "data.xlsx")
        _, kwargs = mock_read.call_args
        assert kwargs.get("engine") == "openpyxl"

    def test_excel_read_failure_raises_runtime_error(self, tmp_path: pathlib.Path):
        """读取失败应抛出 RuntimeError."""
        with patch("pandas.read_excel", side_effect=Exception("boom")):
            with pytest.raises(RuntimeError, match="Failed to read Excel"):
                _load_excel(tmp_path / "bad.xlsx")


# ---------------------------------------------------------------------------
# load_sources 错误处理
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadSourcesErrorHandling:
    """load_sources 对单文件加载失败应跳过并继续."""

    def test_failing_file_skipped_others_continue(self, tmp_path: pathlib.Path):
        """一个文件加载失败不应阻止其他文件."""
        (tmp_path / "good.md").write_text("# Good\n\ncontent", encoding="utf-8")
        # .pdf 文件触发加载但 PdfReader 抛异常 -> 被 load_sources try/except 捕获
        (tmp_path / "bad.pdf").write_bytes(b"not a real pdf")
        docs = load_sources(tmp_path)
        # good.md 一定被加载; bad.pdf 可能失败但被跳过
        assert any("Good" in d.page_content for d in docs)

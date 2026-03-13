from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from langchain_core.documents import Document


def _build_simple_pdf_bytes(text: str) -> bytes:
    def obj(n: int, body: str) -> bytes:
        return f"{n} 0 obj\n{body}\nendobj\n".encode("utf-8")

    content_stream = f"BT /F1 24 Tf 100 700 Td ({text}) Tj ET"
    stream_obj = f"<< /Length {len(content_stream)} >>\nstream\n{content_stream}\nendstream"

    parts: list[bytes] = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = [0]

    def add(b: bytes) -> None:
        offsets.append(sum(len(p) for p in parts))
        parts.append(b)

    add(obj(1, "<< /Type /Catalog /Pages 2 0 R >>"))
    add(obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))
    add(
        obj(
            3,
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        )
    )
    add(obj(4, stream_obj))
    add(obj(5, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))

    xref_start = sum(len(p) for p in parts)
    xref_lines = ["xref\n0 6\n0000000000 65535 f \n"]
    for i in range(1, 6):
        xref_lines.append(f"{offsets[i]:010d} 00000 n \n")
    xref = "".join(xref_lines).encode("utf-8")

    trailer = (
        "trailer\n<< /Size 6 /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    ).encode("utf-8")

    return b"".join(parts) + xref + trailer


class Week2PdfAndChunkingTest(unittest.TestCase):
    def test_pdf_parsing_supported(self) -> None:
        from riskagent_agenticrag.rag.source_loader import load_sources

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf_path = root / "sample.pdf"
            pdf_path.write_bytes(_build_simple_pdf_bytes("Hello PDF"))

            docs = load_sources(root)
            self.assertTrue(docs)
            pdf_docs = [d for d in docs if str(d.metadata.get("file_type")) == "pdf"]
            self.assertTrue(pdf_docs)
            self.assertEqual(int(pdf_docs[0].metadata.get("page")), 1)
            self.assertIn("Hello", pdf_docs[0].page_content)

    def test_markdown_chunk_has_section_path_and_line_range(self) -> None:
        from riskagent_agenticrag.rag.ingestion import split_documents

        md = "# Title\n\n## Section A\nLine1\nLine2\n\n## Section B\nLine3\n"
        docs = [Document(page_content=md, metadata={"source": "tmp.md", "file_type": "md", "_source_text": md})]
        chunks = split_documents(docs)
        self.assertTrue(chunks)
        self.assertTrue(any(bool(c.metadata.get("section_path")) for c in chunks))
        self.assertTrue(any(isinstance(c.metadata.get("start_line"), int) for c in chunks))
        self.assertTrue(any(isinstance(c.metadata.get("end_line"), int) for c in chunks))


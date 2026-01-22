"""语料加载.

当前支持从 corpus 目录递归读取 markdown 与 pdf 文件.

约定.
- 读取 *.md 与 *.pdf.
- 跳过 README.md, 避免把说明文件当作语料.
- 每个文件会被映射为一个 Document, source 路径写入 metadata.
"""

from __future__ import annotations

import pathlib

from langchain_core.documents import Document


def _load_pdf(path: pathlib.Path) -> list[Document]:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except Exception as e:
        raise RuntimeError("PDF parsing requires pypdf installed") from e

    reader = PdfReader(str(path))
    docs: list[Document] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": str(path),
                    "file_type": "pdf",
                    "page": int(i + 1),
                },
            )
        )
    return docs


def load_sources(sources_dir: pathlib.Path) -> list[Document]:
    # sources_dir 不存在时直接返回空列表, 方便 UI 场景下提示用户补充语料.
    if not sources_dir.exists():
        return []

    docs: list[Document] = []
    for path in sorted(sources_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.lower() == "readme.md":
            continue

        suffix = path.suffix.lower().strip()
        if suffix == ".md":
            text = path.read_text(encoding="utf-8", errors="ignore")
            docs.append(
                Document(
                    page_content=text,
                    metadata={"source": str(path), "file_type": "md", "_source_text": text},
                )
            )
            continue

        if suffix == ".pdf":
            docs.extend(_load_pdf(path))
            continue

    return docs

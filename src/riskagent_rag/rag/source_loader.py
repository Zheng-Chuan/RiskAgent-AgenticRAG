"""语料加载.

当前 MVP 仅支持从 docs/sources 目录递归读取 markdown 文件.

约定.
- 只读取 *.md.
- 跳过 docs/sources/README.md, 避免把说明文件当作语料.
- 每个文件会被映射为一个 Document, source 路径写入 metadata.
"""

from __future__ import annotations

import pathlib

from langchain_core.documents import Document


def load_markdown_sources(sources_dir: pathlib.Path) -> list[Document]:
    # sources_dir 不存在时直接返回空列表, 方便 UI 场景下提示用户补充语料.
    if not sources_dir.exists():
        return []

    docs: list[Document] = []
    for path in sorted(sources_dir.rglob("*.md")):
        # README.md 通常是放置说明, 不参与向量化.
        if path.name.lower() == "readme.md":
            continue

        # 采用 utf-8, 失败时 ignore, 优先保证 ingest 不会因为个别编码问题中断.
        text = path.read_text(encoding="utf-8", errors="ignore")
        docs.append(Document(page_content=text, metadata={"source": str(path)}))

    return docs

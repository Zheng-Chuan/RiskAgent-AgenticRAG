from __future__ import annotations

import pathlib
import sys


def ensure_src_on_path() -> None:
    # 中文注释, unittest 运行时我们也需要直接引用 src 下模块.
    project_root = pathlib.Path(__file__).resolve().parent.parent
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

from __future__ import annotations

import pathlib
import sys

project_root = pathlib.Path(__file__).resolve().parent.parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

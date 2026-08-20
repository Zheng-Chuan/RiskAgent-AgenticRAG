"""Trace 持久化 -- 将每次请求的完整 trace 写入 JSON 文件."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def save_trace(trace_data: dict[str, Any], artifacts_dir: str) -> str:
    """将一次请求的完整 trace 写入 JSON 文件.

    参数:
        trace_data: trace 字典, 包含 nodes, events, retrieval_diag 等
        artifacts_dir: 存储根目录, 实际写入 {artifacts_dir}/traces/

    返回:
        写入的文件路径, 失败时返回空字符串
    """
    try:
        # 确保 traces 子目录存在
        traces_dir = Path(artifacts_dir) / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名: trace_id 优先, 否则用时间戳 + uuid
        trace_id = str(trace_data.get("request_id") or trace_data.get("run_id") or "")
        if not trace_id:
            trace_id = f"{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 添加写入时间戳
        trace_data["_saved_at"] = datetime.now().isoformat()
        trace_data["_trace_id"] = trace_id

        file_path = traces_dir / f"{trace_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, ensure_ascii=False, indent=2, default=str)

        return str(file_path)
    except Exception:
        return ""  # 持久化失败不影响主流程


def cleanup_traces(artifacts_dir: str, retention_days: int = 7) -> int:
    """清理超过保留期的 trace 文件.

    参数:
        artifacts_dir: 存储根目录
        retention_days: 保留天数, 默认 7 天

    返回:
        删除的文件数
    """
    try:
        traces_dir = Path(artifacts_dir) / "traces"
        if not traces_dir.is_dir():
            return 0

        cutoff = time.time() - retention_days * 86400
        deleted = 0

        for trace_file in traces_dir.glob("*.json"):
            try:
                if trace_file.stat().st_mtime < cutoff:
                    trace_file.unlink()
                    deleted += 1
            except OSError:
                pass  # 单个文件删除失败不影响整体

        return deleted
    except Exception:
        return 0

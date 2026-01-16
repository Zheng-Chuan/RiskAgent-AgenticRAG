# 中文注释: artifacts 存储模块, 负责将运行结果持久化到本地文件系统
# 用途: 支持回放, 调试, 回归测试, 问题归因

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def save_artifact(
    request_id: str,
    request_data: dict[str, Any],
    response_data: dict[str, Any],
    structured_response_data: dict[str, Any] | None = None,
    artifacts_dir: str = ".artifacts",
) -> str:
    """
    将单次运行的完整输入输出保存为 JSON 文件.

    参数:
        request_id: 请求唯一标识
        request_data: 请求数据, 包含 question, max_rounds 等
        response_data: 响应数据, 包含 answer, citations, decision_log, tool_traces 等
        artifacts_dir: 存储目录, 默认 .artifacts

    返回:
        保存的文件路径

    设计思路:
        - 文件名格式: {timestamp}_{request_id}.json
        - 包含完整的输入输出, 便于后续回放和调试
        - 使用 ISO8601 时间戳, 便于排序和查找
    """
    artifacts_path = Path(artifacts_dir)
    artifacts_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{request_id}.json"
    filepath = artifacts_path / filename

    artifact = {
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request": request_data,
        "response": response_data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)

    # 中文注释: 将 artifacts 按 bundle 目录落盘, 便于回放和评测.
    # 保持上面的单文件 JSON 兼容现有 tests.
    bundle_dir = artifacts_path / f"{timestamp}_{request_id}"
    try:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        with open(bundle_dir / "request.json", "w", encoding="utf-8") as f:
            json.dump(request_data, f, indent=2, ensure_ascii=False)
        with open(bundle_dir / "response.json", "w", encoding="utf-8") as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)

        # 中文注释: 如果 response_data 或 structured_response_data 能对齐结构化 contract, 则额外输出规范化文件.
        try:
            from riskagent_rag.contracts.structured import parse_structured_response

            candidate = structured_response_data or response_data
            obj = parse_structured_response(candidate)
            if hasattr(obj, "model_dump"):
                payload = obj.model_dump()  # type: ignore[attr-defined]
            else:
                payload = obj.dict()
            with open(bundle_dir / "structured_response.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    except Exception:
        pass

    return str(filepath)


def load_artifact(filepath: str) -> dict[str, Any]:
    """
    从文件加载 artifact.

    参数:
        filepath: artifact 文件路径

    返回:
        artifact 数据字典

    用途:
        - 回放历史运行
        - 回归测试
        - 问题归因
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_artifacts(artifacts_dir: str = ".artifacts") -> list[str]:
    """
    列出所有 artifact 文件.

    参数:
        artifacts_dir: 存储目录

    返回:
        文件路径列表, 按时间倒序排列
    """
    artifacts_path = Path(artifacts_dir)
    if not artifacts_path.exists():
        return []

    files = sorted(
        artifacts_path.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [str(f) for f in files]

"""Mock risk tool for local demo.

中文注释: Week3 先用本地 mock tool 结构跑通.
后续可替换为真实数据源, 但 contract 保持稳定.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional


def monitor_desk_exposure(
    *,
    desk: str,
    as_of: Optional[str] = None,
    abs_delta_limit: float = 1_000_000,
    market_snapshot_url: Optional[str] = None,
) -> dict[str, Any]:
    # 中文注释: 返回结构尽量贴近真实系统, 但保持 deterministic.
    seed = f"{desk}|{as_of or ''}|{abs_delta_limit}".encode("utf-8")
    digest = hashlib.sha1(seed).hexdigest()[:8]

    # 中文注释: 生成一个可重复的 delta 数值.
    signed = int(digest, 16) % 2
    magnitude = (int(digest, 16) % 900_000) + 50_000
    total_delta = float(magnitude if signed == 0 else -magnitude)

    breach = abs(total_delta) > abs_delta_limit
    breaches = (
        [
            {
                "type": "abs_delta_limit",
                "metric": "total_delta",
                "value": total_delta,
                "limit": abs_delta_limit,
            }
        ]
        if breach
        else []
    )

    alerts = (
        [
            {
                "level": "high",
                "message": "delta limit breached",
            }
        ]
        if breach
        else []
    )

    return {
        "desk": desk,
        "as_of": as_of,
        "market_snapshot_url": market_snapshot_url,
        "exposure": {
            "total_delta": total_delta,
        },
        "breaches": breaches,
        "alerts": alerts,
    }

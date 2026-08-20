"""observability 模块单元测试 -- persistence 和 latency 统计."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest


# ===========================================================================
# persistence.py: save_trace
# ===========================================================================

@pytest.mark.unit
def test_save_trace_writes_json_file(tmp_path):
    """save_trace 应将 trace 写入 JSON 文件并返回路径."""
    from riskagent_agenticrag.observability.persistence import save_trace

    trace_data = {"request_id": "req-001", "nodes": [], "events": []}
    result = save_trace(trace_data, str(tmp_path))

    assert result != ""
    assert result.endswith("req-001.json")
    assert Path(result).exists()

    loaded = json.loads(Path(result).read_text(encoding="utf-8"))
    assert loaded["request_id"] == "req-001"
    assert "_saved_at" in loaded
    assert loaded["_trace_id"] == "req-001"


@pytest.mark.unit
def test_save_trace_uses_run_id_when_no_request_id(tmp_path):
    """无 request_id 时应使用 run_id 作为文件名."""
    from riskagent_agenticrag.observability.persistence import save_trace

    trace_data = {"run_id": "run-abc", "nodes": []}
    result = save_trace(trace_data, str(tmp_path))

    assert result.endswith("run-abc.json")
    assert Path(result).exists()


@pytest.mark.unit
def test_save_trace_generates_id_when_no_request_or_run_id(tmp_path):
    """无 request_id 和 run_id 时应生成时间戳+uuid 文件名."""
    from riskagent_agenticrag.observability.persistence import save_trace

    trace_data = {"nodes": []}
    result = save_trace(trace_data, str(tmp_path))

    assert result != ""
    file_name = Path(result).name
    assert not file_name == ".json"
    assert file_name.endswith(".json")
    # 文件名应包含时间戳格式 YYYYMMDDTHHMMSS
    assert "T" in file_name


@pytest.mark.unit
def test_save_trace_creates_traces_subdirectory(tmp_path):
    """save_trace 应在 artifacts_dir 下创建 traces 子目录."""
    from riskagent_agenticrag.observability.persistence import save_trace

    traces_dir = tmp_path / "traces"
    assert not traces_dir.exists()

    save_trace({"request_id": "r1"}, str(tmp_path))
    assert traces_dir.exists()
    assert len(list(traces_dir.glob("*.json"))) == 1


@pytest.mark.unit
def test_save_trace_returns_empty_on_failure(tmp_path):
    """save_trace 在写入失败时应返回空字符串, 不抛异常."""
    from riskagent_agenticrag.observability.persistence import save_trace

    # artifacts_dir 指向一个普通文件 -> mkdir traces 子目录必然 NotADirectoryError
    # (不能用 /nonexistent/... 模拟: root 容器下 mkdir parents=True 会直接创建成功)
    blocker = tmp_path / "blocker.txt"
    blocker.write_text("i am a file", encoding="utf-8")
    result = save_trace({"request_id": "r1"}, str(blocker))
    assert result == ""


# ===========================================================================
# persistence.py: cleanup_traces
# ===========================================================================

@pytest.mark.unit
def test_cleanup_traces_deletes_old_files(tmp_path):
    """cleanup_traces 应删除超过保留期的文件."""
    from riskagent_agenticrag.observability.persistence import cleanup_traces

    traces_dir = tmp_path / "traces"
    traces_dir.mkdir()

    # 创建旧文件 (修改 mtime 为 10 天前)
    old_file = traces_dir / "old.json"
    old_file.write_text("{}", encoding="utf-8")
    old_time = time.time() - 10 * 86400
    os.utime(old_file, (old_time, old_time))

    # 创建新文件
    new_file = traces_dir / "new.json"
    new_file.write_text("{}", encoding="utf-8")

    deleted = cleanup_traces(str(tmp_path), retention_days=7)
    assert deleted == 1
    assert not old_file.exists()
    assert new_file.exists()


@pytest.mark.unit
def test_cleanup_traces_returns_zero_when_no_dir(tmp_path):
    """traces 目录不存在时应返回 0."""
    from riskagent_agenticrag.observability.persistence import cleanup_traces

    deleted = cleanup_traces(str(tmp_path), retention_days=7)
    assert deleted == 0


# ===========================================================================
# latency.py: _percentile
# ===========================================================================

@pytest.mark.unit
def test_percentile_empty_returns_zero():
    """空列表应返回 0.0."""
    from riskagent_agenticrag.observability.latency import _percentile

    assert _percentile([], 50) == 0.0


@pytest.mark.unit
def test_percentile_single_element():
    """单元素列表任何百分位都应返回该元素."""
    from riskagent_agenticrag.observability.latency import _percentile

    assert _percentile([42.0], 50) == 42.0
    assert _percentile([42.0], 95) == 42.0
    assert _percentile([42.0], 99) == 42.0


@pytest.mark.unit
def test_percentile_multiple_elements():
    """多元素列表的 p50 应是中位数."""
    from riskagent_agenticrag.observability.latency import _percentile

    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    p50 = _percentile(values, 50)
    assert p50 == 30.0  # 中位数


# ===========================================================================
# latency.py: _load_traces
# ===========================================================================

@pytest.mark.unit
def test_load_traces_empty_dir(tmp_path):
    """无 traces 目录时应返回空列表."""
    from riskagent_agenticrag.observability.latency import _load_traces

    result = _load_traces(str(tmp_path))
    assert result == []


@pytest.mark.unit
def test_load_traces_skips_corrupted(tmp_path):
    """损坏的 JSON 文件应被跳过."""
    from riskagent_agenticrag.observability.latency import _load_traces

    traces_dir = tmp_path / "traces"
    traces_dir.mkdir()
    (traces_dir / "good.json").write_text('{"nodes": []}', encoding="utf-8")
    (traces_dir / "bad.json").write_text("not valid json {{{", encoding="utf-8")

    result = _load_traces(str(tmp_path))
    assert len(result) == 1
    assert result[0]["nodes"] == []


# ===========================================================================
# latency.py: _extract_query_type
# ===========================================================================

@pytest.mark.unit
def test_extract_query_type_from_self_rag():
    """应从 self_rag 数据中提取 question_type."""
    from riskagent_agenticrag.observability.latency import _extract_query_type

    trace = {
        "nodes": [
            {
                "name": "retrieve_and_critique",
                "result": {
                    "docs": [
                        {"grade": {"question_type": "numeric"}}
                    ]
                },
            }
        ]
    }
    assert _extract_query_type(trace) == "numeric"


@pytest.mark.unit
def test_extract_query_type_from_retrieval_diag():
    """无 self_rag 数据时从 retrieval_diag 推断."""
    from riskagent_agenticrag.observability.latency import _extract_query_type

    trace = {
        "nodes": [],
        "retrieval_diag": {"config": {"reranker_model": "cross-encoder-v1"}},
    }
    assert _extract_query_type(trace) == "reranker=cross-encoder-v1"


@pytest.mark.unit
def test_extract_query_type_default_unknown():
    """无任何线索时返回 unknown."""
    from riskagent_agenticrag.observability.latency import _extract_query_type

    assert _extract_query_type({}) == "unknown"
    assert _extract_query_type({"nodes": []}) == "unknown"


# ===========================================================================
# latency.py: collect_latency_stats
# ===========================================================================

@pytest.mark.unit
def test_collect_latency_stats_empty_dir(tmp_path):
    """空目录应返回空统计."""
    from riskagent_agenticrag.observability.latency import collect_latency_stats

    stats = collect_latency_stats(str(tmp_path))
    assert stats["total_traces"] == 0
    assert stats["by_node"] == {}
    assert stats["by_query_type"] == {}


@pytest.mark.unit
def test_collect_latency_stats_aggregates_by_node(tmp_path):
    """应按节点名称聚合 p50/p95/p99 延迟."""
    from riskagent_agenticrag.observability.latency import collect_latency_stats

    traces_dir = tmp_path / "traces"
    traces_dir.mkdir()

    # 写入两个 trace, 每个包含 rewrite 节点
    for i in range(2):
        trace = {
            "request_id": f"r{i}",
            "nodes": [
                {"name": "rewrite", "latency_ms": 100.0 + i * 50},
                {"name": "synthesize_answer", "latency_ms": 200.0},
            ],
        }
        (traces_dir / f"r{i}.json").write_text(
            json.dumps(trace, ensure_ascii=False), encoding="utf-8"
        )

    stats = collect_latency_stats(str(tmp_path))
    assert stats["total_traces"] == 2
    assert "rewrite" in stats["by_node"]
    assert "synthesize_answer" in stats["by_node"]
    assert stats["by_node"]["rewrite"]["count"] == 2
    assert stats["by_node"]["rewrite"]["min_ms"] == 100.0
    assert stats["by_node"]["rewrite"]["max_ms"] == 150.0


@pytest.mark.unit
def test_collect_latency_stats_by_query_type(tmp_path):
    """应按查询类型聚合端到端延迟."""
    from riskagent_agenticrag.observability.latency import collect_latency_stats

    traces_dir = tmp_path / "traces"
    traces_dir.mkdir()

    # 写入一个带 question_type 的 trace
    trace = {
        "request_id": "r1",
        "nodes": [
            {
                "name": "retrieve_and_critique",
                "latency_ms": 50.0,
                "result": {
                    "docs": [{"grade": {"question_type": "definition"}}]
                },
            },
            {"name": "synthesize_answer", "latency_ms": 30.0},
        ],
    }
    (traces_dir / "r1.json").write_text(
        json.dumps(trace, ensure_ascii=False), encoding="utf-8"
    )

    stats = collect_latency_stats(str(tmp_path))
    assert "definition" in stats["by_query_type"]
    qt_stats = stats["by_query_type"]["definition"]
    assert qt_stats["count"] == 1
    # 端到端延迟 = 50 + 30 = 80
    assert qt_stats["total_latency"]["avg_ms"] == 80.0
    assert "retrieve_and_critique" in qt_stats["by_node"]


@pytest.mark.unit
def test_collect_latency_stats_uses_env_var(tmp_path, monkeypatch):
    """无 artifacts_dir 参数时应从环境变量读取."""
    from riskagent_agenticrag.observability.latency import collect_latency_stats

    monkeypatch.setenv("RISKAGENT_ARTIFACTS_DIR", str(tmp_path))
    stats = collect_latency_stats()
    assert stats["total_traces"] == 0

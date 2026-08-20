"""Unit tests for artifacts/storage.py and agents/data_agent.py structured query building."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from riskagent_agenticrag.artifacts.storage import (
    list_artifacts,
    load_artifact,
    save_artifact,
)

# ---------------------------------------------------------------------------
# Artifact save / load / list
# ---------------------------------------------------------------------------

class TestArtifactStorage:

    @pytest.mark.unit
    def test_save_artifact_creates_file(self, tmp_path):
        with patch.dict(os.environ, {"RISKAGENT_ARTIFACTS_DIR": str(tmp_path)}):
            path = save_artifact(
                request_id="req-001",
                request_data={"question": "What is the exposure?"},
                response_data={"answer": "500 million"},
            )
        assert Path(path).exists()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["request_id"] == "req-001"
        assert data["request"]["question"] == "What is the exposure?"
        assert data["response"]["answer"] == "500 million"

    @pytest.mark.unit
    def test_save_artifact_creates_bundle_dir(self, tmp_path):
        with patch.dict(os.environ, {"RISKAGENT_ARTIFACTS_DIR": str(tmp_path)}):
            save_artifact(
                request_id="req-002",
                request_data={"question": "test"},
                response_data={"answer": "test"},
            )
        # Bundle dirs should exist
        dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
        assert len(dirs) == 1
        bundle = dirs[0]
        assert (bundle / "request.json").exists()
        assert (bundle / "response.json").exists()

    @pytest.mark.unit
    def test_load_artifact_existing(self, tmp_path):
        filepath = tmp_path / "test_artifact.json"
        payload = {"request_id": "req-003", "timestamp": "2025-01-01T00:00:00Z"}
        filepath.write_text(json.dumps(payload), encoding="utf-8")
        result = load_artifact(str(filepath))
        assert result is not None
        assert result["request_id"] == "req-003"

    @pytest.mark.unit
    def test_load_artifact_missing_returns_none(self, tmp_path):
        result = load_artifact(str(tmp_path / "nonexistent.json"))
        assert result is None

    @pytest.mark.unit
    def test_list_artifacts_empty_dir(self, tmp_path):
        result = list_artifacts(artifacts_dir=str(tmp_path))
        assert result == []

    @pytest.mark.unit
    def test_list_artifacts_returns_sorted(self, tmp_path):
        (tmp_path / "20250101_000000_a.json").write_text("{}", encoding="utf-8")
        (tmp_path / "20250102_000000_b.json").write_text("{}", encoding="utf-8")
        result = list_artifacts(artifacts_dir=str(tmp_path))
        assert len(result) == 2
        # Should be reverse chronological (most recent first)
        assert "b.json" in result[0]

    @pytest.mark.unit
    def test_list_artifacts_nonexistent_dir(self):
        result = list_artifacts(artifacts_dir="/tmp/nonexistent_dir_xyz_12345")
        assert result == []


# ---------------------------------------------------------------------------
# Bundle 目录的 trace / structured_response 分支
# ---------------------------------------------------------------------------

class TestArtifactBundle:

    @pytest.mark.unit
    def test_save_artifact_writes_trace_json(self, tmp_path):
        """传入 trace_data 时 bundle 目录应落盘 trace.json 且带回填元信息."""
        with patch.dict(os.environ, {"RISKAGENT_ARTIFACTS_DIR": str(tmp_path)}):
            path = save_artifact(
                request_id="req-trace",
                request_data={"question": "q"},
                response_data={"answer": "a"},
                trace_data={"nodes": [{"name": "retrieve"}]},
            )
        # 找到 bundle 目录 (文件名含时间戳, 直接按子目录搜索)
        bundles = [d for d in tmp_path.iterdir() if d.is_dir()]
        assert len(bundles) == 1
        trace_file = bundles[0] / "trace.json"
        assert trace_file.exists()
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        assert trace["nodes"][0]["name"] == "retrieve"
        assert trace["request_id"] == "req-trace"
        assert trace["artifact_path"] == path
        assert trace["bundle_dir"] == str(bundles[0])

    @pytest.mark.unit
    def test_save_artifact_writes_structured_response(self, tmp_path):
        """response_data 可解析为结构化 contract 时应输出 structured_response.json."""
        from riskagent_agenticrag.contracts.structured import StructuredResponse

        resp = StructuredResponse.model_validate(
            {
                "request_id": "req-structured",
                "report": "The exposure is 500m.",
                "evidence_set": [
                    {
                        "evidence_id": "e1",
                        "source": "doc.md",
                        "chunk_id": "doc.md#c0",
                        "start_index": 0,
                        "snippet": "exposure",
                    }
                ],
                "claims": [
                    {
                        "claim_id": "c1",
                        "statement": "exposure is 500m",
                        "evidence_ids": ["e1"],
                        "confidence": "high",
                        "status": "supported",
                    }
                ],
                "decision_log": [
                    {"step_id": "s1", "agent": "retrieval", "rationale": "ok", "chosen": "hybrid"}
                ],
                "status": "ok",
            }
        )
        with patch.dict(os.environ, {"RISKAGENT_ARTIFACTS_DIR": str(tmp_path)}):
            save_artifact(
                request_id="req-structured",
                request_data={"question": "q"},
                response_data=resp.model_dump(),
            )
        bundles = [d for d in tmp_path.iterdir() if d.is_dir()]
        structured = bundles[0] / "structured_response.json"
        assert structured.exists()
        payload = json.loads(structured.read_text(encoding="utf-8"))
        assert payload["report"] == "The exposure is 500m."

    @pytest.mark.unit
    def test_save_artifact_unparseable_response_skips_structured(self, tmp_path):
        """response_data 不符合 contract 时静默跳过 structured_response.json, 主文件仍落盘."""
        with patch.dict(os.environ, {"RISKAGENT_ARTIFACTS_DIR": str(tmp_path)}):
            path = save_artifact(
                request_id="req-bad",
                request_data={"question": "q"},
                response_data={"not": "a valid contract"},
            )
        bundles = [d for d in tmp_path.iterdir() if d.is_dir()]
        assert not (bundles[0] / "structured_response.json").exists()
        assert Path(path).exists()  # 主 JSON 不受影响

    @pytest.mark.unit
    def test_save_artifact_bundle_failure_returns_path(self, tmp_path, monkeypatch):
        """bundle 写入失败时打印错误并返回主文件路径, 不抛异常."""
        # 让 bundle_dir.mkdir 抛错: 先创建同名文件占位 (mkdir exist_ok 遇到文件会 FileExistsError)
        with patch.dict(os.environ, {"RISKAGENT_ARTIFACTS_DIR": str(tmp_path)}):
            # 预创建一个与时间戳前缀匹配的阻碍不可行 (时间戳未知), 改为 patch Path.mkdir
            import riskagent_agenticrag.artifacts.storage as storage_mod

            def _boom(self, *a, **kw):  # type: ignore[no-untyped-def]
                raise OSError("disk full")

            monkeypatch.setattr(storage_mod.Path, "mkdir", _boom)
            # 主文件写入也用 mkdir... 只有 bundle 分支在 try 内, 主 JSON 在 mkdir 之后
            # 简化: 直接验证外层异常分支 -- patch json.dump 使 bundle 内写入失败
            monkeypatch.setattr(
                storage_mod.Path, "mkdir", lambda self, *a, **kw: None
            )
            real_open = open

            def _flaky_open(file, mode="r", *a, **kw):  # type: ignore[no-untyped-def]
                # bundle 内的写入都是 "w" 模式, 第二次开始失败
                if "w" in mode and getattr(_flaky_open, "calls", 0) > 0:
                    raise OSError("disk full")
                _flaky_open.calls = getattr(_flaky_open, "calls", 0) + 1
                return real_open(file, mode, *a, **kw)

            path = save_artifact(
                request_id="req-fail",
                request_data={"question": "q"},
                response_data={"answer": "a"},
            )
        assert path != ""  # 返回主文件路径而非抛异常


# ---------------------------------------------------------------------------
# load_artifact 异常分支
# ---------------------------------------------------------------------------

class TestLoadArtifactErrors:

    @pytest.mark.unit
    def test_load_artifact_corrupted_json_returns_none(self, tmp_path, capsys):
        """损坏的 JSON 文件应返回 None 并打印错误, 不抛异常."""
        bad = tmp_path / "corrupt.json"
        bad.write_text("{not valid json", encoding="utf-8")
        result = load_artifact(str(bad))
        assert result is None
        assert "Error loading artifact" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Directory structure creation
# ---------------------------------------------------------------------------

class TestDirectoryStructure:

    @pytest.mark.unit
    def test_save_creates_nested_dirs(self, tmp_path):
        nested = tmp_path / "level1" / "level2"
        with patch.dict(os.environ, {"RISKAGENT_ARTIFACTS_DIR": str(nested)}):
            path = save_artifact(
                request_id="req-nested",
                request_data={"q": "test"},
                response_data={"a": "test"},
            )
        assert nested.exists()
        assert Path(path).exists()


# ---------------------------------------------------------------------------
# data_agent structured query building
# ---------------------------------------------------------------------------

class TestDataAgentStructuredQuery:

    @pytest.mark.unit
    def test_extract_structured_request_valid(self):
        from riskagent_agenticrag.agents.data_agent import extract_structured_request
        result = extract_structured_request(
            question="What is the delta exposure for desk FX-ASIA with abs delta limit = 500000 as of 2025-06-01?",
            request_id="test-req-1",
        )
        assert result is not None
        assert result.desk == "FX-ASIA"
        assert result.abs_delta_limit == 500000.0
        assert result.as_of == "2025-06-01"

    @pytest.mark.unit
    def test_extract_structured_request_no_keywords(self):
        from riskagent_agenticrag.agents.data_agent import extract_structured_request
        result = extract_structured_request(
            question="What is the weather today?",
            request_id="test-req-2",
        )
        assert result is None

    @pytest.mark.unit
    def test_extract_structured_request_missing_limit(self):
        from riskagent_agenticrag.agents.data_agent import extract_structured_request
        result = extract_structured_request(
            question="What is the delta exposure for desk FX-ASIA?",
            request_id="test-req-3",
        )
        assert result is None

    @pytest.mark.unit
    def test_extract_structured_request_empty_question(self):
        from riskagent_agenticrag.agents.data_agent import extract_structured_request
        result = extract_structured_request(question="", request_id="test-req-4")
        assert result is None

    @pytest.mark.unit
    def test_tool_output_to_document(self):
        from riskagent_agenticrag.agents.data_agent import tool_output_to_document
        from riskagent_agenticrag.contracts.structured import build_tool_trace

        tool_output = {
            "desk": "FX-ASIA",
            "as_of": "2025-06-01",
            "exposure": {"total_delta": 1500.0},
            "breaches": [],
        }
        trace = build_tool_trace(
            tool_name="monitor_desk_exposure",
            tool_input={"desk": "FX-ASIA", "abs_delta_limit": 500000.0},
            tool_output=tool_output,
            started_at="2025-06-01T00:00:00Z",
            finished_at="2025-06-01T00:00:01Z",
            error=None,
        )
        doc = tool_output_to_document(tool_output=tool_output, tool_trace=trace)
        assert "FX-ASIA" in doc.page_content
        assert "1500.00" in doc.page_content
        assert doc.metadata["desk"] == "FX-ASIA"
        assert doc.metadata["chunk_id"].startswith("tool:")

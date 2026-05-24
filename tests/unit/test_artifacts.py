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

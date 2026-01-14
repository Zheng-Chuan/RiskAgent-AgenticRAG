# 中文注释: artifacts 和 validator 验收测试
# 用途: 验证 artifacts 落盘和 validator gate 功能

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# 中文注释: 确保 src 在 sys.path 中, 便于导入项目模块
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from riskagent_rag.artifacts.storage import save_artifact, load_artifact, list_artifacts  # type: ignore[import-not-found]
from riskagent_rag.validators.gates import (  # type: ignore[import-not-found]
    validate_response,
    evidence_gate,
    numeric_consistency_gate,
    refusal_gate,
)


class ContractArtifactsValidatorTest(unittest.TestCase):
    """artifacts 和 validator 验收测试."""

    def test_artifacts_save_and_load(self):
        """测试 artifacts 落盘和加载功能."""
        with tempfile.TemporaryDirectory() as tmpdir:
            request_id = "test_req_001"
            request_data = {"question": "What is delta?", "max_rounds": 2}
            response_data = {
                "answer": "Delta is a risk metric.",
                "citations": [{"source": "test.md", "chunk_id": "chunk_0"}],
                "status": "ok",
                "failure_reason": None,
            }

            filepath = save_artifact(request_id, request_data, response_data, artifacts_dir=tmpdir)
            self.assertTrue(os.path.exists(filepath))

            loaded = load_artifact(filepath)
            self.assertEqual(loaded["request_id"], request_id)
            self.assertEqual(loaded["request"]["question"], "What is delta?")
            self.assertEqual(loaded["response"]["status"], "ok")

            artifacts = list_artifacts(artifacts_dir=tmpdir)
            self.assertEqual(len(artifacts), 1)
            self.assertIn(request_id, artifacts[0])

    def test_evidence_gate_pass(self):
        """测试 evidence gate 通过场景."""
        claims = [
            {
                "claim_id": "c1",
                "statement": "Delta is positive",
                "evidence_ids": ["ev_0"],
            }
        ]
        evidence_set = [
            {
                "evidence_id": "ev_0",
                "source": "test.md",
                "chunk_id": "chunk_0",
                "text": "Delta is positive",
            }
        ]

        failure = evidence_gate(claims, evidence_set)
        self.assertIsNone(failure)

    def test_evidence_gate_fail_missing_evidence_ids(self):
        """测试 evidence gate 失败场景: claim 缺少 evidence_ids."""
        claims = [
            {
                "claim_id": "c1",
                "statement": "Delta is positive",
                "evidence_ids": [],
            }
        ]
        evidence_set = [
            {
                "evidence_id": "ev_0",
                "source": "test.md",
                "chunk_id": "chunk_0",
                "text": "Delta is positive",
            }
        ]

        failure = evidence_gate(claims, evidence_set)
        self.assertIsNotNone(failure)
        self.assertEqual(failure["category"], "evidence_missing")

    def test_evidence_gate_fail_evidence_not_found(self):
        """测试 evidence gate 失败场景: evidence_id 在 evidence_set 中找不到."""
        claims = [
            {
                "claim_id": "c1",
                "statement": "Delta is positive",
                "evidence_ids": ["ev_999"],
            }
        ]
        evidence_set = [
            {
                "evidence_id": "ev_0",
                "source": "test.md",
                "chunk_id": "chunk_0",
                "text": "Delta is positive",
            }
        ]

        failure = evidence_gate(claims, evidence_set)
        self.assertIsNotNone(failure)
        self.assertEqual(failure["category"], "evidence_not_found")

    def test_numeric_consistency_gate_pass(self):
        """测试 numeric consistency gate 通过场景."""
        report = "The delta is 1000."
        claims = [{"statement": "Delta is 1000"}]
        tool_traces = [{"tool_name": "monitor_desk_exposure", "output": {"delta": 1000}}]

        failure = numeric_consistency_gate(report, claims, tool_traces)
        self.assertIsNone(failure)

    def test_numeric_consistency_gate_fail(self):
        """测试 numeric consistency gate 失败场景: 有数字但没有 tool_traces."""
        report = "The delta is 1000."
        claims = [{"statement": "Delta is 1000"}]
        tool_traces = []

        failure = numeric_consistency_gate(report, claims, tool_traces)
        self.assertIsNotNone(failure)
        self.assertEqual(failure["category"], "numeric_inconsistent")

    def test_refusal_gate_pass(self):
        """测试 refusal gate 通过场景: 有足够的 docs 和 evidence."""
        docs = [{"page_content": "test"}]
        evidence_set = [{"evidence_id": "ev_0"}]
        report = "Delta is a risk metric."

        failure = refusal_gate(docs, evidence_set, report)
        self.assertIsNone(failure)

    def test_refusal_gate_fail_empty_docs(self):
        """测试 refusal gate 失败场景: docs 为空但没有明确拒答."""
        docs = []
        evidence_set = []
        report = "Delta is a risk metric."

        failure = refusal_gate(docs, evidence_set, report)
        self.assertIsNotNone(failure)
        self.assertIn(failure["category"], ["refusal_incomplete", "refusal_unclear"])

    def test_validate_response_integration(self):
        """测试 validate_response 集成场景."""
        report = "I do not know the answer. Please add more documents."
        claims = []
        evidence_set = []
        tool_traces = []
        docs = []

        failure = validate_response(report, claims, evidence_set, tool_traces, docs)
        self.assertIsNone(failure)


if __name__ == "__main__":
    unittest.main()

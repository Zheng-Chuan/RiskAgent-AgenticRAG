from __future__ import annotations

import unittest

from tests.conftest import ensure_src_on_path


# ROADMAP 验收映射表
# Contract
# - 明确输入输出 contract(可执行 schema, v1)
#   - test_contract_and_tool_traces_schema
# - 引入工具调用(本地优先)
#   - test_contract_and_tool_traces_schema


class ContractMilestone1AcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_src_on_path()

    def test_contract_and_tool_traces_schema(self) -> None:
        from riskagent_agenticrag.agents.data_agent import run_data_agent  # type: ignore[import-not-found]
        from riskagent_agenticrag.contracts.structured import StructuredRequest  # type: ignore[import-not-found]

        request = StructuredRequest(
            request_id="test-request-id",
            query="monitor desk exposure",
            as_of="2026-01-12",
            desk="Equity Derivatives",
            abs_delta_limit=1000000,
        )

        tool_output, trace, _failure_reason = run_data_agent(request)

        self.assertIsNotNone(trace)
        self.assertEqual(trace.tool_name, "monitor_desk_exposure")
        self.assertIsInstance(trace.tool_input, dict)
        self.assertIsInstance(trace.tool_output, dict)
        self.assertTrue(trace.started_at, "trace missing started_at")
        self.assertTrue(trace.finished_at, "trace missing finished_at")

        self.assertIsInstance(tool_output, dict)
        self.assertIn("exposure", tool_output)

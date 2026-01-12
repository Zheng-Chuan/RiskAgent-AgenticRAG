from __future__ import annotations

import unittest

from tests.conftest import ensure_src_on_path


# ROADMAP 验收映射表
# Week 3
# - 明确输入输出 contract(可执行 schema, v1)
#   - test_week3_contract_and_tool_traces_schema
# - 引入工具调用(本地优先)
#   - test_week3_contract_and_tool_traces_schema


class Week3Milestone1AcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_src_on_path()

    def test_week3_contract_and_tool_traces_schema(self) -> None:
        from riskagent_rag.contracts.week3 import (  # type: ignore[import-not-found]
            Week3Request,
            parse_week3_response,
        )
        from riskagent_rag.week3.run_week3 import run_week3  # type: ignore[import-not-found]

        request = Week3Request(
            request_id="test-request-id",
            query="monitor desk exposure",
            as_of="2026-01-12",
            desk="Equity Derivatives",
            abs_delta_limit=1000000,
        )

        out_dict = run_week3(request)
        parsed = parse_week3_response(out_dict)

        self.assertEqual(parsed.request_id, "test-request-id")
        self.assertTrue(parsed.tool_traces, "week3 expected non-empty tool_traces")

        trace = parsed.tool_traces[0]
        self.assertEqual(trace.tool_name, "monitor_desk_exposure")
        self.assertIsInstance(trace.tool_input, dict)
        self.assertIsInstance(trace.tool_output, dict)
        self.assertTrue(trace.started_at, "week3 trace missing started_at")
        self.assertTrue(trace.finished_at, "week3 trace missing finished_at")

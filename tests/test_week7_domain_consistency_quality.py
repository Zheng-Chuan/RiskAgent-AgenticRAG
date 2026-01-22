from __future__ import annotations

import unittest

from tests.conftest import ensure_src_on_path


class Week7DomainConsistencyQualityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_src_on_path()

    def test_numeric_consistency_supported(self) -> None:
        from riskagent_rag.evaluation.domain_consistency import try_compute_domain_consistency

        samples = [
            {
                "id": "s1",
                "answer": "The PnL impact is 10.0 and the threshold is 5.",
                "contexts": ["PnL impact is 10.0. The threshold is 5."],
            }
        ]
        out = try_compute_domain_consistency(samples=samples, tolerance=0.001)
        self.assertTrue(out.ok)
        self.assertGreaterEqual(float(out.metrics.get("numeric_consistency_score", 0.0)), 0.99)

    def test_numeric_consistency_unsupported(self) -> None:
        from riskagent_rag.evaluation.domain_consistency import try_compute_domain_consistency

        samples = [
            {
                "id": "s1",
                "answer": "The PnL impact is 10.0.",
                "contexts": ["PnL impact is 8.0."],
            }
        ]
        out = try_compute_domain_consistency(samples=samples, tolerance=0.001)
        self.assertTrue(out.ok)
        self.assertLess(float(out.metrics.get("numeric_consistency_score", 1.0)), 0.5)

    def test_glossary_violation(self) -> None:
        from riskagent_rag.evaluation.domain_consistency import try_compute_domain_consistency

        samples = [
            {
                "id": "s1",
                "answer": "Delta means 差值 between two prices.",
                "contexts": ["Delta is a sensitivity measure."],
            }
        ]
        out = try_compute_domain_consistency(samples=samples)
        self.assertTrue(out.ok)
        self.assertLess(float(out.metrics.get("glossary_consistency_score", 1.0)), 1.0)


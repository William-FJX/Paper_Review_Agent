"""Tests for mechanical citation evaluation."""

import unittest

from paper_agent.evaluation import evaluate_analysis


class EvaluationTest(unittest.TestCase):
    def test_finds_valid_and_invalid_page_citations(self) -> None:
        result = evaluate_analysis(
            "Supported [PDF page 2], repeated [PDF page 2], bad [PDF page 9].",
            page_count=4,
        )

        self.assertEqual(result.cited_pages, (2, 9))
        self.assertEqual(result.invalid_pages, (9,))
        self.assertIn("outside the source PDF", result.warnings[0])

    def test_warns_when_no_citation_exists(self) -> None:
        result = evaluate_analysis("No citations here.", page_count=3)
        self.assertEqual(result.cited_pages, ())
        self.assertIn("No [PDF page N]", result.warnings[0])


if __name__ == "__main__":
    unittest.main()

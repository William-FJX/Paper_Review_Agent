"""Tests for the provider-independent analysis workflow."""

import unittest

from paper_agent.analysis import analyze_paper
from paper_agent.paper_pipeline import PreparedPaper, PreparedPaperPrompt


class AnalysisWorkflowTest(unittest.TestCase):
    def test_analyzes_chunks_then_synthesizes(self) -> None:
        calls = []
        responses = iter(
            [
                "First chunk analysis [PDF page 1].",
                "Second chunk analysis [PDF page 2].",
                "Final synthesized answer [PDF page 1] [PDF page 2].",
            ]
        )

        def fake_generate(prompt: str) -> str:
            calls.append(prompt)
            return next(responses)

        paper = PreparedPaper(
            source_sha256="abc123",
            page_count=2,
            learner_request="Explain the method.",
            prompts=(
                PreparedPaperPrompt(1, 1, 100, "first chunk prompt"),
                PreparedPaperPrompt(2, 2, 100, "second chunk prompt"),
            ),
        )

        result = analyze_paper(paper, fake_generate)

        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0], "first chunk prompt")
        self.assertEqual(calls[1], "second chunk prompt")
        self.assertIn("PDF pages 1", calls[2])
        self.assertIn("PDF pages 2", calls[2])
        self.assertEqual(len(result.chunk_analyses), 2)
        self.assertEqual(
            result.synthesis,
            "Final synthesized answer [PDF page 1] [PDF page 2].",
        )

    def test_rejects_empty_chunk_response(self) -> None:
        paper = PreparedPaper(
            source_sha256="abc123",
            page_count=1,
            learner_request="Explain the method.",
            prompts=(
                PreparedPaperPrompt(1, 1, 100, "chunk prompt"),
            ),
        )

        with self.assertRaisesRegex(ValueError, "empty analysis"):
            analyze_paper(paper, lambda prompt: "   ")


if __name__ == "__main__":
    unittest.main()

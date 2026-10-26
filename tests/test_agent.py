"""Tests for the bounded model-directed tool loop."""

import unittest

from paper_agent.agent import run_agent
from paper_agent.literature import LiteratureWork
from paper_agent.pdf_reader import PageText


class AgentLoopTest(unittest.TestCase):
    def test_model_selects_read_search_and_finish(self) -> None:
        decisions = iter(
            [
                '{"action":"read_pages","arguments":{"start_page":1,"end_page":1}}',
                '{"action":"search_literature","arguments":{"query":"AdamW","limit":2}}',
                '{"action":"finish","answer":"Grounded answer [PDF page 1]."}',
            ]
        )
        model_prompts = []
        searches = []

        def fake_generate(prompt: str) -> str:
            model_prompts.append(prompt)
            return next(decisions)

        def fake_search(query: str, limit: int) -> list[LiteratureWork]:
            searches.append((query, limit))
            return [
                LiteratureWork(
                    openalex_id="W1",
                    title="Decoupled Weight Decay",
                    publication_year=2019,
                    authors=("A. Researcher",),
                    cited_by_count=10,
                    doi=None,
                    url="https://openalex.org/W1",
                )
            ]

        result = run_agent(
            pages=[PageText(1, "Paper evidence.")],
            question="How does the method connect to AdamW?",
            learner_request="Explain for an algebra student.",
            generate=fake_generate,
            search_literature=fake_search,
            max_steps=4,
        )

        self.assertEqual(len(model_prompts), 3)
        self.assertEqual(searches, [("AdamW", 2)])
        self.assertEqual(
            [step.action for step in result.steps],
            ["read_pages", "search_literature", "finish"],
        )
        self.assertIn("[PDF page 1]", result.answer)

    def test_rejects_unknown_action(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown agent action"):
            run_agent(
                pages=[PageText(1, "Evidence")],
                question="Question",
                learner_request="Request",
                generate=lambda prompt: '{"action":"delete_files"}',
                search_literature=lambda query, limit: [],
            )

    def test_requires_reading_before_finish(self) -> None:
        with self.assertRaisesRegex(ValueError, "read at least one PDF page"):
            run_agent(
                pages=[PageText(1, "Evidence")],
                question="Question",
                learner_request="Request",
                generate=lambda prompt: '{"action":"finish","answer":"Too soon"}',
                search_literature=lambda query, limit: [],
            )


if __name__ == "__main__":
    unittest.main()

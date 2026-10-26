"""Tests for private session state, follow-ups, and research ideas."""

import tempfile
import unittest
from pathlib import Path

from paper_agent.analysis import ChunkAnalysis, PaperAnalysis
from paper_agent.conversation import answer_follow_up
from paper_agent.evaluation import evaluate_analysis
from paper_agent.research_ideas import generate_research_ideas
from paper_agent.storage import SessionStore


class StorageAndConversationTest(unittest.TestCase):
    def test_saves_analysis_follow_up_and_ideas(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory))
            analysis = PaperAnalysis(
                chunk_analyses=(ChunkAnalysis(1, 2, "Chunk [PDF page 1]."),),
                synthesis="Synthesis [PDF page 1].",
            )
            evaluation = evaluate_analysis(analysis.synthesis, page_count=2)

            session_id = store.create_analysis_session(
                source_pdf="private/papers/paper.pdf",
                source_sha256="abc123",
                model_provider="fake",
                model_name="fake-model",
                question="What is the method?",
                analysis=analysis,
                evaluation=evaluation,
            )
            answer = answer_follow_up(
                store=store,
                session_id=session_id,
                question="What assumption matters most?",
                profile=None,
                generate=lambda prompt: "The key assumption is X [PDF page 1].",
            )
            ideas = generate_research_ideas(
                store,
                session_id,
                lambda prompt: "Idea with baseline and disconfirming evidence.",
            )
            saved = store.load(session_id)

            self.assertIn("key assumption", answer)
            self.assertEqual(len(saved["turns"]), 2)
            self.assertEqual(saved["research_ideas"], ideas)
            self.assertEqual(saved["source_sha256"], "abc123")
            self.assertEqual(saved["model_name"], "fake-model")
            self.assertTrue(store.report_path(session_id).is_file())
            self.assertEqual(len(store.list_sessions()), 1)


if __name__ == "__main__":
    unittest.main()

"""Persist private reading sessions, reports, and research ideas."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from paper_agent.agent import AgentResult
from paper_agent.analysis import PaperAnalysis
from paper_agent.evaluation import AnalysisEvaluation


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_ROOT = PROJECT_ROOT / "private"


class SessionStore:
    """Store private session state as JSON plus a readable Markdown report."""

    def __init__(self, root: Path = PRIVATE_ROOT) -> None:
        self.root = root
        self.sessions_dir = root / "sessions"
        self.reports_dir = root / "reports"

    def create_analysis_session(
        self,
        source_pdf: str | Path,
        source_sha256: str,
        model_provider: str,
        model_name: str,
        question: str,
        analysis: PaperAnalysis,
        evaluation: AnalysisEvaluation,
    ) -> str:
        """Create a private reading session and return its identifier."""
        session_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
            "source_pdf": str(source_pdf),
            "source_sha256": source_sha256,
            "model_provider": model_provider,
            "model_name": model_name,
            "question": question,
            "chunk_analyses": [
                {
                    "start_page": chunk.start_page,
                    "end_page": chunk.end_page,
                    "text": chunk.text,
                }
                for chunk in analysis.chunk_analyses
            ],
            "synthesis": analysis.synthesis,
            "evaluation": {
                "cited_pages": list(evaluation.cited_pages),
                "invalid_pages": list(evaluation.invalid_pages),
                "warnings": list(evaluation.warnings),
            },
            "turns": [],
            "research_ideas": None,
        }
        self._write_json(self._session_path(session_id), data)
        self._write_report(session_id, data)
        return session_id

    def create_agent_session(
        self,
        source_pdf: str | Path,
        source_sha256: str,
        model_provider: str,
        model_name: str,
        question: str,
        result: AgentResult,
        evaluation: AnalysisEvaluation,
    ) -> str:
        """Save an agent answer and its selected actions as reading history."""
        session_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
            "source_pdf": str(source_pdf),
            "source_sha256": source_sha256,
            "model_provider": model_provider,
            "model_name": model_name,
            "question": question,
            "chunk_analyses": [],
            "agent_steps": [
                {"action": step.action, "summary": step.summary}
                for step in result.steps
            ],
            "synthesis": result.answer,
            "evaluation": {
                "cited_pages": list(evaluation.cited_pages),
                "invalid_pages": list(evaluation.invalid_pages),
                "warnings": list(evaluation.warnings),
            },
            "turns": [],
            "research_ideas": None,
        }
        self._write_json(self._session_path(session_id), data)
        self._write_report(session_id, data)
        return session_id

    def load(self, session_id: str) -> dict[str, object]:
        """Load one private reading session."""
        path = self._session_path(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"Session not found: {session_id}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Session JSON is invalid: {session_id}") from error

        if not isinstance(data, dict):
            raise ValueError(f"Session must contain one JSON object: {session_id}")
        return data

    def append_turns(
        self,
        session_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        """Append one user/assistant exchange to explicit conversation state."""
        data = self.load(session_id)
        turns = data.get("turns")
        if not isinstance(turns, list):
            raise ValueError(f"Session turns are invalid: {session_id}")

        turns.extend(
            [
                {"role": "user", "text": user_text},
                {"role": "assistant", "text": assistant_text},
            ]
        )
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_json(self._session_path(session_id), data)
        self._write_report(session_id, data)

    def save_research_ideas(self, session_id: str, ideas: str) -> None:
        """Save generated research ideas inside an existing session."""
        data = self.load(session_id)
        data["research_ideas"] = ideas
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_json(self._session_path(session_id), data)
        self._write_report(session_id, data)

    def list_sessions(self) -> list[dict[str, object]]:
        """Return lightweight metadata for saved sessions, newest first."""
        if not self.sessions_dir.is_dir():
            return []

        sessions = []
        for path in self.sessions_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                sessions.append(
                    {
                        "session_id": data.get("session_id"),
                        "updated_at": data.get("updated_at"),
                        "source_pdf": data.get("source_pdf"),
                        "question": data.get("question"),
                    }
                )

        return sorted(
            sessions,
            key=lambda item: str(item.get("updated_at", "")),
            reverse=True,
        )

    def report_path(self, session_id: str) -> Path:
        """Return the private Markdown report path for a valid session ID."""
        self._validate_session_id(session_id)
        return self.reports_dir / f"{session_id}.md"

    def _session_path(self, session_id: str) -> Path:
        self._validate_session_id(session_id)
        return self.sessions_dir / f"{session_id}.json"

    @staticmethod
    def _validate_session_id(session_id: str) -> None:
        try:
            parsed = UUID(session_id)
        except ValueError as error:
            raise ValueError(f"Invalid session ID: {session_id}") from error
        if str(parsed) != session_id:
            raise ValueError(f"Invalid session ID: {session_id}")

    @staticmethod
    def _write_json(path: Path, data: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)

    def _write_report(self, session_id: str, data: dict[str, object]) -> None:
        report_path = self.report_path(session_id)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        evaluation = data.get("evaluation", {})
        warnings = evaluation.get("warnings", []) if isinstance(evaluation, dict) else []
        warning_lines = "\n".join(f"- {warning}" for warning in warnings)
        ideas = data.get("research_ideas") or "Not generated yet."
        report = (
            "# Paper Reading Report\n\n"
            f"Session: `{session_id}`\n\n"
            f"Source: `{data.get('source_pdf', '')}`\n\n"
            f"SHA-256: `{data.get('source_sha256', '')}`\n\n"
            f"Model: `{data.get('model_provider', '')}/{data.get('model_name', '')}`\n\n"
            f"## Question\n\n{data.get('question', '')}\n\n"
            f"## Synthesis\n\n{data.get('synthesis', '')}\n\n"
            f"## Mechanical Evaluation\n\n{warning_lines}\n\n"
            f"## Research Ideas\n\n{ideas}\n"
        )
        report_path.write_text(report, encoding="utf-8")

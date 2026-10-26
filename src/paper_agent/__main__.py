"""Command-line interface for the paper-review application."""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from paper_agent.agent import run_agent
from paper_agent.analysis import analyze_paper
from paper_agent.conversation import answer_follow_up
from paper_agent.evaluation import evaluate_analysis
from paper_agent.literature import format_literature_results, search_openalex
from paper_agent.model import get_model_info, get_text_generator
from paper_agent.paper_pipeline import PreparedPaper, prepare_paper
from paper_agent.pdf_reader import compute_sha256, extract_pages
from paper_agent.profile import load_profile
from paper_agent.prompt import build_prompt
from paper_agent.research_ideas import generate_research_ideas
from paper_agent.storage import SessionStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    """Define the application's command-line commands and arguments."""
    parser = argparse.ArgumentParser(prog="paper-agent")
    commands = parser.add_subparsers(dest="command", required=True)

    ask_parser = commands.add_parser("ask", help="Send one question to the model")
    ask_parser.add_argument("question", help="Question to ask")

    prepare_parser = commands.add_parser(
        "prepare-paper",
        help="Prepare local PDF prompts without calling a model",
    )
    prepare_parser.add_argument("pdf_path", type=Path, help="Local PDF path")
    prepare_parser.add_argument("question", help="Paper question to prepare")
    prepare_parser.add_argument(
        "--max-chars",
        type=int,
        default=12_000,
        help="Target maximum extracted characters per chunk",
    )

    analyze_parser = commands.add_parser(
        "analyze-paper",
        help="Analyze a PDF, synthesize results, and save a private session",
    )
    analyze_parser.add_argument("pdf_path", type=Path, help="Local PDF path")
    analyze_parser.add_argument("question", help="Question about the paper")
    analyze_parser.add_argument("--max-chars", type=int, default=12_000)

    follow_up_parser = commands.add_parser(
        "follow-up",
        help="Ask a question using one saved session's explicit state",
    )
    follow_up_parser.add_argument("session_id", help="Saved session UUID")
    follow_up_parser.add_argument("question", help="Follow-up question")

    ideas_parser = commands.add_parser(
        "research-ideas",
        help="Generate testable ideas from one saved analysis",
    )
    ideas_parser.add_argument("session_id", help="Saved session UUID")

    search_parser = commands.add_parser(
        "search-literature",
        help="Search OpenAlex metadata; sends only the search query",
    )
    search_parser.add_argument("query", help="Literature search query")
    search_parser.add_argument("--limit", type=int, default=5)

    agent_parser = commands.add_parser(
        "agent",
        help="Let the model choose bounded PDF-reading and search tools",
    )
    agent_parser.add_argument("pdf_path", type=Path, help="Local PDF path")
    agent_parser.add_argument("question", help="Research question")
    agent_parser.add_argument("--max-steps", type=int, default=8)

    commands.add_parser("history", help="List private saved reading sessions")

    return parser


def _openalex_api_key() -> str | None:
    """Load the optional OpenAlex API key without displaying it."""
    load_dotenv(PROJECT_ROOT / ".env")
    value = os.getenv("OPENALEX_API_KEY", "").strip()
    return value or None


def _print_preparation_summary(paper: PreparedPaper, max_chars: int) -> None:
    """Print safe metadata without displaying private paper text."""
    print(f"Pages extracted: {paper.page_count}")
    print(f"Prompt chunks prepared: {len(paper.prompts)}")

    for number, prepared_prompt in enumerate(paper.prompts, start=1):
        page_range = (
            f"{prepared_prompt.start_page}"
            if prepared_prompt.start_page == prepared_prompt.end_page
            else f"{prepared_prompt.start_page}-{prepared_prompt.end_page}"
        )
        over_limit = (
            " (complete page exceeds target)"
            if prepared_prompt.source_characters > max_chars
            else ""
        )
        print(
            f"Chunk {number}: pages {page_range}; "
            f"source characters: {prepared_prompt.source_characters}"
            f"{over_limit}"
        )


def main() -> None:
    """Run the selected command."""
    arguments = build_parser().parse_args()

    try:
        if arguments.command == "ask":
            profile = load_profile()
            prompt = build_prompt(arguments.question, profile)
            print(get_text_generator()(prompt))
            return

        if arguments.command == "prepare-paper":
            paper = prepare_paper(
                path=arguments.pdf_path,
                question=arguments.question,
                profile=load_profile(),
                max_source_characters=arguments.max_chars,
            )
            _print_preparation_summary(paper, arguments.max_chars)
            print("No model request was made.")
            return

        if arguments.command == "analyze-paper":
            model_info = get_model_info()
            paper = prepare_paper(
                path=arguments.pdf_path,
                question=arguments.question,
                profile=load_profile(),
                max_source_characters=arguments.max_chars,
            )
            analysis = analyze_paper(paper, get_text_generator())
            evaluation = evaluate_analysis(analysis.synthesis, paper.page_count)
            store = SessionStore()
            session_id = store.create_analysis_session(
                source_pdf=arguments.pdf_path,
                source_sha256=paper.source_sha256,
                model_provider=model_info.provider,
                model_name=model_info.model,
                question=arguments.question,
                analysis=analysis,
                evaluation=evaluation,
            )
            print(analysis.synthesis)
            print(f"\nSession: {session_id}")
            print(f"Private report: {store.report_path(session_id)}")
            return

        if arguments.command == "follow-up":
            answer = answer_follow_up(
                store=SessionStore(),
                session_id=arguments.session_id,
                question=arguments.question,
                profile=load_profile(),
                generate=get_text_generator(),
            )
            print(answer)
            return

        if arguments.command == "research-ideas":
            ideas = generate_research_ideas(
                SessionStore(),
                arguments.session_id,
                get_text_generator(),
            )
            print(ideas)
            return

        if arguments.command == "search-literature":
            works = search_openalex(
                query=arguments.query,
                limit=arguments.limit,
                api_key=_openalex_api_key(),
            )
            print(format_literature_results(works))
            return

        if arguments.command == "agent":
            model_info = get_model_info()
            profile = load_profile()
            pages = extract_pages(arguments.pdf_path)
            learner_request = build_prompt(arguments.question, profile)
            api_key = _openalex_api_key()

            def search(query: str, limit: int):
                return search_openalex(query, limit=limit, api_key=api_key)

            result = run_agent(
                pages=pages,
                question=arguments.question,
                learner_request=learner_request,
                generate=get_text_generator(),
                search_literature=search,
                max_steps=arguments.max_steps,
            )
            evaluation = evaluate_analysis(result.answer, len(pages))
            store = SessionStore()
            session_id = store.create_agent_session(
                source_pdf=arguments.pdf_path,
                source_sha256=compute_sha256(arguments.pdf_path),
                model_provider=model_info.provider,
                model_name=model_info.model,
                question=arguments.question,
                result=result,
                evaluation=evaluation,
            )
            for number, step in enumerate(result.steps, start=1):
                print(f"Step {number}: {step.summary}")
            print(f"\n{result.answer}")
            print(f"\nSession: {session_id}")
            return

        if arguments.command == "history":
            sessions = SessionStore().list_sessions()
            if not sessions:
                print("No saved sessions.")
                return
            for session in sessions:
                print(
                    f"{session.get('session_id')} | {session.get('updated_at')} | "
                    f"{session.get('question')}"
                )
            return

    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()

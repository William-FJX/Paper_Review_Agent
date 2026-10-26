"""Prepare a research paper for later model analysis."""

from dataclasses import dataclass
from pathlib import Path

from paper_agent.pdf_reader import chunk_pages, compute_sha256, extract_pages
from paper_agent.prompt import build_paper_prompt, build_prompt


@dataclass(frozen=True)
class PreparedPaperPrompt:
    """One page-ranged prompt prepared without calling a model."""

    start_page: int
    end_page: int
    source_characters: int
    prompt: str


@dataclass(frozen=True)
class PreparedPaper:
    """Summary of all locally prepared prompts for one paper."""

    source_sha256: str
    page_count: int
    learner_request: str
    prompts: tuple[PreparedPaperPrompt, ...]


def prepare_paper(
    path: str | Path,
    question: str,
    profile: dict[str, object] | None,
    max_source_characters: int = 12_000,
) -> PreparedPaper:
    """Extract, chunk, and prepare prompts without making model requests."""
    pages = extract_pages(path)
    chunks = chunk_pages(pages, max_characters=max_source_characters)

    prepared_prompts = []
    for chunk in chunks:
        prepared_prompts.append(
            PreparedPaperPrompt(
                start_page=chunk.start_page,
                end_page=chunk.end_page,
                source_characters=chunk.source_characters,
                prompt=build_paper_prompt(
                    question=question,
                    profile=profile,
                    pages=list(chunk.pages),
                ),
            )
        )

    return PreparedPaper(
        source_sha256=compute_sha256(path),
        page_count=len(pages),
        learner_request=build_prompt(question, profile),
        prompts=tuple(prepared_prompts),
    )

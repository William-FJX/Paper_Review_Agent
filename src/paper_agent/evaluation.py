"""Run mechanical checks on generated paper analyses."""

import re
from dataclasses import dataclass


PAGE_CITATION_PATTERN = re.compile(r"\[PDF page (\d+)\]")


@dataclass(frozen=True)
class AnalysisEvaluation:
    """Citation checks that do not claim factual correctness."""

    cited_pages: tuple[int, ...]
    invalid_pages: tuple[int, ...]
    warnings: tuple[str, ...]


def evaluate_analysis(text: str, page_count: int) -> AnalysisEvaluation:
    """Check whether page citations are present and within the PDF range."""
    if page_count <= 0:
        raise ValueError("Page count must be greater than zero.")

    cited_pages = tuple(
        sorted({int(match) for match in PAGE_CITATION_PATTERN.findall(text)})
    )
    invalid_pages = tuple(
        page for page in cited_pages if page < 1 or page > page_count
    )

    warnings = []
    if not cited_pages:
        warnings.append("No [PDF page N] citations were found.")
    if invalid_pages:
        warnings.append(
            "Citations refer to pages outside the source PDF: "
            + ", ".join(str(page) for page in invalid_pages)
        )
    warnings.append(
        "Citation presence does not prove that a claim is supported or correct."
    )

    return AnalysisEvaluation(
        cited_pages=cited_pages,
        invalid_pages=invalid_pages,
        warnings=tuple(warnings),
    )

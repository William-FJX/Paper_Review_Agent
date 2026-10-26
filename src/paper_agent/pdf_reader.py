"""Inspect local research-paper PDF files."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


@dataclass(frozen=True)
class PageText:
    """Text extracted from one numbered PDF page."""

    page_number: int
    text: str
    warning: str | None = None


@dataclass(frozen=True)
class PageChunk:
    """A size-limited group of complete PDF pages."""

    start_page: int
    end_page: int
    pages: tuple[PageText, ...]
    source_characters: int


def _open_pdf(path: str | Path) -> PdfReader:
    """Validate and open a readable, unencrypted PDF."""
    pdf_path = Path(path)

    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file: {pdf_path}")

    try:
        reader = PdfReader(pdf_path)
    except (PdfReadError, OSError) as error:
        raise ValueError(f"Could not read PDF: {pdf_path}") from error

    if reader.is_encrypted:
        raise ValueError(f"Encrypted PDFs are not supported yet: {pdf_path}")

    return reader


def get_page_count(path: str | Path) -> int:
    """Return the number of pages in a readable, unencrypted PDF."""
    return len(_open_pdf(path).pages)


def compute_sha256(path: str | Path) -> str:
    """Return a stable fingerprint for one local file version."""
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    digest = hashlib.sha256()
    with pdf_path.open("rb") as pdf_file:
        for block in iter(lambda: pdf_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_pages(path: str | Path) -> list[PageText]:
    """Extract text while preserving each PDF page number."""
    reader = _open_pdf(path)
    extracted_pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        warning = None
        if not text.strip():
            warning = "No extractable text found; this page may require OCR."

        extracted_pages.append(
            PageText(
                page_number=page_number,
                text=text,
                warning=warning,
            )
        )

    return extracted_pages


def format_pages(pages: list[PageText]) -> str:
    """Format extracted pages as numbered evidence blocks."""
    if not pages:
        raise ValueError("At least one extracted PDF page is required.")

    page_blocks = []
    for page in pages:
        block_lines = [f"[PDF page {page.page_number}]"]
        if page.warning:
            block_lines.append(f"[Extraction warning: {page.warning}]")

        page_text = page.text.strip() or "[No text extracted from this page.]"
        block_lines.append(page_text)
        page_blocks.append("\n".join(block_lines))

    return "\n\n".join(page_blocks)


def chunk_pages(
    pages: list[PageText],
    max_characters: int = 12_000,
) -> list[PageChunk]:
    """Group complete pages under a target source-character limit."""
    if not pages:
        raise ValueError("At least one extracted PDF page is required.")

    if max_characters <= 0:
        raise ValueError("Maximum chunk characters must be greater than zero.")

    chunks = []
    current_pages = []

    for page in pages:
        candidate_pages = [*current_pages, page]
        candidate_length = len(format_pages(candidate_pages))

        if current_pages and candidate_length > max_characters:
            formatted_chunk = format_pages(current_pages)
            chunks.append(
                PageChunk(
                    start_page=current_pages[0].page_number,
                    end_page=current_pages[-1].page_number,
                    pages=tuple(current_pages),
                    source_characters=len(formatted_chunk),
                )
            )
            current_pages = [page]
        else:
            current_pages.append(page)

    if current_pages:
        formatted_chunk = format_pages(current_pages)
        chunks.append(
            PageChunk(
                start_page=current_pages[0].page_number,
                end_page=current_pages[-1].page_number,
                pages=tuple(current_pages),
                source_characters=len(formatted_chunk),
            )
        )

    return chunks

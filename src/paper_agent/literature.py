"""Search OpenAlex for research-work metadata."""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OPENALEX_WORKS_URL = "https://api.openalex.org/works"
JsonFetcher = Callable[[str], dict[str, object]]


@dataclass(frozen=True)
class LiteratureWork:
    """A small, source-linked subset of OpenAlex work metadata."""

    openalex_id: str
    title: str
    publication_year: int | None
    authors: tuple[str, ...]
    cited_by_count: int
    doi: str | None
    url: str


def _fetch_json(url: str) -> dict[str, object]:
    """Fetch one JSON response with short retries for transient failures."""
    request = Request(
        url,
        headers={"User-Agent": "paper-review-agent/0.1"},
    )

    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            if not isinstance(data, dict):
                raise RuntimeError("OpenAlex returned a non-object JSON response.")
            return data
        except HTTPError as error:
            if error.code == 429 or error.code >= 500:
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
            raise RuntimeError(f"OpenAlex request failed: HTTP {error.code}") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            if attempt < 2:
                time.sleep(2**attempt)
                continue
            raise RuntimeError("OpenAlex request failed after three attempts.") from error

    raise RuntimeError("OpenAlex request failed after three attempts.")


def search_openalex(
    query: str,
    limit: int = 5,
    api_key: str | None = None,
    fetch_json: JsonFetcher = _fetch_json,
) -> list[LiteratureWork]:
    """Search OpenAlex and return normalized work metadata."""
    query = query.strip()
    if not query:
        raise ValueError("Literature search query cannot be empty.")
    if limit < 1 or limit > 20:
        raise ValueError("Literature search limit must be between 1 and 20.")

    parameters = {
        "search": query,
        "per_page": str(limit),
        "select": (
            "id,display_name,publication_year,authorships,cited_by_count,"
            "doi,primary_location"
        ),
    }
    if api_key:
        parameters["api_key"] = api_key

    data = fetch_json(f"{OPENALEX_WORKS_URL}?{urlencode(parameters)}")
    raw_results = data.get("results", [])
    if not isinstance(raw_results, list):
        raise ValueError("OpenAlex response has an invalid results field.")

    works = []
    for raw_work in raw_results:
        if not isinstance(raw_work, dict):
            continue

        openalex_id = str(raw_work.get("id", ""))
        title = str(raw_work.get("display_name", "Untitled work"))
        publication_year = raw_work.get("publication_year")
        if not isinstance(publication_year, int):
            publication_year = None

        authors = []
        raw_authorships = raw_work.get("authorships", [])
        if isinstance(raw_authorships, list):
            for authorship in raw_authorships[:8]:
                if not isinstance(authorship, dict):
                    continue
                author = authorship.get("author", {})
                if isinstance(author, dict) and author.get("display_name"):
                    authors.append(str(author["display_name"]))

        cited_by_count = raw_work.get("cited_by_count", 0)
        if not isinstance(cited_by_count, int):
            cited_by_count = 0

        doi = raw_work.get("doi")
        doi = str(doi) if doi else None
        primary_location = raw_work.get("primary_location", {})
        landing_page = None
        if isinstance(primary_location, dict):
            value = primary_location.get("landing_page_url")
            landing_page = str(value) if value else None

        works.append(
            LiteratureWork(
                openalex_id=openalex_id,
                title=title,
                publication_year=publication_year,
                authors=tuple(authors),
                cited_by_count=cited_by_count,
                doi=doi,
                url=doi or landing_page or openalex_id,
            )
        )

    return works


def format_literature_results(works: list[LiteratureWork]) -> str:
    """Format metadata without claiming relevance or novelty."""
    if not works:
        return "No works were returned by this search."

    lines = [
        "Search metadata only: inspect the linked works before relying on them."
    ]
    for number, work in enumerate(works, start=1):
        authors = ", ".join(work.authors) or "Unknown authors"
        year = work.publication_year or "Unknown year"
        lines.append(
            f"{number}. {work.title} ({year})\n"
            f"   Authors: {authors}\n"
            f"   Cited by: {work.cited_by_count}\n"
            f"   URL: {work.url}"
        )
    return "\n".join(lines)

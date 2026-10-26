"""Tests for normalized OpenAlex search metadata."""

import unittest

from paper_agent.literature import search_openalex


class LiteratureSearchTest(unittest.TestCase):
    def test_parses_fake_openalex_response_without_network(self) -> None:
        requested_urls = []

        def fake_fetch(url: str) -> dict[str, object]:
            requested_urls.append(url)
            return {
                "results": [
                    {
                        "id": "https://openalex.org/W1",
                        "display_name": "A Useful Paper",
                        "publication_year": 2025,
                        "authorships": [
                            {"author": {"display_name": "Ada Example"}}
                        ],
                        "cited_by_count": 7,
                        "doi": "https://doi.org/10.0000/example",
                        "primary_location": None,
                    }
                ]
            }

        works = search_openalex(
            "optimizer geometry",
            limit=3,
            fetch_json=fake_fetch,
        )

        self.assertEqual(len(requested_urls), 1)
        self.assertIn("search=optimizer+geometry", requested_urls[0])
        self.assertEqual(works[0].title, "A Useful Paper")
        self.assertEqual(works[0].authors, ("Ada Example",))
        self.assertEqual(works[0].cited_by_count, 7)


if __name__ == "__main__":
    unittest.main()

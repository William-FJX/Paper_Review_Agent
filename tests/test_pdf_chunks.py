"""Tests for page-preserving chunk construction."""

import unittest

from paper_agent.pdf_reader import PageText, chunk_pages, format_pages


class PdfChunkTest(unittest.TestCase):
    def test_chunks_without_splitting_pages(self) -> None:
        pages = [
            PageText(1, "a" * 20),
            PageText(2, "b" * 20),
            PageText(3, "c" * 20),
        ]

        chunks = chunk_pages(pages, max_characters=45)

        covered = [page.page_number for chunk in chunks for page in chunk.pages]
        self.assertEqual(covered, [1, 2, 3])
        self.assertEqual(chunks[0].start_page, 1)
        self.assertTrue(all(chunk.start_page == chunk.end_page for chunk in chunks))

    def test_preserves_empty_page_warning(self) -> None:
        formatted = format_pages(
            [PageText(4, "", "No extractable text; OCR required.")]
        )
        self.assertIn("[PDF page 4]", formatted)
        self.assertIn("OCR required", formatted)
        self.assertIn("[No text extracted", formatted)


if __name__ == "__main__":
    unittest.main()

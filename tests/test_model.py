"""Tests for explicit model-provider selection."""

import os
import unittest
from unittest.mock import patch

from paper_agent.model import get_text_generator


class ModelSelectionTest(unittest.TestCase):
    def test_rejects_unknown_provider_before_any_request(self) -> None:
        with patch.dict(os.environ, {"MODEL_PROVIDER": "unknown"}):
            with self.assertRaisesRegex(ValueError, "Unsupported MODEL_PROVIDER"):
                get_text_generator()


if __name__ == "__main__":
    unittest.main()

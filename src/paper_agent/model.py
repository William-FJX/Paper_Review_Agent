"""Select a configured text-model provider."""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


TextGenerator = Callable[[str], str]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ModelInfo:
    """Reproducibility metadata for the configured model endpoint."""

    provider: str
    model: str


def get_model_info() -> ModelInfo:
    """Return the configured provider and model without exposing a key."""
    load_dotenv(PROJECT_ROOT / ".env")
    provider = os.getenv("MODEL_PROVIDER", "gemini").strip().lower()

    if provider == "gemini":
        model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
        return ModelInfo(provider=provider, model=model)

    raise ValueError(
        f"Unsupported MODEL_PROVIDER: {provider}. "
        "Implemented providers: gemini."
    )


def get_text_generator() -> TextGenerator:
    """Return the configured provider's text-generation function."""
    model_info = get_model_info()

    if model_info.provider == "gemini":
        from paper_agent.gemini import generate_text

        return generate_text

    raise ValueError(
        f"Unsupported MODEL_PROVIDER: {model_info.provider}. "
        "Implemented providers: gemini."
    )

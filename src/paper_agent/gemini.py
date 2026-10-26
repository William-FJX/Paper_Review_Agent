"""Make one text request to the Gemini API."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


DEFAULT_MODEL = "gemini-3.8-flash"


def generate_text(prompt: str) -> str:
    """Send a prompt to Gemini and return its text response."""
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is empty. Add your key to .env first.")

    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text or ""

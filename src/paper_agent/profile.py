"""Load the optional private learner profile."""

import json
from pathlib import Path


PROFILE_PATH = Path(__file__).resolve().parents[2] / "private" / "profile.json"


def load_profile(path: Path = PROFILE_PATH) -> dict[str, object] | None:
    """Return the learner profile, or None when no profile exists."""
    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as profile_file:
            profile = json.load(profile_file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Profile contains invalid JSON: line {error.lineno}"
        ) from error

    if not isinstance(profile, dict):
        raise ValueError("Profile must contain one JSON object.")

    return profile

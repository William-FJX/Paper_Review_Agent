"""Generate testable research ideas from a saved paper analysis."""

from paper_agent.model import TextGenerator
from paper_agent.storage import SessionStore


def build_research_ideas_prompt(session: dict[str, object]) -> str:
    """Build a cautious prompt for small, falsifiable research ideas."""
    synthesis = str(session.get("synthesis", "")).strip()
    if not synthesis:
        raise ValueError("Saved session has no synthesis to build on.")

    return (
        "Propose three grounded research questions or small experiments based "
        "on the saved paper synthesis below.\n"
        "For each idea include: rationale, smallest useful test, baseline, "
        "measurements, expected result, and evidence that would disconfirm the "
        "idea. Preserve [PDF page N] citations when relying on the paper.\n"
        "Do not claim novelty. These ideas are hypotheses until a literature "
        "search and experiment support them.\n\n"
        f"<saved_synthesis>\n{synthesis}\n</saved_synthesis>"
    )


def generate_research_ideas(
    store: SessionStore,
    session_id: str,
    generate: TextGenerator,
) -> str:
    """Generate ideas and save them in the private session."""
    session = store.load(session_id)
    prompt = build_research_ideas_prompt(session)
    ideas = generate(prompt).strip()
    if not ideas:
        raise ValueError("Model returned no research ideas.")

    store.save_research_ideas(session_id, ideas)
    return ideas

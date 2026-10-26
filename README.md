# Paper Review Agent

A private-by-default Python CLI for learning from research papers. It supports a
fixed analysis pipeline and a separate bounded agent loop so their behavior is
easy to compare.

## What it does

- Loads an optional private learner profile.
- Extracts PDFs page by page and preserves `[PDF page N]` labels.
- Records a SHA-256 fingerprint for the exact source-file version.
- Chunks long papers without splitting page references.
- Builds grounded prompts that separate claims, derivations, experiments,
  interpretations, applications, limitations, and uncertainty.
- Runs provider-independent chunk analysis plus final synthesis.
- Saves reports, evaluations, follow-up turns, and research ideas privately.
- Searches OpenAlex metadata for earlier and later research connections.
- Runs a bounded agent that may choose `read_pages`, `search_literature`, or
  `finish`; it cannot execute shell commands or modify files.

## Architecture

```text
private/profile.json ─┐
                     ├─► prompt construction ─► configured model provider
private/papers/*.pdf ─┤         ▲                         │
                     │         │                         ▼
PDF extraction ─► page chunks ─┘              analysis / tool decision
                                                       │
OpenAlex metadata ◄──── bounded search tool ◄──────────┤
                                                       ▼
                                   private sessions and reports
```

The fixed workflow decides every step in Python. The agent loop is different:
the model selects one action from a small allowlist, Python validates it, and
Python executes only that tool.

## Setup

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

The ignored `.env` currently supports:

```dotenv
MODEL_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
OPENALEX_API_KEY=
```

Gemini is the first implemented adapter. The paper workflows accept a generic
`generate(prompt) -> text` function, so another provider can be added without
rewriting PDF, storage, conversation, or agent logic. Provider keys are not
interchangeable.

## Privacy and external data

Real profiles, PDFs, sessions, reports, and ideas belong under ignored
`private/`. Git ignore rules prevent commits; they do not prevent API requests.

| Command | External communication |
| --- | --- |
| `prepare-paper` | None |
| `history` | None |
| `ask` | Sends the question and optional learner profile to the model provider |
| `analyze-paper` | Sends page-labeled extracted text, question, and optional profile to the model provider |
| `follow-up` | Sends saved synthesis, recent turns, question, and optional profile to the model provider |
| `research-ideas` | Sends the saved synthesis to the model provider |
| `search-literature` | Sends only the search query to OpenAlex |
| `agent` | Sends the question/profile and selected PDF pages or search metadata to the model provider; OpenAlex receives agent-selected search queries |

## Commands

Inspect commands and arguments:

```bash
.venv/bin/paper-agent --help
```

Local PDF preparation, with no model call:

```bash
.venv/bin/paper-agent prepare-paper \
  "private/papers/example.pdf" \
  "Explain the problem, method, assumptions, and limitations."
```

Fixed analysis workflow:

```bash
.venv/bin/paper-agent analyze-paper \
  "private/papers/example.pdf" \
  "Explain the problem, method, assumptions, and limitations."
```

The command prints a synthesis and saves a session UUID. Use it for:

```bash
.venv/bin/paper-agent follow-up SESSION_UUID "Why is that assumption needed?"
.venv/bin/paper-agent research-ideas SESSION_UUID
.venv/bin/paper-agent history
```

Standalone literature metadata search:

```bash
.venv/bin/paper-agent search-literature "optimizer rotational invariance" --limit 5
```

Bounded model-directed agent:

```bash
.venv/bin/paper-agent agent \
  "private/papers/example.pdf" \
  "Connect this method to later optimizer work and identify uncertainty."
```

## Project map

```text
src/paper_agent/
├── __main__.py          CLI commands and explicit side-effect boundaries
├── agent.py             Bounded model-directed read/search/finish loop
├── analysis.py          Provider-independent chunk analysis and synthesis
├── conversation.py      Explicit saved follow-up state
├── evaluation.py        Mechanical page-citation checks
├── gemini.py            Gemini-specific adapter
├── literature.py        OpenAlex search and metadata normalization
├── model.py             Provider selection boundary
├── paper_pipeline.py    Extraction, chunking, and prompt preparation
├── pdf_reader.py        PDF validation, fingerprinting, and page extraction
├── profile.py           Optional private learner-profile loading
├── prompt.py            Grounded prompt construction
├── research_ideas.py    Falsifiable research-idea prompt and persistence
└── storage.py           Private JSON sessions and Markdown reports
```

## Verification

Run all offline tests:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests use fake model and OpenAlex functions. They verify orchestration, tool
boundaries, citation parsing, and persistence without network requests. A test
pass does not prove that a future model response is factually correct.

For a code-oriented explanation of the design, read
[`docs/BUILDING_GUIDE.md`](docs/BUILDING_GUIDE.md).

## Known limitations

- Plain-text PDF extraction can damage equations, tables, figures, columns, and
  reading order. Empty pages are flagged, but nonempty extraction may still be
  wrong and should be checked visually.
- Character chunk limits are not provider token limits.
- Hierarchical synthesis relies on model-generated intermediate analyses and
  may compound errors.
- Citation checks verify syntax and page range only, not claim support.
- OpenAlex search is not exhaustive and cannot establish novelty.
- Only the Gemini model adapter is implemented today; the core is prepared for
  additional explicit adapters.

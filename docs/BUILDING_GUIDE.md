# How to Build and Understand This Agent

This guide explains the reusable ideas behind the project rather than only its
commands.

## 1. Start with transformations, not an agent

Most of the application is ordinary Python:

```text
file path -> PDF pages -> chunks -> prompts -> responses -> saved report
```

Each arrow should be a small function with an explicit input and output. This
makes failures inspectable. Build and test this fixed workflow before allowing
a model to choose actions.

## 2. Python concepts used here

### Functions and return values

A function names one transformation:

```python
pages = extract_pages(path)
```

`path` is the input. `pages` receives the return value. Functions such as
`format_pages()` are nearly pure: the same input produces the same output and
they do not contact external services.

### Type annotations

```python
def get_page_count(path: str | Path) -> int:
```

The input may be a string or `Path`; the output should be an integer. Python
does not automatically enforce these annotations. They document intent and help
editors and type-checking tools find mistakes.

### Dataclasses

```python
@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str
```

A dataclass groups related values and generates its constructor. `frozen=True`
prevents accidental reassignment. This resembles defining a mathematical object
by its named components.

### Lists and tuples

A list is mutable: items can be appended. A tuple is fixed after construction.
The chunker builds a list while working, then stores the finished pages as a
tuple so later code cannot silently change the chunk.

### Exceptions

Exceptions separate successful values from failures:

```python
if not path.exists():
    raise FileNotFoundError(...)
```

The CLI catches expected exceptions and prints concise messages. Unexpected
programming errors are not silently converted into plausible results.

### Dependency injection

The most important provider-independence idea is:

```python
analyze_paper(prepared_paper, generate)
```

The analysis code receives a function with the shape `prompt -> text`. During
tests, `generate` is a fake deterministic function. In real use, it is the
Gemini adapter. An OpenAI, Anthropic, or local-model adapter can implement the
same boundary without changing PDF or storage code.

## 3. Configuration, APIs, and SDKs

- An environment variable is a named value supplied outside source code.
- `.env` is a convenient local file for those values; `python-dotenv` loads it.
- An API is the remote contract: requests go out and responses return.
- An SDK is a Python library that wraps that API in Python functions/classes.
- An API key authenticates one provider. Keys from different providers are not
  interchangeable.

The Gemini SDK is isolated in `gemini.py`. The rest of the application calls a
provider-neutral function selected by `model.py`.

## 4. Grounding a paper analysis

The paper is not placed into one unstructured string. Every extracted block is
labeled:

```text
[PDF page 3]
extracted text...
```

This enables page citations and exposes which evidence was available. It does
not guarantee correctness: PDF extraction may scramble an equation or column.
Visual checking remains necessary for important mathematical claims.

Long papers are grouped at page boundaries. The current limit counts
characters because that is deterministic and provider-independent. Production
systems often add provider-specific token counting later.

## 5. Fixed workflow versus agent loop

The fixed analysis workflow is predetermined:

```text
analyze every chunk -> synthesize -> evaluate -> save
```

The agent loop instead asks the model for a JSON decision:

```json
{"action": "read_pages", "arguments": {"start_page": 1, "end_page": 3}}
```

Python parses and validates the decision, then runs only an allowed tool. The
model cannot invent a `delete_files` tool because unknown actions are rejected.
The loop is also capped by `max_steps`, preventing unlimited autonomous work.

This is actual agent behavior: the model chooses the next action. The tools,
permissions, validation, and stopping rule remain ordinary code.

## 6. Explicit conversation state

Models do not automatically remember prior command invocations. A follow-up is
possible because the application saves:

- the synthesis;
- recent user/assistant turns;
- source identity;
- evaluation warnings.

It then deliberately projects selected state into the next prompt. Durable
history and the model's current context are different things.

## 7. Provenance and evaluation

The SHA-256 fingerprint identifies the exact bytes of the PDF version used.
Page labels connect answers to locations. OpenAlex results retain source links.

The evaluator is intentionally modest. It can check whether `[PDF page N]`
citations exist and whether numbers fall inside the PDF. It cannot determine
whether a sentence is truly supported. Reliable evaluation needs both
mechanical checks and human/source review.

## 8. Research-quality boundaries

Keep these categories separate:

- Paper claim: what the authors state.
- Demonstration: what a proof or experiment actually establishes.
- Interpretation: an explanation inferred from the evidence.
- Hypothesis: a testable possibility not yet demonstrated.

A literature search that finds nothing does not prove novelty. Citation counts
do not prove quality. A plausible model answer does not prove that extraction,
mathematics, or attribution is correct.

## 9. How to add another model provider

1. Create a small adapter module that accepts a prompt and returns text.
2. Read only that provider's environment variables in the adapter.
3. Add an explicit provider case to `get_text_generator()`.
4. Add an offline unit test for selection and response normalization.
5. Document exactly what data the provider receives.

Do not guess the provider from the shape of an API key, and do not send one
provider's credential to another provider.

## 10. Best next experiments

After live credentials are configured:

1. Run one short `ask` request and record the exact model endpoint.
2. Analyze a short paper whose content you know and manually check every page
   citation.
3. Compare fixed workflow output with the bounded agent on the same question.
4. Measure model calls, latency, source pages read, citation errors, and cost.
5. Construct a deliberately misleading PDF sentence and verify that it is
   treated as document data rather than an application command.

These experiments test the system rather than assuming that a successful API
response means the research assistant is reliable.

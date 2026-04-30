# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_auth.py::test_api_key_auth_default_header -v

# Run a test file
uv run pytest tests/test_session.py -v

# Run the tool
uv run saasy start --target ona --url https://api.ona.io --api-key <PAT>
```

`ANTHROPIC_API_KEY` must be set in the environment to run the tool against a live target. Tests do not require it.

## Architecture

SaaSy is a CLI tool with an interactive session loop. The user authenticates to a SaaS target, then Claude and the tester take turns: Claude proposes an API call, the tester approves it, the tool fires the real HTTP request, Claude analyzes the result, and either proposes the next step or enters a conversational chat mode on a notable finding.

### Data flow

```
cli.py → session.run() → [ai.propose_next_step() → user approves → enumeration.execute()] loop
                       → _chat_loop() on finding (ai.chat() ↔ user)
```

### Key types (`models.py`)

- **`Proposal`** — an API call Claude wants to make, plus optional finding metadata (`is_finding`, `finding_title`, `finding_description`). Finding metadata is returned inline on the same proposal rather than as a separate object, because Claude signals findings via the `propose_enumeration_step` tool.
- **`EnumResult`** — a captured request/response pair linked to its `Proposal`.
- **`Finding`** — a notable security issue with a title, description, and an `EnumResult` as evidence.
- **`Session`** — all mutable state for a run: `auth_headers`, `enum_results`, `findings`, and `conversation` (the AI chat history as a list of `{"role", "content"}` dicts).

### AI layer (`ai/`)

`ClaudeProvider` drives two modes:

1. **`propose_next_step(session)`** — uses extended thinking (`budget_tokens=5000`) and forces tool use via `tool_choice={"type": "any"}` with the `propose_enumeration_step` tool. Returns a structured `Proposal`. Setting `is_finding=True` on the returned proposal is how Claude signals a finding mid-enumeration.

2. **`chat(message, session)`** — standard conversational call. Appends user message to `session.conversation` before the API call, appends the assistant reply after. The full conversation history is included in every chat call.

`context.py` builds the system prompt from `Session` state, including the full enumeration history (first 800 chars of each response body).

### Connectors (`connectors/`)

`BaseConnector` has two methods: `describe() -> str` and `seed_proposals() -> list[Proposal]`. Seeded proposals run before Claude is consulted — they bootstrap the session with high-value known endpoints for the platform. `OnaConnector` seeds `/api/v1/user`, `/api/v1/orgs`, and `/api/v1/projects`. `GenericConnector` optionally parses an OpenAPI spec to seed up to 3 GET endpoints.

To add a new connector: subclass `BaseConnector`, implement both methods, add it to the `--target` choices in `cli.py`.

### Session loop (`session.py`)

The loop pops seeded proposals first, then calls `ai.propose_next_step()`. When a proposal has `is_finding=True`, the loop creates a `Finding`, appends it to `sess.findings`, and calls `_chat_loop()`. `_chat_loop` returns `True` to end the session or `False` to continue. After chat exits with `False`, a "Continue?" prompt is shown before resuming enumeration.

### Auth (`auth/`)

`APIKeyAuth` and `BasicAuth` both implement `get_headers() -> dict`. The resulting headers dict is stored flat on `Session.auth_headers` and merged into every request in `enumeration.execute()`. Proposal-level headers override auth headers (proposal is merged last).

### Tests

Tests mock `Prompt.ask` with `side_effect` lists — the order of prompts in the list must exactly match the sequence the session loop will call them. Tests mock `saasy.session.enumeration.execute` and `saasy.session.console` to avoid real HTTP calls and Rich output in tests. Claude API calls have no unit tests; they are validated by smoke testing against a live target.

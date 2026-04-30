# saasy — AI-Powered SaaS Red Team Assistant

**Date:** 2026-04-30  
**Status:** Approved

---

## Overview

saasy is an AI-powered red team assistant for evaluating SaaS applications. It authenticates to a target SaaS instance using real credentials, performs enumeration via live API calls, and uses Claude (AI) to reason about the results from an attacker's mindset — surfacing potential attack paths and discussing them conversationally with the tester.

This is not a compliance checker. It is a proactive attack path development tool designed for security engineers and principal pentesters.

---

## Goals

- Authenticate to any SaaS target using an API key or username+password
- Enumerate the target's attack surface through real API calls
- Use Claude to analyze enumeration results and propose the next step (human approves each)
- Engage the tester in a conversational debrief when a finding warrants investigation
- Ship with Ona as the reference connector implementation
- Provide a generic connector path for any SaaS with an OpenAPI spec

---

## Non-Goals

- Automated exploitation (no payloads sent without tester approval)
- Multi-identity / role-switching (single credential set per session)
- Built-in reporting format (deferred to a future decision)
- Compliance scoring or pass/fail output

---

## Architecture

### Project Structure

```
saasy/
├── saasy/
│   ├── cli.py                  # Entry point — starts session, parses args
│   ├── session.py              # Core session loop — state machine, approval flow
│   ├── auth/
│   │   ├── base.py             # Abstract auth interface
│   │   └── basic.py            # APIKeyAuth + BasicAuth implementations
│   ├── connectors/
│   │   ├── base.py             # Abstract connector — base URL, describe(), seed_proposals()
│   │   └── ona.py              # Ona connector (reference implementation)
│   ├── ai/
│   │   ├── base.py             # Abstract AI provider interface
│   │   ├── claude.py           # Claude implementation (tool use + extended thinking)
│   │   └── context.py          # Builds rolling system prompt from session state
│   ├── enumeration.py          # Executes approved API calls, captures req/res pairs
│   └── models.py               # Dataclasses: Session, EnumResult, Proposal, Finding
├── docs/
│   ├── future_features.md
│   └── superpowers/specs/
├── pyproject.toml
└── README.md
```

---

## Core Session Loop

```
INIT → AUTH → ENUMERATE → [AI_PROPOSE → USER_APPROVE → EXECUTE → AI_ANALYZE] → CHAT ↔ loop
```

1. **INIT** — user provides target, connector type, and credentials via CLI flags
2. **AUTH** — connector authenticates and stores session token/headers
3. **AI_PROPOSE** — Claude analyzes current session state and proposes the next API call (endpoint, method, params, rationale)
4. **USER_APPROVE** — tester sees the proposal and approves, modifies, or skips it
5. **EXECUTE** — `enumeration.py` fires the approved request and captures the full req/res pair
6. **AI_ANALYZE** — Claude receives the result, updates its attack surface model, either proposes the next step or switches to chat mode on a notable finding
7. **CHAT** — conversational mode: tester asks questions, Claude reasons about attack paths, tester decides what to pursue next

---

## Components

### Auth (`auth/`)

- `APIKeyAuth` — injects key as a configurable header (e.g., `Authorization: Token <key>`) or query param
- `BasicAuth` — POSTs to a login endpoint with username+password, stores returned token
- Both implement `get_headers() -> dict`
- Credentials loaded from `~/.saasy/credentials.yaml`

### Connectors (`connectors/`)

- `BaseConnector` — abstract class defining `base_url`, `describe() -> str` (human-readable target description), and `seed_proposals() -> list[Proposal]` (first enumeration steps to suggest)
- `OnaConnector` — Ona-specific implementation; seeds proposals with high-value Ona endpoints:
  - `GET /api/v1/user` — current user profile and permissions
  - `GET /api/v1/orgs` — organizations the user belongs to
  - `GET /api/v1/projects` — projects and visibility settings
  - `GET /api/v1/data/{form_id}` — form submission data
- Generic path: `BaseConnector` with an OpenAPI spec — Claude reasons about which endpoints to target without connector-specific seeding

### AI Layer (`ai/`)

- `BaseAIProvider` — abstract interface with two methods:
  - `propose_next_step(session: Session) -> Proposal`
  - `chat(message: str, session: Session) -> str`
- `ClaudeProvider` — implements both using the Anthropic SDK:
  - Uses **tool use** to return structured proposals (endpoint, method, params, rationale)
  - Uses **extended thinking** for attack path reasoning before responding
- `context.py` — builds the rolling system prompt from session state: target description, credentials type, all enumeration results so far, and findings noted during the session

### Session State (`models.py`)

```python
@dataclass
class Session:
    target_url: str
    connector: BaseConnector
    auth: BaseAuth
    ai: BaseAIProvider
    enum_results: list[EnumResult]   # all captured req/res pairs
    findings: list[Finding]           # notable items flagged by AI
    conversation: list[dict]          # chat history for AI context

@dataclass
class Proposal:
    method: str
    endpoint: str
    params: dict
    rationale: str                    # AI's reasoning for this step

@dataclass
class EnumResult:
    proposal: Proposal
    request: dict                     # full request captured
    response: dict                    # full response captured
    timestamp: str

@dataclass
class Finding:
    title: str
    description: str
    evidence: EnumResult
```

---

## CLI Interface

```bash
# Ona target with PAT
saasy start --target ona --url https://api.ona.io --api-key <PAT>

# Generic target with OpenAPI spec and user+pass
saasy start --target generic --spec openapi.yaml --url https://app.example.com --user admin --pass secret
```

---

## AI Interaction UX

**Proposal mode:**
```
[AI] Enumerated 47 users across 3 organizations. I want to check whether
     project data is scoped per-org or globally accessible.
     
     Proposed: GET /api/v1/projects?owner=<other-org>
     Rationale: Tests whether the PAT can read projects outside the
                authenticated user's organization (IDOR risk).
     
     Approve? [y/n/modify] 
```

**Chat mode (triggered on a notable finding):**
```
[AI] This endpoint returns all user emails without rate limiting and
     appears accessible with any valid PAT regardless of org membership.
     An attacker could enumerate the full user base across all orgs.
     
     Want to explore whether unauthenticated access is also possible,
     or discuss the impact of this finding?
```

---

## Future Features

See `docs/future_features.md`.

Key item: a module to convert SaaS API specs and CLI commands into MCP servers — enabling AI agents to call target SaaS APIs directly as MCP tools.

---

## Dependencies

- `anthropic` — Claude SDK (tool use + extended thinking)
- `httpx` — async HTTP client for API calls
- `click` — CLI framework
- `pyyaml` — credentials config loading
- `rich` — terminal output formatting

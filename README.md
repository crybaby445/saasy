# saasy

An AI-powered SaaS red team assistant. Authenticate to a SaaS target, enumerate its attack surface through live API calls, and work with Claude to develop attack paths — conversationally, from an attacker's mindset.

This is not a compliance scanner. saasy is for security engineers and pentesters who want to think offensively about a SaaS application they have access to.

---

## How it works

1. **Authenticate** — provide an API key or username/password for your target
2. **Enumerate** — Claude proposes API calls to make; you approve each one before it fires
3. **Analyze** — Claude reasons about what it found and suggests the next step
4. **Discuss** — when something interesting surfaces, saasy enters a chat mode so you can explore the finding with Claude before continuing

The loop runs until you quit. Every request and response is captured in the session.

---

## Installation

```bash
git clone https://github.com/crybaby445/saasy
cd saasy
pip install -e .
```

Requires Python 3.11+ and an Anthropic API key.

```bash
export ANTHROPIC_API_KEY=your-key-here
```

---

## Usage

### Ona (reference connector)

```bash
saasy start --target ona --url https://api.ona.io --api-key <your-PAT>
```

### Generic SaaS target with API key

```bash
saasy start --target generic --url https://api.example.com --api-key <key>
```

### Generic SaaS target with OpenAPI spec + credentials

```bash
saasy start --target generic \
  --url https://api.example.com \
  --spec openapi.yaml \
  --user admin \
  --pass secret
```

### Use a specific Claude model

```bash
saasy start --target ona --url https://api.ona.io --api-key <PAT> --model claude-opus-4-7
```

---

## Credentials file

Instead of passing credentials on the command line every time, store them in `~/.saasy/credentials.yaml`:

```yaml
ona:
  api_key: your-pat-here

generic:
  username: admin
  password: secret
```

CLI flags take precedence over the config file.

---

## Session walkthrough

```
╭─ Session Started ─────────────────────────────────────────────╮
│ saasy — Ona — ODK-based data collection SaaS (api.ona.io)     │
│ Target: https://api.ona.io                                     │
╰───────────────────────────────────────────────────────────────╯

╭─ AI Proposal ─────────────────────────────────────────────────╮
│ GET https://api.ona.io/api/v1/user                            │
│                                                               │
│ Rationale: Enumerate current user profile and permissions     │
│ to understand access level                                    │
╰───────────────────────────────────────────────────────────────╯
Approve? [y/n/m/quit] (y): y

Executing...
HTTP 200 — 843 bytes

Consulting AI for next step...

╭─ AI Proposal ─────────────────────────────────────────────────╮
│ GET https://api.ona.io/api/v1/projects                        │
│                                                               │
│ Rationale: List all projects — check visibility settings and  │
│ whether projects outside the user's org are accessible        │
╰───────────────────────────────────────────────────────────────╯
Approve? [y/n/m/quit] (y): y

Executing...
HTTP 200 — 12,450 bytes

╭─ Finding: Cross-Org Project Exposure ─────────────────────────╮
│ The /projects endpoint returns projects across all            │
│ organizations, not scoped to the authenticated user's org.   │
│ An attacker with any valid PAT can enumerate all projects     │
│ on the instance — including those in unrelated orgs.         │
╰───────────────────────────────────────────────────────────────╯

Chat mode — discuss this finding. Type 'next' to continue enumeration.

You: how bad is this? can they read the form data too?
AI: This is a significant access control issue. The exposure here is
    the project metadata — names, visibility, owner orgs. Whether form
    submission data is also accessible depends on the /data/{form_id}
    endpoint. I'd suggest we test that next: take a form ID from a
    project that belongs to a different org and attempt to read its
    submissions with your PAT.

You: next
Continue? [y/quit] (y): y
```

---

## Proposal controls

| Input | Action |
|-------|--------|
| `y` | Approve and execute the proposed API call |
| `n` | Skip this proposal, ask AI for another |
| `m` | Modify the endpoint or method before executing |
| `quit` | End the session |

In chat mode, type `next` or `continue` to return to enumeration.

---

## Writing checks for a new target

saasy ships with a connector for Ona and a generic connector for any SaaS with an OpenAPI spec. To add a new first-class connector, create a file in `saasy/connectors/`:

```python
# saasy/connectors/myapp.py
from .base import BaseConnector
from ..models import Proposal

class MyAppConnector(BaseConnector):
    def describe(self) -> str:
        return f"MyApp SaaS ({self.base_url})"

    def seed_proposals(self) -> list[Proposal]:
        return [
            Proposal(
                method="GET",
                endpoint=f"{self.base_url}/api/users",
                rationale="Enumerate users — check for cross-tenant exposure",
            ),
            Proposal(
                method="GET",
                endpoint=f"{self.base_url}/api/admin/settings",
                rationale="Probe admin endpoint — may be accessible with low-priv token",
            ),
        ]
```

Then wire it into `cli.py` alongside the existing connectors.

---

## Project structure

```
saasy/
├── saasy/
│   ├── cli.py            # Entry point
│   ├── session.py        # Interactive REPL loop
│   ├── enumeration.py    # HTTP executor
│   ├── models.py         # Core dataclasses
│   ├── auth/             # APIKeyAuth, BasicAuth
│   ├── connectors/       # OnaConnector, GenericConnector
│   └── ai/               # ClaudeProvider (tool use + extended thinking)
├── tests/                # 24 tests
└── docs/
    ├── future_features.md
    └── superpowers/specs/
```

---

## Future

See [`docs/future_features.md`](docs/future_features.md) for planned work, including a module to automatically convert SaaS API specs and CLI commands into MCP servers.

---

## Requirements

- Python 3.11+
- `ANTHROPIC_API_KEY` environment variable
- Network access to the target SaaS instance

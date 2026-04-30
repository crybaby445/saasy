# saasy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build saasy — an AI-powered SaaS red team assistant that authenticates to a target, enumerates its API via live calls, and uses Claude to reason about attack paths conversationally with the tester.

**Architecture:** A Python CLI tool with a session-based interactive loop. Claude proposes enumeration steps one at a time using tool use + extended thinking; the tester approves each; the tool fires the real HTTP request; Claude analyzes the result and either proposes the next step or enters a conversational chat on a notable finding. Ona is the reference connector implementation; a generic connector handles any SaaS via OpenAPI spec.

**Tech Stack:** Python 3.11+, `anthropic` SDK (tool use + extended thinking), `httpx` (HTTP), `click` (CLI), `rich` (terminal output), `pyyaml` (config), `pytest` + `respx` (testing)

---

## File Map

| File | Responsibility |
|------|---------------|
| `saasy/models.py` | Dataclasses: `Proposal`, `EnumResult`, `Finding`, `Session` |
| `saasy/auth/base.py` | Abstract `BaseAuth` interface |
| `saasy/auth/basic.py` | `APIKeyAuth` and `BasicAuth` implementations |
| `saasy/connectors/base.py` | Abstract `BaseConnector` interface |
| `saasy/connectors/ona.py` | Ona reference connector |
| `saasy/connectors/generic.py` | Generic connector with optional OpenAPI spec seeding |
| `saasy/enumeration.py` | `execute(proposal, auth_headers) -> EnumResult` |
| `saasy/ai/base.py` | Abstract `BaseAIProvider` interface |
| `saasy/ai/context.py` | Builds rolling system prompt from session state |
| `saasy/ai/claude.py` | Claude implementation (tool use + extended thinking) |
| `saasy/session.py` | Session state machine: propose → approve → execute → analyze → chat |
| `saasy/cli.py` | Click CLI entry point |
| `tests/test_models.py` | Model instantiation tests |
| `tests/test_auth.py` | Auth header generation and login flow tests |
| `tests/test_connectors.py` | Connector describe/seed tests |
| `tests/test_enumeration.py` | HTTP execution tests (respx mocked) |
| `tests/test_ai_context.py` | System prompt generation tests |
| `tests/test_session.py` | Session loop flow tests (mocked AI + mocked enumeration) |

---

## Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `saasy/__init__.py`
- Create: `saasy/auth/__init__.py`
- Create: `saasy/connectors/__init__.py`
- Create: `saasy/ai/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "saasy"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.40.0",
    "httpx>=0.27.0",
    "click>=8.1.0",
    "rich>=13.0.0",
    "pyyaml>=6.0.0",
]

[project.scripts]
saasy = "saasy.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "respx>=0.21.0",
    "pytest-httpx>=0.30.0",
]
```

- [ ] **Step 2: Create package skeleton**

```bash
mkdir -p saasy/auth saasy/connectors saasy/ai tests
touch saasy/__init__.py saasy/auth/__init__.py saasy/connectors/__init__.py saasy/ai/__init__.py
touch tests/__init__.py tests/conftest.py
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -e ".[dev]" 2>/dev/null || pip install anthropic httpx click rich pyyaml pytest respx
```

- [ ] **Step 4: Verify pytest runs**

```bash
pytest --collect-only
```
Expected: `no tests ran` (0 errors)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml saasy/ tests/
git commit -m "feat: initialize saasy project structure"
```

---

## Task 2: Models

**Files:**
- Create: `saasy/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from saasy.models import Proposal, EnumResult, Finding, Session

def test_proposal_defaults():
    p = Proposal(method="GET", endpoint="https://api.example.com/users", rationale="test")
    assert p.params == {}
    assert p.headers == {}
    assert p.body is None
    assert p.is_finding is False
    assert p.finding_title == ""
    assert p.finding_description == ""

def test_enum_result_captures_fields():
    p = Proposal(method="GET", endpoint="https://api.example.com/users", rationale="test")
    r = EnumResult(
        proposal=p,
        request_headers={"Authorization": "Token abc"},
        request_body=None,
        response_status=200,
        response_headers={"content-type": "application/json"},
        response_body='[{"id": 1}]',
    )
    assert r.response_status == 200
    assert r.timestamp != ""

def test_session_defaults():
    s = Session(target_url="https://api.example.com", target_name="example")
    assert s.enum_results == []
    assert s.findings == []
    assert s.conversation == []
    assert s.auth_headers == {}

def test_finding_links_evidence():
    p = Proposal(method="GET", endpoint="https://api.example.com/users", rationale="test")
    r = EnumResult(
        proposal=p, request_headers={}, request_body=None,
        response_status=200, response_headers={}, response_body="[]",
    )
    f = Finding(title="User Enumeration", description="All users exposed", evidence=r)
    assert f.evidence.response_status == 200
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'saasy.models'`

- [ ] **Step 3: Implement models.py**

```python
# saasy/models.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

@dataclass
class Proposal:
    method: str
    endpoint: str
    rationale: str
    params: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    body: Optional[dict] = None
    is_finding: bool = False
    finding_title: str = ""
    finding_description: str = ""

@dataclass
class EnumResult:
    proposal: Proposal
    request_headers: dict
    request_body: Optional[dict]
    response_status: int
    response_headers: dict
    response_body: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

@dataclass
class Finding:
    title: str
    description: str
    evidence: Optional["EnumResult"]

@dataclass
class Session:
    target_url: str
    target_name: str
    connector_description: str = ""
    auth_headers: dict = field(default_factory=dict)
    auth_type: str = "API Key"
    enum_results: list = field(default_factory=list)   # list[EnumResult]
    findings: list = field(default_factory=list)        # list[Finding]
    conversation: list = field(default_factory=list)    # list[dict]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_models.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add saasy/models.py tests/test_models.py
git commit -m "feat: add core datamodels"
```

---

## Task 3: Auth Layer

**Files:**
- Create: `saasy/auth/base.py`
- Create: `saasy/auth/basic.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_auth.py
import pytest
import respx
import httpx
from saasy.auth.basic import APIKeyAuth, BasicAuth

def test_api_key_auth_default_header():
    auth = APIKeyAuth(api_key="abc123")
    headers = auth.get_headers()
    assert headers == {"Authorization": "Token abc123"}

def test_api_key_auth_custom_header():
    auth = APIKeyAuth(api_key="abc123", header_name="X-API-Key", prefix="")
    headers = auth.get_headers()
    assert headers == {"X-API-Key": "abc123"}

def test_api_key_auth_empty_prefix():
    auth = APIKeyAuth(api_key="abc123", prefix="Bearer")
    assert auth.get_headers()["Authorization"] == "Bearer abc123"

@respx.mock
def test_basic_auth_authenticates_and_returns_token():
    respx.post("https://api.example.com/auth/login").mock(
        return_value=httpx.Response(200, json={"token": "tok_xyz"})
    )
    auth = BasicAuth(
        login_url="https://api.example.com/auth/login",
        username="admin",
        password="secret",
    )
    auth.authenticate()
    assert auth.get_headers() == {"Authorization": "Token tok_xyz"}

@respx.mock
def test_basic_auth_custom_token_key():
    respx.post("https://api.example.com/auth/login").mock(
        return_value=httpx.Response(200, json={"access_token": "tok_abc"})
    )
    auth = BasicAuth(
        login_url="https://api.example.com/auth/login",
        username="admin",
        password="secret",
        token_key="access_token",
    )
    auth.authenticate()
    assert auth.get_headers()["Authorization"] == "Token tok_abc"

def test_basic_auth_raises_before_authenticate():
    auth = BasicAuth(
        login_url="https://api.example.com/auth/login",
        username="admin",
        password="secret",
    )
    with pytest.raises(RuntimeError, match="Not authenticated"):
        auth.get_headers()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_auth.py -v
```
Expected: `ModuleNotFoundError: No module named 'saasy.auth.basic'`

- [ ] **Step 3: Implement auth/base.py**

```python
# saasy/auth/base.py
from abc import ABC, abstractmethod

class BaseAuth(ABC):
    @abstractmethod
    def get_headers(self) -> dict:
        pass
```

- [ ] **Step 4: Implement auth/basic.py**

```python
# saasy/auth/basic.py
import httpx
from .base import BaseAuth

class APIKeyAuth(BaseAuth):
    def __init__(self, api_key: str, header_name: str = "Authorization", prefix: str = "Token"):
        self.api_key = api_key
        self.header_name = header_name
        self.prefix = prefix

    def get_headers(self) -> dict:
        value = f"{self.prefix} {self.api_key}".strip() if self.prefix else self.api_key
        return {self.header_name: value}


class BasicAuth(BaseAuth):
    def __init__(self, login_url: str, username: str, password: str, token_key: str = "token"):
        self.login_url = login_url
        self.username = username
        self.password = password
        self.token_key = token_key
        self._token: str | None = None

    def authenticate(self) -> None:
        response = httpx.post(
            self.login_url,
            json={"username": self.username, "password": self.password},
            timeout=30.0,
        )
        response.raise_for_status()
        self._token = response.json()[self.token_key]

    def get_headers(self) -> dict:
        if not self._token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        return {"Authorization": f"Token {self._token}"}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_auth.py -v
```
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add saasy/auth/base.py saasy/auth/basic.py tests/test_auth.py
git commit -m "feat: add API key and basic auth implementations"
```

---

## Task 4: Connectors

**Files:**
- Create: `saasy/connectors/base.py`
- Create: `saasy/connectors/ona.py`
- Create: `saasy/connectors/generic.py`
- Create: `tests/test_connectors.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_connectors.py
import json
import pytest
from pathlib import Path
from saasy.connectors.ona import OnaConnector
from saasy.connectors.generic import GenericConnector

def test_ona_connector_describe():
    conn = OnaConnector(base_url="https://api.ona.io")
    assert "Ona" in conn.describe()

def test_ona_connector_seeds_proposals():
    conn = OnaConnector(base_url="https://api.ona.io")
    proposals = conn.seed_proposals()
    assert len(proposals) >= 3
    endpoints = [p.endpoint for p in proposals]
    assert any("/api/v1/user" in e for e in endpoints)
    assert any("/api/v1/orgs" in e for e in endpoints)
    assert any("/api/v1/projects" in e for e in endpoints)
    for p in proposals:
        assert p.method == "GET"
        assert p.rationale != ""

def test_generic_connector_no_spec():
    conn = GenericConnector(base_url="https://api.example.com")
    assert "api.example.com" in conn.describe()
    assert conn.seed_proposals() == []

def test_generic_connector_seeds_from_openapi_spec(tmp_path):
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {"get": {}, "post": {}},
            "/projects": {"get": {}},
            "/admin/settings": {"get": {}},
        }
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))

    conn = GenericConnector(base_url="https://api.example.com", spec_path=str(spec_file))
    proposals = conn.seed_proposals()
    assert len(proposals) <= 3
    assert all(p.method == "GET" for p in proposals)
    assert all(p.endpoint.startswith("https://api.example.com") for p in proposals)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_connectors.py -v
```
Expected: `ModuleNotFoundError: No module named 'saasy.connectors.ona'`

- [ ] **Step 3: Implement connectors/base.py**

```python
# saasy/connectors/base.py
from abc import ABC, abstractmethod
from ..models import Proposal

class BaseConnector(ABC):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    @abstractmethod
    def describe(self) -> str:
        pass

    @abstractmethod
    def seed_proposals(self) -> list[Proposal]:
        pass
```

- [ ] **Step 4: Implement connectors/ona.py**

```python
# saasy/connectors/ona.py
from .base import BaseConnector
from ..models import Proposal

class OnaConnector(BaseConnector):
    def describe(self) -> str:
        return f"Ona — ODK-based data collection SaaS ({self.base_url})"

    def seed_proposals(self) -> list[Proposal]:
        return [
            Proposal(
                method="GET",
                endpoint=f"{self.base_url}/api/v1/user",
                rationale="Enumerate current user profile and permissions to understand access level",
            ),
            Proposal(
                method="GET",
                endpoint=f"{self.base_url}/api/v1/orgs",
                rationale="List organizations the user belongs to — reveals org membership scope",
            ),
            Proposal(
                method="GET",
                endpoint=f"{self.base_url}/api/v1/projects",
                rationale="List all projects and visibility settings — check for cross-org access",
            ),
        ]
```

- [ ] **Step 5: Implement connectors/generic.py**

```python
# saasy/connectors/generic.py
import json
import yaml
from pathlib import Path
from .base import BaseConnector
from ..models import Proposal

class GenericConnector(BaseConnector):
    def __init__(self, base_url: str, spec_path: str | None = None):
        super().__init__(base_url)
        self._endpoints: list[dict] = []
        if spec_path:
            self._load_spec(spec_path)

    def _load_spec(self, path: str) -> None:
        content = Path(path).read_text()
        if path.endswith((".yaml", ".yml")):
            spec = yaml.safe_load(content)
        else:
            spec = json.loads(content)
        for path_str, methods in spec.get("paths", {}).items():
            for method in methods:
                if method.upper() in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                    self._endpoints.append({"method": method.upper(), "path": path_str})

    def describe(self) -> str:
        suffix = f" ({len(self._endpoints)} endpoints from spec)" if self._endpoints else ""
        return f"Generic SaaS target at {self.base_url}{suffix}"

    def seed_proposals(self) -> list[Proposal]:
        gets = [e for e in self._endpoints if e["method"] == "GET"][:3]
        return [
            Proposal(
                method=e["method"],
                endpoint=f"{self.base_url}{e['path']}",
                rationale=f"Discovered from OpenAPI spec — checking {e['path']}",
            )
            for e in gets
        ]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_connectors.py -v
```
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add saasy/connectors/ tests/test_connectors.py
git commit -m "feat: add Ona and generic SaaS connectors"
```

---

## Task 5: Enumeration Executor

**Files:**
- Create: `saasy/enumeration.py`
- Create: `tests/test_enumeration.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_enumeration.py
import respx
import httpx
import pytest
from saasy.models import Proposal
from saasy import enumeration

@respx.mock
def test_execute_get_captures_response():
    respx.get("https://api.example.com/users").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "email": "a@b.com"}])
    )
    proposal = Proposal(
        method="GET",
        endpoint="https://api.example.com/users",
        rationale="test"
    )
    result = enumeration.execute(proposal, auth_headers={"Authorization": "Token abc"})

    assert result.response_status == 200
    assert '"id"' in result.response_body
    assert result.request_headers["Authorization"] == "Token abc"
    assert result.proposal is proposal
    assert result.timestamp != ""

@respx.mock
def test_execute_merges_proposal_headers():
    respx.get("https://api.example.com/items").mock(
        return_value=httpx.Response(200, json=[])
    )
    proposal = Proposal(
        method="GET",
        endpoint="https://api.example.com/items",
        rationale="test",
        headers={"X-Custom": "value"},
    )
    result = enumeration.execute(proposal, auth_headers={"Authorization": "Token abc"})
    assert result.request_headers["X-Custom"] == "value"
    assert result.request_headers["Authorization"] == "Token abc"

@respx.mock
def test_execute_captures_error_responses():
    respx.get("https://api.example.com/admin").mock(
        return_value=httpx.Response(403, json={"detail": "Forbidden"})
    )
    proposal = Proposal(
        method="GET",
        endpoint="https://api.example.com/admin",
        rationale="test"
    )
    result = enumeration.execute(proposal, auth_headers={})
    assert result.response_status == 403
    assert "Forbidden" in result.response_body
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_enumeration.py -v
```
Expected: `ModuleNotFoundError: No module named 'saasy.enumeration'`

- [ ] **Step 3: Implement enumeration.py**

```python
# saasy/enumeration.py
import httpx
from .models import Proposal, EnumResult

def execute(proposal: Proposal, auth_headers: dict) -> EnumResult:
    headers = {**auth_headers, **proposal.headers}
    with httpx.Client(timeout=30.0) as client:
        response = client.request(
            method=proposal.method,
            url=proposal.endpoint,
            params=proposal.params or None,
            headers=headers,
            json=proposal.body,
        )
    return EnumResult(
        proposal=proposal,
        request_headers=headers,
        request_body=proposal.body,
        response_status=response.status_code,
        response_headers=dict(response.headers),
        response_body=response.text,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_enumeration.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add saasy/enumeration.py tests/test_enumeration.py
git commit -m "feat: add HTTP enumeration executor"
```

---

## Task 6: AI Context Builder

**Files:**
- Create: `saasy/ai/context.py`
- Create: `tests/test_ai_context.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ai_context.py
from saasy.models import Session, Proposal, EnumResult
from saasy.ai.context import build_system_prompt, build_chat_messages

def make_session(**kwargs) -> Session:
    return Session(
        target_url="https://api.ona.io",
        target_name="ona",
        connector_description="Ona — ODK-based data collection SaaS",
        auth_type="API Key",
        **kwargs,
    )

def test_system_prompt_includes_target_info():
    session = make_session()
    prompt = build_system_prompt(session)
    assert "https://api.ona.io" in prompt
    assert "Ona" in prompt
    assert "API Key" in prompt

def test_system_prompt_includes_enum_history():
    p = Proposal(method="GET", endpoint="https://api.ona.io/api/v1/user", rationale="test")
    r = EnumResult(
        proposal=p, request_headers={}, request_body=None,
        response_status=200, response_headers={}, response_body='{"username": "admin"}',
    )
    session = make_session(enum_results=[r])
    prompt = build_system_prompt(session)
    assert "/api/v1/user" in prompt
    assert "200" in prompt

def test_system_prompt_empty_history():
    session = make_session()
    prompt = build_system_prompt(session)
    assert "0" in prompt  # result count

def test_build_chat_messages_returns_conversation():
    session = make_session(conversation=[
        {"role": "user", "content": "what does this mean?"},
        {"role": "assistant", "content": "it means the API is wide open"},
    ])
    messages = build_chat_messages(session)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ai_context.py -v
```
Expected: `ModuleNotFoundError: No module named 'saasy.ai.context'`

- [ ] **Step 3: Implement ai/context.py**

```python
# saasy/ai/context.py
from ..models import Session

_SYSTEM_TEMPLATE = """\
You are a senior penetration tester and red team operator evaluating a SaaS \
application from an attacker's perspective.

Target: {connector_description}
Base URL: {target_url}
Authentication: {auth_type}

Your role:
- Analyze API responses to identify attack surface and potential vulnerabilities
- Think like an attacker: IDOR, broken access control, data exposure, business logic flaws
- Propose the next enumeration step using the propose_enumeration_step tool
- When you identify something exploitable, set is_finding=true and describe the impact clearly

Session state:
- Enumeration steps completed: {result_count}
- Findings noted: {finding_count}

{results_summary}"""

def build_system_prompt(session: Session) -> str:
    results_summary = ""
    if session.enum_results:
        lines = []
        for i, r in enumerate(session.enum_results, 1):
            lines.append(
                f"{i}. {r.proposal.method} {r.proposal.endpoint} → HTTP {r.response_status}\n"
                f"   Response (first 800 chars): {r.response_body[:800]}"
            )
        results_summary = "Enumeration history:\n\n" + "\n\n".join(lines)

    return _SYSTEM_TEMPLATE.format(
        connector_description=session.connector_description,
        target_url=session.target_url,
        auth_type=session.auth_type,
        result_count=len(session.enum_results),
        finding_count=len(session.findings),
        results_summary=results_summary,
    )


def build_chat_messages(session: Session) -> list[dict]:
    return list(session.conversation)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_ai_context.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add saasy/ai/context.py tests/test_ai_context.py
git commit -m "feat: add AI context builder"
```

---

## Task 7: Claude AI Provider

**Files:**
- Create: `saasy/ai/base.py`
- Create: `saasy/ai/claude.py`

No dedicated unit tests for this task — the Claude API requires a live key. Integration is validated end-to-end in Task 9. Add `ANTHROPIC_API_KEY` to your environment before running the full tool.

- [ ] **Step 1: Implement ai/base.py**

```python
# saasy/ai/base.py
from abc import ABC, abstractmethod
from ..models import Session, Proposal

class BaseAIProvider(ABC):
    @abstractmethod
    def propose_next_step(self, session: Session) -> Proposal:
        """Analyze session state and return the next enumeration step to take."""
        pass

    @abstractmethod
    def chat(self, message: str, session: Session) -> str:
        """Respond to a tester message in the context of the current session."""
        pass
```

- [ ] **Step 2: Implement ai/claude.py**

```python
# saasy/ai/claude.py
import anthropic
from .base import BaseAIProvider
from .context import build_system_prompt, build_chat_messages
from ..models import Session, Proposal

_PROPOSE_TOOL = {
    "name": "propose_enumeration_step",
    "description": "Propose the next API call to make during enumeration of the SaaS target",
    "input_schema": {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
            },
            "endpoint": {
                "type": "string",
                "description": "Full URL to call",
            },
            "params": {
                "type": "object",
                "description": "Query parameters to include",
            },
            "body": {
                "type": "object",
                "description": "Request body for POST/PUT/PATCH requests",
            },
            "rationale": {
                "type": "string",
                "description": "Why this step is valuable from an attacker's perspective",
            },
            "is_finding": {
                "type": "boolean",
                "description": "True if the previous result revealed something worth discussing with the tester",
            },
            "finding_title": {
                "type": "string",
                "description": "Short title for the finding (required when is_finding=true)",
            },
            "finding_description": {
                "type": "string",
                "description": "Detailed description of the finding and its impact (required when is_finding=true)",
            },
        },
        "required": ["method", "endpoint", "rationale", "is_finding"],
    },
}


class ClaudeProvider(BaseAIProvider):
    def __init__(self, model: str = "claude-opus-4-7"):
        self.client = anthropic.Anthropic()
        self.model = model

    def propose_next_step(self, session: Session) -> Proposal:
        system = build_system_prompt(session)

        if session.enum_results:
            last = session.enum_results[-1]
            user_content = (
                f"Last result: {last.proposal.method} {last.proposal.endpoint} "
                f"→ HTTP {last.response_status}\n\n"
                f"Response body:\n{last.response_body[:3000]}\n\n"
                f"What should we enumerate next?"
            )
        else:
            user_content = "We've just authenticated. What should we enumerate first?"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            thinking={"type": "enabled", "budget_tokens": 5000},
            system=system,
            tools=[_PROPOSE_TOOL],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": user_content}],
        )

        tool_use = next(b for b in response.content if b.type == "tool_use")
        inp = tool_use.input

        return Proposal(
            method=inp["method"],
            endpoint=inp["endpoint"],
            params=inp.get("params") or {},
            body=inp.get("body"),
            rationale=inp["rationale"],
            is_finding=inp["is_finding"],
            finding_title=inp.get("finding_title", ""),
            finding_description=inp.get("finding_description", ""),
        )

    def chat(self, message: str, session: Session) -> str:
        system = build_system_prompt(session)
        session.conversation.append({"role": "user", "content": message})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=system,
            messages=build_chat_messages(session),
        )

        reply = response.content[0].text
        session.conversation.append({"role": "assistant", "content": reply})
        return reply
```

- [ ] **Step 3: Commit**

```bash
git add saasy/ai/base.py saasy/ai/claude.py
git commit -m "feat: add Claude AI provider with tool use and extended thinking"
```

---

## Task 8: Session Loop

**Files:**
- Create: `saasy/session.py`
- Create: `tests/test_session.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_session.py
from unittest.mock import MagicMock, patch, call
from saasy.models import Session, Proposal, EnumResult, Finding
from saasy.connectors.ona import OnaConnector
from saasy import session as session_module

def make_session() -> Session:
    return Session(
        target_url="https://api.ona.io",
        target_name="ona",
        connector_description="Ona",
        auth_headers={"Authorization": "Token abc"},
    )

def make_enum_result(proposal: Proposal, status: int = 200) -> EnumResult:
    return EnumResult(
        proposal=proposal,
        request_headers={},
        request_body=None,
        response_status=status,
        response_headers={},
        response_body='{"username": "admin"}',
    )

def test_run_approves_and_executes_seeded_proposal():
    sess = make_session()
    connector = OnaConnector(base_url="https://api.ona.io")
    ai = MagicMock()
    first_proposal = connector.seed_proposals()[0]

    with (
        patch("saasy.session.enumeration.execute", return_value=make_enum_result(first_proposal)) as mock_exec,
        patch("saasy.session.Prompt.ask", side_effect=["y", "quit"]),
        patch("saasy.session.console"),
    ):
        ai.propose_next_step.return_value = Proposal(
            method="GET", endpoint="https://api.ona.io/api/v1/orgs",
            rationale="next step", is_finding=False,
        )
        session_module.run(sess, connector, ai)

    mock_exec.assert_called_once()
    assert len(sess.enum_results) == 1

def test_run_skips_proposal_on_n():
    sess = make_session()
    connector = OnaConnector(base_url="https://api.ona.io")
    ai = MagicMock()

    with (
        patch("saasy.session.enumeration.execute") as mock_exec,
        patch("saasy.session.Prompt.ask", side_effect=["n", "quit"]),
        patch("saasy.session.console"),
    ):
        session_module.run(sess, connector, ai)

    mock_exec.assert_not_called()

def test_finding_triggers_chat_mode():
    sess = make_session()
    connector = MagicMock()
    connector.seed_proposals.return_value = []
    ai = MagicMock()

    finding_proposal = Proposal(
        method="GET", endpoint="https://api.ona.io/api/v1/users",
        rationale="check", is_finding=True,
        finding_title="User Enumeration", finding_description="All users exposed",
    )
    ai.propose_next_step.return_value = finding_proposal
    ai.chat.return_value = "This is a serious finding."

    with (
        patch("saasy.session.Prompt.ask", side_effect=["what does this mean?", "next", "quit"]),
        patch("saasy.session.console"),
    ):
        session_module.run(sess, connector, ai)

    ai.chat.assert_called_once_with("what does this mean?", sess)
    assert len(sess.findings) == 1
    assert sess.findings[0].title == "User Enumeration"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_session.py -v
```
Expected: `ModuleNotFoundError: No module named 'saasy.session'`

- [ ] **Step 3: Implement session.py**

```python
# saasy/session.py
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from .models import Session, Finding
from .connectors.base import BaseConnector
from .ai.base import BaseAIProvider
from . import enumeration

console = Console()


def run(sess: Session, connector: BaseConnector, ai: BaseAIProvider) -> None:
    console.print(Panel.fit(
        f"[bold green]saasy[/bold green] — {connector.describe()}\n"
        f"Target: {sess.target_url}",
        title="Session Started",
    ))

    pending = list(connector.seed_proposals())

    while True:
        if pending:
            proposal = pending.pop(0)
        else:
            console.print("\n[dim]Consulting AI for next step...[/dim]")
            proposal = ai.propose_next_step(sess)

        if proposal.is_finding and proposal.finding_title:
            finding = Finding(
                title=proposal.finding_title,
                description=proposal.finding_description,
                evidence=sess.enum_results[-1] if sess.enum_results else None,
            )
            sess.findings.append(finding)
            console.print(Panel(
                f"[bold]{finding.description}[/bold]",
                title=f"[red]Finding: {finding.title}[/red]",
                border_style="red",
            ))
            _chat_loop(sess, ai)
            continue

        console.print(Panel(
            f"[bold]{proposal.method}[/bold] {proposal.endpoint}\n\n"
            f"[dim]Rationale:[/dim] {proposal.rationale}",
            title="AI Proposal",
        ))

        choice = Prompt.ask("Approve?", choices=["y", "n", "m", "quit"], default="y")

        if choice == "quit":
            console.print("[yellow]Session ended.[/yellow]")
            break
        elif choice == "n":
            continue
        elif choice == "m":
            proposal.endpoint = Prompt.ask("Endpoint", default=proposal.endpoint)
            proposal.method = Prompt.ask("Method", default=proposal.method)

        console.print("[dim]Executing...[/dim]")
        result = enumeration.execute(proposal, sess.auth_headers)
        sess.enum_results.append(result)

        status_color = "green" if result.response_status < 400 else "red"
        console.print(
            f"[{status_color}]HTTP {result.response_status}[/{status_color}] — "
            f"{len(result.response_body)} bytes"
        )


def _chat_loop(sess: Session, ai: BaseAIProvider) -> None:
    console.print(
        "\n[bold]Chat mode[/bold] — discuss this finding. "
        "Type [bold]'next'[/bold] to continue enumeration.\n"
    )
    while True:
        message = Prompt.ask("[cyan]You[/cyan]")
        if message.lower() in ("next", "continue", "exit", "quit"):
            break
        reply = ai.chat(message, sess)
        console.print(f"\n[green]AI:[/green] {reply}\n")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_session.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add saasy/session.py tests/test_session.py
git commit -m "feat: add interactive session loop with AI proposal and chat mode"
```

---

## Task 9: CLI Entry Point

**Files:**
- Create: `saasy/cli.py`

- [ ] **Step 1: Implement cli.py**

```python
# saasy/cli.py
import click
import yaml
from pathlib import Path
from .models import Session
from .auth.basic import APIKeyAuth, BasicAuth
from .connectors.ona import OnaConnector
from .connectors.generic import GenericConnector
from .ai.claude import ClaudeProvider
from . import session as session_module

_CONFIG_PATH = Path.home() / ".saasy" / "credentials.yaml"


def _load_config(target: str) -> dict:
    if _CONFIG_PATH.exists():
        data = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
        return data.get(target, {})
    return {}


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option("--target", required=True, type=click.Choice(["ona", "generic"]),
              help="SaaS connector to use")
@click.option("--url", required=True, help="Target base URL (e.g. https://api.ona.io)")
@click.option("--api-key", default=None, help="API key / PAT for authentication")
@click.option("--user", default=None, help="Username for user+pass authentication")
@click.option("--pass", "password", default=None, help="Password for user+pass authentication")
@click.option("--spec", default=None, help="Path to OpenAPI spec file (generic target only)")
@click.option("--model", default="claude-opus-4-7", help="Claude model to use")
def start(target: str, url: str, api_key: str | None, user: str | None,
          password: str | None, spec: str | None, model: str) -> None:
    """Start an interactive red team session against a SaaS target."""
    config = _load_config(target)
    api_key = api_key or config.get("api_key")
    user = user or config.get("username")
    password = password or config.get("password")

    if api_key:
        auth = APIKeyAuth(api_key=api_key)
        auth_type = "API Key"
    elif user and password:
        login_url = f"{url.rstrip('/')}/api/v1/profiles/"
        auth = BasicAuth(login_url=login_url, username=user, password=password)
        click.echo("Authenticating...")
        auth.authenticate()
        auth_type = "Username/Password"
    else:
        raise click.UsageError("Provide --api-key or both --user and --pass")

    if target == "ona":
        connector = OnaConnector(base_url=url)
    else:
        connector = GenericConnector(base_url=url, spec_path=spec)

    ai = ClaudeProvider(model=model)

    sess = Session(
        target_url=url,
        target_name=target,
        connector_description=connector.describe(),
        auth_headers=auth.get_headers(),
        auth_type=auth_type,
    )

    session_module.run(sess, connector, ai)


def main() -> None:
    cli()
```

- [ ] **Step 2: Verify CLI is importable**

```bash
python -c "from saasy.cli import main; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Verify help text renders**

```bash
python -m saasy.cli start --help
```
Expected: help text showing `--target`, `--url`, `--api-key`, `--user`, `--pass`, `--spec`, `--model`

- [ ] **Step 4: Run full test suite**

```bash
pytest -v
```
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add saasy/cli.py
git commit -m "feat: add CLI entry point"
```

---

## Task 10: Smoke Test with Ona

> Requires `ANTHROPIC_API_KEY` set and a valid Ona PAT.

- [ ] **Step 1: Set environment and run**

```bash
export ANTHROPIC_API_KEY=<your-key>
saasy start --target ona --url https://api.ona.io --api-key <your-PAT>
```

Expected flow:
1. Session banner appears with Ona connector description
2. First seeded proposal shown: `GET https://api.ona.io/api/v1/user`
3. Approve with `y` — HTTP 200 response displayed
4. AI proposes next step based on response
5. Continue until AI enters chat mode on a finding, or type `quit`

- [ ] **Step 2: Commit any fixes found during smoke test**

```bash
git add -p
git commit -m "fix: smoke test corrections"
```

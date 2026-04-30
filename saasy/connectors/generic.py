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

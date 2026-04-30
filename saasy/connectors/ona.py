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

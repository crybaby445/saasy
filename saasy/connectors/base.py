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

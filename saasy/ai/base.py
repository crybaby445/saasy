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

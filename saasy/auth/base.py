from abc import ABC, abstractmethod

class BaseAuth(ABC):
    @abstractmethod
    def get_headers(self) -> dict:
        pass

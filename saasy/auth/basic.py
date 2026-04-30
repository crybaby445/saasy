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

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

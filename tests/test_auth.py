"""
Tests for /auth/* endpoints — registration, login, forgot/reset password.
"""

import importlib
import sys
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers — reload auth_service between tests so the in-memory store is fresh
# ---------------------------------------------------------------------------

def _fresh_client():
    """Import main with a clean auth_service state."""
    # Remove cached modules so the in-memory dicts start empty
    for mod in list(sys.modules.keys()):
        if "auth_service" in mod or "main" in mod:
            del sys.modules[mod]
    from main import app  # re-import after clearing cache
    return TestClient(app)


@pytest.fixture(autouse=True)
def fresh_auth():
    """Reload auth_service before every test."""
    for mod in list(sys.modules.keys()):
        if "auth_service" in mod:
            del sys.modules[mod]
    # Re-import auth_service in the already-loaded main module
    import services.auth_service as auth_svc
    auth_svc._USERS.clear()
    auth_svc._RESET_TOKENS.clear()
    yield
    auth_svc._USERS.clear()
    auth_svc._RESET_TOKENS.clear()


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/auth/register", json={
            "email": "artist@example.com",
            "password": "securepassword",
            "name": "Test Artist",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["user"]["email"] == "artist@example.com"
        assert data["user"]["name"] == "Test Artist"

    def test_register_name_defaults_to_email_local_part(self, client):
        resp = client.post("/auth/register", json={
            "email": "noname@example.com",
            "password": "securepassword",
            "name": "",
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["name"] == "noname"

    def test_register_duplicate_email(self, client):
        payload = {"email": "dup@example.com", "password": "securepassword", "name": "A"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_register_invalid_email(self, client):
        resp = client.post("/auth/register", json={
            "email": "notanemail",
            "password": "securepassword",
            "name": "A",
        })
        assert resp.status_code == 400

    def test_register_short_password(self, client):
        resp = client.post("/auth/register", json={
            "email": "ok@example.com",
            "password": "short",
            "name": "A",
        })
        assert resp.status_code == 400
        assert "8 characters" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    def _register(self, client):
        client.post("/auth/register", json={
            "email": "user@example.com",
            "password": "password123",
            "name": "User",
        })

    def test_login_success(self, client):
        self._register(client)
        resp = client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "token" in data
        assert data["user"]["email"] == "user@example.com"

    def test_login_wrong_password(self, client):
        self._register(client)
        resp = client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        assert "Invalid" in resp.json()["detail"]

    def test_login_unknown_email(self, client):
        resp = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "anything",
        })
        assert resp.status_code == 401

    def test_login_email_case_insensitive(self, client):
        self._register(client)
        resp = client.post("/auth/login", json={
            "email": "USER@EXAMPLE.COM",
            "password": "password123",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Forgot / Reset password
# ---------------------------------------------------------------------------

class TestForgotReset:
    def _setup(self, client):
        client.post("/auth/register", json={
            "email": "reset@example.com",
            "password": "oldpassword",
            "name": "Reset",
        })

    def test_forgot_unknown_email_still_succeeds(self, client):
        """Always returns success to prevent email enumeration."""
        resp = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_forgot_returns_reset_token(self, client):
        self._setup(client)
        resp = client.post("/auth/forgot-password", json={"email": "reset@example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert "reset_token" in data
        assert len(data["reset_token"]) > 10

    def test_reset_success(self, client):
        self._setup(client)
        token_resp = client.post("/auth/forgot-password", json={"email": "reset@example.com"})
        reset_token = token_resp.json()["reset_token"]

        resp = client.post("/auth/reset-password", json={
            "token": reset_token,
            "new_password": "newpassword123",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Old password should no longer work
        bad = client.post("/auth/login", json={
            "email": "reset@example.com",
            "password": "oldpassword",
        })
        assert bad.status_code == 401

        # New password should work
        good = client.post("/auth/login", json={
            "email": "reset@example.com",
            "password": "newpassword123",
        })
        assert good.status_code == 200

    def test_reset_invalid_token(self, client):
        resp = client.post("/auth/reset-password", json={
            "token": "invalid-token",
            "new_password": "newpassword123",
        })
        assert resp.status_code == 400
        assert "expired or is invalid" in resp.json()["detail"]

    def test_reset_token_can_only_be_used_once(self, client):
        self._setup(client)
        token_resp = client.post("/auth/forgot-password", json={"email": "reset@example.com"})
        reset_token = token_resp.json()["reset_token"]

        client.post("/auth/reset-password", json={
            "token": reset_token,
            "new_password": "newpassword123",
        })
        # Second use should fail
        resp = client.post("/auth/reset-password", json={
            "token": reset_token,
            "new_password": "anotherpassword",
        })
        assert resp.status_code == 400

    def test_reset_short_password(self, client):
        self._setup(client)
        token_resp = client.post("/auth/forgot-password", json={"email": "reset@example.com"})
        reset_token = token_resp.json()["reset_token"]
        resp = client.post("/auth/reset-password", json={
            "token": reset_token,
            "new_password": "short",
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------

class TestMe:
    def test_me_valid_token(self, client):
        client.post("/auth/register", json={
            "email": "me@example.com",
            "password": "password123",
            "name": "Me",
        })
        login_resp = client.post("/auth/login", json={
            "email": "me@example.com",
            "password": "password123",
        })
        token = login_resp.json()["token"]
        resp = client.get(f"/auth/me?token={token}")
        assert resp.status_code == 200
        assert resp.json()["email"] == "me@example.com"

    def test_me_invalid_token(self, client):
        resp = client.get("/auth/me?token=bogus")
        assert resp.status_code == 401

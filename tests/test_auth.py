"""
Tests for /auth/* endpoints — registration, login, forgot/reset password.
"""

import importlib
import sys
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers — clear auth_service state between tests
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
    """Clear auth_service state before (and after) every test.

    We clear the module that *main* actually holds a reference to rather than
    a freshly re-imported copy, so that endpoint handlers pick up the clean slate.
    """
    import main as _main
    auth_svc = _main.auth_service
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


# ---------------------------------------------------------------------------
# Session expiry
# ---------------------------------------------------------------------------

class TestSessionExpiry:
    def _register_and_login(self, client):
        client.post("/auth/register", json={
            "email": "exp@example.com",
            "password": "password123",
            "name": "Exp",
        })
        resp = client.post("/auth/login", json={
            "email": "exp@example.com",
            "password": "password123",
        })
        return resp.json()["token"]

    def test_valid_token_accepted(self, client):
        token = self._register_and_login(client)
        resp = client.get(f"/auth/me?token={token}")
        assert resp.status_code == 200

    def test_expired_token_rejected(self, client):
        import services.auth_service as auth_svc
        import time as _time
        token = self._register_and_login(client)
        # Rewrite expiry to the past by monkeypatching time inside the token
        # Instead, forge a token whose exp field is in the past.
        parts = token.rsplit(":", 1)          # split off signature
        payload = parts[0]
        fields = payload.split(":")           # [email, nonce, ts, exp]
        fields[3] = str(int(_time.time()) - 1)  # exp = 1 second ago
        bad_payload = ":".join(fields)
        bad_sig = auth_svc._sign(bad_payload)
        expired_token = f"{bad_payload}:{bad_sig}"
        resp = client.get(f"/auth/me?token={expired_token}")
        assert resp.status_code == 401

    def test_tampered_token_rejected(self, client):
        token = self._register_and_login(client)
        # Flip last character of signature
        bad = token[:-1] + ("0" if token[-1] != "0" else "1")
        resp = client.get(f"/auth/me?token={bad}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /auth/update-profile
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    def _setup(self, client):
        client.post("/auth/register", json={
            "email": "profile@example.com",
            "password": "password123",
            "name": "Old Name",
        })
        resp = client.post("/auth/login", json={
            "email": "profile@example.com",
            "password": "password123",
        })
        return resp.json()["token"]

    def test_update_name_success(self, client):
        token = self._setup(client)
        resp = client.post("/auth/update-profile", json={"token": token, "name": "New Name"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["user"]["name"] == "New Name"

    def test_update_name_reflected_in_me(self, client):
        token = self._setup(client)
        client.post("/auth/update-profile", json={"token": token, "name": "Updated"})
        resp = client.get(f"/auth/me?token={token}")
        assert resp.json()["name"] == "Updated"

    def test_update_empty_name_rejected(self, client):
        token = self._setup(client)
        resp = client.post("/auth/update-profile", json={"token": token, "name": "   "})
        assert resp.status_code == 400

    def test_update_invalid_token_rejected(self, client):
        resp = client.post("/auth/update-profile", json={"token": "bogus", "name": "X"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /auth/change-password
# ---------------------------------------------------------------------------

class TestChangePassword:
    def _setup(self, client):
        client.post("/auth/register", json={
            "email": "chpass@example.com",
            "password": "oldpassword1",
            "name": "User",
        })
        resp = client.post("/auth/login", json={
            "email": "chpass@example.com",
            "password": "oldpassword1",
        })
        return resp.json()["token"]

    def test_change_password_success(self, client):
        token = self._setup(client)
        resp = client.post("/auth/change-password", json={
            "token": token,
            "old_password": "oldpassword1",
            "new_password": "newpassword2",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_new_password_works_for_login(self, client):
        token = self._setup(client)
        client.post("/auth/change-password", json={
            "token": token,
            "old_password": "oldpassword1",
            "new_password": "newpassword2",
        })
        resp = client.post("/auth/login", json={
            "email": "chpass@example.com",
            "password": "newpassword2",
        })
        assert resp.status_code == 200

    def test_old_password_rejected_after_change(self, client):
        token = self._setup(client)
        client.post("/auth/change-password", json={
            "token": token,
            "old_password": "oldpassword1",
            "new_password": "newpassword2",
        })
        resp = client.post("/auth/login", json={
            "email": "chpass@example.com",
            "password": "oldpassword1",
        })
        assert resp.status_code == 401

    def test_wrong_old_password_rejected(self, client):
        token = self._setup(client)
        resp = client.post("/auth/change-password", json={
            "token": token,
            "old_password": "wrongpassword",
            "new_password": "newpassword2",
        })
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["detail"]

    def test_new_password_too_short_rejected(self, client):
        token = self._setup(client)
        resp = client.post("/auth/change-password", json={
            "token": token,
            "old_password": "oldpassword1",
            "new_password": "short",
        })
        assert resp.status_code == 400

    def test_invalid_token_rejected(self, client):
        resp = client.post("/auth/change-password", json={
            "token": "bogus",
            "old_password": "anything",
            "new_password": "newpassword2",
        })
        assert resp.status_code == 400

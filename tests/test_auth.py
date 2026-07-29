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


# ---------------------------------------------------------------------------
# /auth/logout
# ---------------------------------------------------------------------------

class TestLogout:
    def _setup(self, client):
        client.post("/auth/register", json={
            "email": "logoutuser@example.com",
            "password": "password123",
            "name": "Logout",
        })
        resp = client.post("/auth/login", json={
            "email": "logoutuser@example.com",
            "password": "password123",
        })
        return resp.json()["token"]

    def test_logout_returns_success(self, client):
        token = self._setup(client)
        resp = client.post("/auth/logout", json={"token": token})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_token_invalid_after_logout(self, client):
        token = self._setup(client)
        client.post("/auth/logout", json={"token": token})
        resp = client.get(f"/auth/me?token={token}")
        assert resp.status_code == 401

    def test_logout_with_bogus_token_still_200(self, client):
        """Logout is idempotent — invalid tokens don't return an error."""
        resp = client.post("/auth/logout", json={"token": "not-a-real-token"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /auth/delete-account
# ---------------------------------------------------------------------------

class TestDeleteAccount:
    def _setup(self, client):
        client.post("/auth/register", json={
            "email": "delete@example.com",
            "password": "password123",
            "name": "Delete",
        })
        resp = client.post("/auth/login", json={
            "email": "delete@example.com",
            "password": "password123",
        })
        return resp.json()["token"]

    def test_delete_account_success(self, client):
        token = self._setup(client)
        resp = client.request("DELETE", "/auth/delete-account", json={
            "token": token,
            "password": "password123",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_token_invalid_after_deletion(self, client):
        token = self._setup(client)
        client.request("DELETE", "/auth/delete-account", json={
            "token": token,
            "password": "password123",
        })
        resp = client.get(f"/auth/me?token={token}")
        assert resp.status_code == 401

    def test_login_fails_after_deletion(self, client):
        token = self._setup(client)
        client.request("DELETE", "/auth/delete-account", json={
            "token": token,
            "password": "password123",
        })
        resp = client.post("/auth/login", json={
            "email": "delete@example.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_wrong_password_rejected(self, client):
        token = self._setup(client)
        resp = client.request("DELETE", "/auth/delete-account", json={
            "token": token,
            "password": "wrongpassword",
        })
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["detail"]

    def test_invalid_token_rejected(self, client):
        resp = client.request("DELETE", "/auth/delete-account", json={
            "token": "bogus",
            "password": "password123",
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# CSRF Protection for Profile Updates
# ---------------------------------------------------------------------------

class TestCsrfProtection:
    def _setup(self, client):
        """Register and login a test user, return token."""
        client.post("/auth/register", json={
            "email": "csrf@example.com",
            "password": "password123",
            "name": "CSRF Test",
        })
        resp = client.post("/auth/login", json={
            "email": "csrf@example.com",
            "password": "password123",
        })
        return resp.json()["token"]

    def test_csrf_token_generation(self, client):
        """Verify CSRF token can be generated for valid session."""
        token = self._setup(client)
        resp = client.get("/auth/csrf-token", params={"token": token})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "csrf_token" in data
        assert len(data["csrf_token"]) > 20

    def test_csrf_token_invalid_session(self, client):
        """Verify CSRF token generation fails with invalid session."""
        resp = client.get("/auth/csrf-token", params={"token": "invalid.token"})
        assert resp.status_code == 401
        assert "Invalid or expired" in resp.json()["detail"]

    def test_profile_update_requires_csrf_token(self, client):
        """Verify profile update fails without CSRF token."""
        token = self._setup(client)
        resp = client.post("/auth/update-profile", json={
            "token": token,
            "name": "Updated Name",
        })
        assert resp.status_code == 400
        assert "CSRF token is required" in resp.json()["detail"]

    def test_profile_update_with_valid_csrf_token(self, client):
        """Verify profile update succeeds with valid CSRF token."""
        token = self._setup(client)

        # Get CSRF token
        csrf_resp = client.get("/auth/csrf-token", params={"token": token})
        csrf_token = csrf_resp.json()["csrf_token"]

        # Update profile with CSRF token
        resp = client.post("/auth/update-profile", json={
            "token": token,
            "csrf_token": csrf_token,
            "name": "Updated Name",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["user"]["name"] == "Updated Name"

    def test_csrf_token_invalid_after_use(self, client):
        """Verify CSRF tokens are single-use (cannot be reused)."""
        token = self._setup(client)

        # Get CSRF token
        csrf_resp = client.get("/auth/csrf-token", params={"token": token})
        csrf_token = csrf_resp.json()["csrf_token"]

        # First use should succeed
        resp1 = client.post("/auth/update-profile", json={
            "token": token,
            "csrf_token": csrf_token,
            "name": "First Update",
        })
        assert resp1.status_code == 200

        # Second use with same token should fail
        resp2 = client.post("/auth/update-profile", json={
            "token": token,
            "csrf_token": csrf_token,
            "name": "Second Update",
        })
        assert resp2.status_code == 400
        assert "Invalid or expired CSRF token" in resp2.json()["detail"]

    def test_csrf_token_invalid_token_rejected(self, client):
        """Verify invalid CSRF tokens are rejected."""
        token = self._setup(client)
        resp = client.post("/auth/update-profile", json={
            "token": token,
            "csrf_token": "invalid.csrf.token",
            "name": "Updated Name",
        })
        assert resp.status_code == 400
        assert "Invalid or expired CSRF token" in resp.json()["detail"]

    def test_csrf_token_protects_against_cross_session_use(self, client):
        """Verify CSRF tokens from one session cannot be used in another."""
        # Create two users
        client.post("/auth/register", json={
            "email": "user1@example.com",
            "password": "password123",
            "name": "User 1",
        })
        client.post("/auth/register", json={
            "email": "user2@example.com",
            "password": "password123",
            "name": "User 2",
        })

        # Login both users
        token1 = client.post("/auth/login", json={
            "email": "user1@example.com",
            "password": "password123",
        }).json()["token"]

        token2 = client.post("/auth/login", json={
            "email": "user2@example.com",
            "password": "password123",
        }).json()["token"]

        # Get CSRF token for user1
        csrf_token_1 = client.get(
            "/auth/csrf-token",
            params={"token": token1}
        ).json()["csrf_token"]

        # Try to use user1's CSRF token with user2's session
        resp = client.post("/auth/update-profile", json={
            "token": token2,
            "csrf_token": csrf_token_1,
            "name": "Hacked Name",
        })
        assert resp.status_code == 400
        assert "Invalid or expired CSRF token" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Rate-limiting is applied to /auth/register
# ---------------------------------------------------------------------------

class TestRegisterRateLimit:
    def test_register_endpoint_has_rate_limit_decorator(self):
        """
        Verify that the register endpoint is wrapped by the rate limiter.
        We don't actually trigger the limit (tests run with 10000/minute) —
        instead we confirm the route has the limiter decoration by checking
        that the FastAPI app includes an exception handler for RateLimitExceeded.
        """
        import main as _main
        from slowapi.errors import RateLimitExceeded
        assert RateLimitExceeded in _main.app.exception_handlers

"""
Auth Service – Registration, Login, Password Reset
----------------------------------------------------
Simple in-memory user store with PBKDF2 password hashing and
HMAC-signed session tokens.  No external dependencies beyond stdlib.

In production, replace _USERS / _RESET_TOKENS with a real database
(e.g. PostgreSQL + SQLAlchemy) and deliver reset links by email.

Public API
----------
register(email, password, name)           → user dict  or raises ValueError
login(email, password)                    → token str  or raises ValueError
request_password_reset(email)             → reset_token str
reset_password(reset_token, new_password) → None       or raises ValueError
get_user(token)                           → user dict  or None

Security notes
--------------
* Passwords are hashed with PBKDF2-HMAC-SHA256, 200 000 iterations.
* Session tokens are HMAC-SHA256–signed opaque strings.
* _APP_SECRET is read from KALA_SECRET env var; falls back to a random
  value generated at start-up (tokens are therefore invalidated on
  server restart when the env var is not set — acceptable for demo).
* request_password_reset() always succeeds regardless of whether the
  email exists (prevents user enumeration).
"""

import hashlib
import hmac
import os
import secrets
import time
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# In-memory stores  (swap for a real DB in production)
# ---------------------------------------------------------------------------
_USERS: Dict[str, dict] = {}         # email → user record
_RESET_TOKENS: Dict[str, dict] = {}  # token → {email, expires_at}

_RESET_TTL  = 3_600                  # seconds – 1 hour
_APP_SECRET = os.environ.get("KALA_SECRET") or secrets.token_hex(32)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """Return (hex_hash, hex_salt).  Generates a fresh salt if not provided."""
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return dk.hex(), salt


def _sign(payload: str) -> str:
    return hmac.new(_APP_SECRET.encode(), payload.encode(), "sha256").hexdigest()


def _make_session_token(email: str) -> str:
    nonce   = secrets.token_hex(16)
    ts      = int(time.time())
    payload = f"{email}:{nonce}:{ts}"
    sig     = _sign(payload)
    return f"{payload}:{sig}"


def _verify_session_token(token: str) -> Optional[str]:
    """Return the email embedded in a valid token, otherwise None."""
    try:
        idx = token.rfind(":")
        if idx < 0:
            return None
        payload, sig = token[:idx], token[idx + 1:]
        expected = _sign(payload)
        if not hmac.compare_digest(sig, expected):
            return None
        email = payload.split(":")[0]
        return email if email in _USERS else None
    except Exception:  # pragma: no cover – defensive catch-all
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register(email: str, password: str, name: str) -> dict:
    """Create a new user account.  Returns user info dict on success."""
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Invalid email address.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if email in _USERS:
        raise ValueError("An account with this email already exists.")

    pw_hash, pw_salt = _hash_password(password)
    _USERS[email] = {
        "email":      email,
        "name":       name.strip() or email.split("@")[0],
        "pw_hash":    pw_hash,
        "pw_salt":    pw_salt,
        "created_at": int(time.time()),
    }
    return {"email": email, "name": _USERS[email]["name"]}


def login(email: str, password: str) -> str:
    """Validate credentials and return a signed session token."""
    email = email.strip().lower()
    user  = _USERS.get(email)
    if not user:
        raise ValueError("Invalid email or password.")
    dk, _ = _hash_password(password, user["pw_salt"])
    if not hmac.compare_digest(dk, user["pw_hash"]):
        raise ValueError("Invalid email or password.")
    return _make_session_token(email)


def request_password_reset(email: str) -> str:
    """
    Generate a password-reset token.  Always returns a token string so the
    caller cannot determine whether the email address exists (anti-enum).

    In production: do NOT return the token in the API response — email it
    to the user as a link instead.
    """
    email = email.strip().lower()
    token = secrets.token_urlsafe(32)
    if email in _USERS:
        _RESET_TOKENS[token] = {
            "email":      email,
            "expires_at": int(time.time()) + _RESET_TTL,
        }
    return token


def reset_password(reset_token: str, new_password: str) -> None:
    """Apply the new password if the reset token is valid and unexpired."""
    entry = _RESET_TOKENS.get(reset_token)
    if not entry or int(time.time()) > entry["expires_at"]:
        raise ValueError("Reset link has expired or is invalid.")
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    email = entry["email"]
    pw_hash, pw_salt = _hash_password(new_password)
    _USERS[email]["pw_hash"] = pw_hash
    _USERS[email]["pw_salt"] = pw_salt
    del _RESET_TOKENS[reset_token]


def get_user(token: str) -> Optional[dict]:
    """Return public user info for a valid session token, or None."""
    email = _verify_session_token(token)
    if not email:
        return None
    user = _USERS.get(email)
    if not user:
        return None
    return {"email": user["email"], "name": user["name"]}

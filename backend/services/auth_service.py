"""
Auth Service – Registration, Login, Password Reset, Profile
-------------------------------------------------------------
Persists users and reset tokens to SQLite (KALA_DB_PATH, default: kalaos.db).
Passwords are PBKDF2-HMAC-SHA256 hashed; sessions use HMAC-SHA256-signed
tokens with a 30-day TTL.

Optional SMTP delivery for password-reset tokens:
  KALA_SMTP_HOST  – SMTP hostname (enables email delivery when set)
  KALA_SMTP_PORT  – SMTP port (default: 587)
  KALA_SMTP_USER  – SMTP username
  KALA_SMTP_PASS  – SMTP password
  KALA_SMTP_FROM  – Sender address (defaults to KALA_SMTP_USER)
  KALA_APP_URL    – Public base URL used to build the reset link

Public API
----------
register(email, password, name)                    → user dict  or raises ValueError
login(email, password)                             → token str  or raises ValueError
logout(token)                                      → None (revokes the token server-side)
request_password_reset(email)                      → reset_token str (empty str when SMTP delivers it)
reset_password(reset_token, new_password)          → None       or raises ValueError
get_user(token)                                    → user dict  or None
update_profile(token, name)                        → user dict  or raises ValueError
change_password(token, old_password, new_password) → None       or raises ValueError
delete_account(token, password)                    → None       or raises ValueError

Security notes
--------------
* Passwords: PBKDF2-HMAC-SHA256, 200 000 iterations.
* Session tokens: HMAC-SHA256-signed; include a 30-day expiry timestamp.
* _APP_SECRET is read from KALA_SECRET env var; falls back to a per-process
  random value (tokens are invalidated on restart when the env var is unset).
* request_password_reset() always succeeds regardless of whether the email
  exists (prevents user enumeration).
* logout() adds the token to a short-lived revocation list (TTL = remaining
  token lifetime) so it cannot be reused even before its natural expiry.
"""

import hashlib
import hmac
import logging
import os
import secrets
import smtplib
import sqlite3
import threading
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_APP_SECRET  = os.environ.get("KALA_SECRET") or secrets.token_hex(32)
_DB_PATH     = os.environ.get("KALA_DB_PATH", "kalaos.db")
_RESET_TTL   = 3_600           # seconds – 1 hour
_SESSION_TTL = 30 * 86_400     # seconds – 30 days

# SMTP (all optional; email delivery enabled only when KALA_SMTP_HOST is set)
_SMTP_HOST = os.environ.get("KALA_SMTP_HOST", "")
_SMTP_PORT = int(os.environ.get("KALA_SMTP_PORT", "587"))
_SMTP_USER = os.environ.get("KALA_SMTP_USER", "")
_SMTP_PASS = os.environ.get("KALA_SMTP_PASS", "")
_SMTP_FROM = os.environ.get("KALA_SMTP_FROM", "") or _SMTP_USER
_APP_URL   = os.environ.get("KALA_APP_URL", "http://localhost:8000")

# Consumers can check this to decide whether to expose the reset token in the response.
SMTP_CONFIGURED: bool = bool(_SMTP_HOST)


# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

_db_lock = threading.Lock()


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _db_init() -> None:
    with _db_lock:
        with _get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    email      TEXT PRIMARY KEY,
                    name       TEXT NOT NULL,
                    pw_hash    TEXT NOT NULL,
                    pw_salt    TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    avatar_url TEXT NOT NULL DEFAULT '',
                    bio        TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reset_tokens (
                    token      TEXT PRIMARY KEY,
                    email      TEXT NOT NULL,
                    expires_at INTEGER NOT NULL
                )
            """)
            # Migration: add new user columns.
            # _MIGRATION_COLS values are hardcoded source constants (not user input).
            # Column names are validated against an alphanumeric+underscore whitelist
            # before being interpolated into the ALTER TABLE statement.
            _MIGRATION_COLS = {"avatar_url": "''", "bio": "''"}
            _ALLOWED_DEFAULT = frozenset(_MIGRATION_COLS.values())
            for col, default in _MIGRATION_COLS.items():
                if not col.replace("_", "").isalnum() or default not in _ALLOWED_DEFAULT:
                    raise RuntimeError(f"Unsafe migration column definition: {col!r}")
                try:
                    conn.execute(
                        f"ALTER TABLE users ADD COLUMN {col} TEXT NOT NULL DEFAULT {default}"
                    )
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise  # unexpected error — re-raise


def _db_upsert_user(email: str, user: dict) -> None:
    with _db_lock:
        with _get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO users "
                "(email, name, pw_hash, pw_salt, created_at, avatar_url, bio) VALUES (?,?,?,?,?,?,?)",
                (user["email"], user["name"], user["pw_hash"],
                 user["pw_salt"], user["created_at"],
                 user.get("avatar_url", ""), user.get("bio", "")),
            )


def _db_delete_user(email: str) -> None:
    with _db_lock:
        with _get_db() as conn:
            conn.execute("DELETE FROM users WHERE email = ?", (email,))


def _db_clear_users() -> None:
    with _db_lock:
        with _get_db() as conn:
            conn.execute("DELETE FROM users")


def _db_upsert_token(token: str, entry: dict) -> None:
    with _db_lock:
        with _get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO reset_tokens (token, email, expires_at) VALUES (?,?,?)",
                (token, entry["email"], entry["expires_at"]),
            )


def _db_delete_token(token: str) -> None:
    with _db_lock:
        with _get_db() as conn:
            conn.execute("DELETE FROM reset_tokens WHERE token = ?", (token,))


def _db_clear_tokens() -> None:
    with _db_lock:
        with _get_db() as conn:
            conn.execute("DELETE FROM reset_tokens")


# ---------------------------------------------------------------------------
# SQLite-backed in-memory stores
# ---------------------------------------------------------------------------

class _UserStore(dict):
    """dict subclass that mirrors every mutation to the SQLite users table."""

    def __setitem__(self, key: str, value: dict) -> None:
        super().__setitem__(key, value)
        _db_upsert_user(key, value)

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        _db_delete_user(key)

    def clear(self) -> None:
        super().clear()
        _db_clear_users()


class _TokenStore(dict):
    """dict subclass that mirrors every mutation to the SQLite reset_tokens table."""

    def __setitem__(self, key: str, value: dict) -> None:
        super().__setitem__(key, value)
        _db_upsert_token(key, value)

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        _db_delete_token(key)

    def clear(self) -> None:
        super().clear()
        _db_clear_tokens()


_USERS: _UserStore = _UserStore()
_RESET_TOKENS: _TokenStore = _TokenStore()

# ---------------------------------------------------------------------------
# In-memory revocation list for logged-out session tokens.
# Entries: { token_sig: expires_at_unix_int }.  Expired entries are pruned
# lazily on each revocation check so the dict stays small.
# ---------------------------------------------------------------------------
_REVOKED_TOKENS: dict = {}
_revoked_lock = threading.Lock()


def _revoke_token(token: str, exp: int) -> None:
    """Add a token's signature to the revocation list until its natural expiry."""
    sig = token.rsplit(":", 1)[-1]  # use the HMAC signature as the key
    with _revoked_lock:
        _REVOKED_TOKENS[sig] = exp
        # Prune expired entries while we have the lock
        now = int(time.time())
        expired = [k for k, v in _REVOKED_TOKENS.items() if v <= now]
        for k in expired:
            del _REVOKED_TOKENS[k]


def _is_revoked(token: str) -> bool:
    sig = token.rsplit(":", 1)[-1]
    with _revoked_lock:
        exp = _REVOKED_TOKENS.get(sig)
    return exp is not None and int(time.time()) <= exp


def _bootstrap() -> None:
    """Initialise DB schema and warm the in-memory caches from SQLite."""
    _db_init()
    now = int(time.time())
    with _db_lock:
        with _get_db() as conn:
            for row in conn.execute(
                "SELECT email, name, pw_hash, pw_salt, created_at, avatar_url, bio FROM users"
            ):
                dict.__setitem__(_USERS, row["email"], dict(row))
            for row in conn.execute(
                "SELECT token, email, expires_at FROM reset_tokens WHERE expires_at > ?",
                (now,),
            ):
                dict.__setitem__(_RESET_TOKENS, row["token"], dict(row))


_bootstrap()


# ---------------------------------------------------------------------------
# SMTP helper
# ---------------------------------------------------------------------------

def _send_reset_email(to_email: str, reset_token: str) -> None:
    """
    Send a password-reset email via SMTP.  Swallows errors so a misconfigured
    mail server never blocks the API response.
    """
    reset_url = f"{_APP_URL.rstrip('/')}/#reset?token={reset_token}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "KalaOS – Reset your password"
    msg["From"]    = _SMTP_FROM
    msg["To"]      = to_email

    plain = (
        f"Hi,\n\n"
        f"You requested a password reset for your KalaOS account.\n\n"
        f"Reset link (valid for 1 hour):\n{reset_url}\n\n"
        f"If you didn't request this, you can safely ignore this email.\n\n"
        f"— The KalaOS Team"
    )
    html = (
        f"<p>Hi,</p>"
        f"<p>You requested a password reset for your KalaOS account.</p>"
        f'<p><a href="{reset_url}">Click here to reset your password</a> '
        f"(valid for 1 hour).</p>"
        f"<p>If you didn't request this, you can safely ignore this email.</p>"
        f"<p>— The KalaOS Team</p>"
    )
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=10) as server:
            server.starttls()
            if _SMTP_USER and _SMTP_PASS:
                server.login(_SMTP_USER, _SMTP_PASS)
            server.sendmail(_SMTP_FROM, to_email, msg.as_string())
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to send password-reset email to %s: %s", to_email, exc)


# ---------------------------------------------------------------------------
# Internal crypto helpers
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
    exp     = ts + _SESSION_TTL
    payload = f"{email}:{nonce}:{ts}:{exp}"
    sig     = _sign(payload)
    return f"{payload}:{sig}"


def _verify_session_token(token: str) -> Optional[str]:
    """Return the email embedded in a valid, unexpired, non-revoked token, or None."""
    try:
        idx = token.rfind(":")
        if idx < 0:
            return None
        payload, sig = token[:idx], token[idx + 1:]
        expected = _sign(payload)
        if not hmac.compare_digest(sig, expected):
            return None
        parts = payload.split(":")
        if len(parts) < 4:
            return None
        email, _, _, exp = parts[0], parts[1], parts[2], parts[3]
        if int(time.time()) > int(exp):
            return None
        if _is_revoked(token):
            return None
        return email if email in _USERS else None
    except Exception:  # pragma: no cover – defensive catch-all
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register(email: str, password: str, name: str,
             avatar_url: str = "", bio: str = "") -> dict:
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
        "avatar_url": avatar_url,
        "bio":        bio,
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
    Generate a password-reset token.  Always returns a token string (or an
    empty string when SMTP delivery is enabled) so the caller cannot determine
    whether the email exists (anti-enumeration).

    When KALA_SMTP_HOST is set the token is emailed to the user and an empty
    string is returned; the API endpoint should omit the token from the response
    in that case.
    """
    email = email.strip().lower()
    token = secrets.token_urlsafe(32)
    if email in _USERS:
        _RESET_TOKENS[token] = {
            "email":      email,
            "expires_at": int(time.time()) + _RESET_TTL,
        }
        if SMTP_CONFIGURED:
            _send_reset_email(email, token)
            return ""   # token delivered by email; don't expose it in the response
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
    user = dict(_USERS[email])
    user["pw_hash"] = pw_hash
    user["pw_salt"] = pw_salt
    _USERS[email] = user       # triggers SQLite sync
    del _RESET_TOKENS[reset_token]


def get_user(token: str) -> Optional[dict]:
    """Return public user info for a valid session token, or None."""
    email = _verify_session_token(token)
    if not email:
        return None
    user = _USERS.get(email)
    if not user:
        return None
    return {"email": user["email"], "name": user["name"],
            "avatar_url": user.get("avatar_url", ""), "bio": user.get("bio", ""),
            "created_at": user["created_at"]}


def get_user_by_email(email: str) -> Optional[dict]:
    """Return public profile for a user by email, or None if not found."""
    user = _USERS.get(email.strip().lower())
    if not user:
        return None
    return {
        "email":      user["email"],
        "name":       user["name"],
        "avatar_url": user.get("avatar_url", ""),
        "bio":        user.get("bio", ""),
        "created_at": user["created_at"],
    }


def update_profile(token: str, name: str,
                   avatar_url: Optional[str] = None, bio: Optional[str] = None) -> dict:
    """Update the display name, avatar_url, and bio for the authenticated user."""
    email = _verify_session_token(token)
    if not email:
        raise ValueError("Invalid or expired session token.")
    name = name.strip()
    if not name:
        raise ValueError("Name must not be empty.")
    user = dict(_USERS[email])
    user["name"] = name
    if avatar_url is not None:
        user["avatar_url"] = avatar_url
    if bio is not None:
        user["bio"] = bio
    _USERS[email] = user       # triggers SQLite sync
    return {"email": email, "name": name,
            "avatar_url": user.get("avatar_url", ""), "bio": user.get("bio", "")}


def change_password(token: str, old_password: str, new_password: str) -> None:
    """Change the password for the authenticated user."""
    email = _verify_session_token(token)
    if not email:
        raise ValueError("Invalid or expired session token.")
    user = _USERS[email]
    dk, _ = _hash_password(old_password, user["pw_salt"])
    if not hmac.compare_digest(dk, user["pw_hash"]):
        raise ValueError("Current password is incorrect.")
    if len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters.")
    pw_hash, pw_salt = _hash_password(new_password)
    updated = dict(user)
    updated["pw_hash"] = pw_hash
    updated["pw_salt"] = pw_salt
    _USERS[email] = updated    # triggers SQLite sync


def logout(token: str) -> None:
    """Revoke a session token so it cannot be used again before its natural expiry.

    This is a best-effort server-side revocation: the token is added to an
    in-memory revocation list keyed by its HMAC signature.  If the process
    restarts, previously-issued tokens will still expire naturally via their
    embedded ``exp`` timestamp.
    """
    try:
        idx = token.rfind(":")
        if idx < 0:
            return
        payload = token[:idx]
        parts = payload.split(":")
        if len(parts) >= 4:
            exp = int(parts[3])
            _revoke_token(token, exp)
    except Exception:  # pragma: no cover
        pass  # silently ignore malformed tokens on logout


def delete_account(token: str, password: str) -> None:
    """Permanently delete the authenticated user's account.

    Requires the current password as confirmation, then revokes the session
    token and removes all user data (users row + any pending reset tokens).
    """
    email = _verify_session_token(token)
    if not email:
        raise ValueError("Invalid or expired session token.")
    user = _USERS[email]
    dk, _ = _hash_password(password, user["pw_salt"])
    if not hmac.compare_digest(dk, user["pw_hash"]):
        raise ValueError("Password is incorrect.")
    # Revoke the token immediately
    logout(token)
    # Delete the user (triggers SQLite sync via _UserStore.__delitem__)
    del _USERS[email]
    # Remove any pending reset tokens belonging to this email
    stale = [k for k, v in list(_RESET_TOKENS.items()) if v.get("email") == email]
    for k in stale:
        del _RESET_TOKENS[k]

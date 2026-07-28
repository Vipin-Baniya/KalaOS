"""
CSRF Protection Middleware

Implements the Synchronizer Token Pattern to prevent Cross-Site Request Forgery (CSRF)
attacks. Each request that modifies state must include a valid CSRF token.

Security features:
- Tokens are cryptographically secure random values
- Each session has a unique CSRF token
- Tokens are validated on every state-mutating request
- Compatible with SameSite cookie policy
"""

import secrets
from typing import Dict
from fastapi import Request, HTTPException


class CSRFTokenStore:
    """In-memory store for CSRF tokens mapped to sessions."""

    def __init__(self):
        self._tokens: Dict[str, str] = {}  # token -> session_id mapping

    def generate_token(self, session_id: str) -> str:
        """Generate a new CSRF token for a session."""
        token = secrets.token_urlsafe(32)
        self._tokens[token] = session_id
        return token

    def validate_token(self, token: str, session_id: str) -> bool:
        """Validate that a token belongs to the given session."""
        stored_session = self._tokens.get(token)
        return stored_session == session_id

    def revoke_token(self, token: str) -> None:
        """Revoke a token after use."""
        self._tokens.pop(token, None)

    def revoke_session_tokens(self, session_id: str) -> None:
        """Revoke all tokens for a session (on logout)."""
        to_delete = [
            token for token, sid in self._tokens.items()
            if sid == session_id
        ]
        for token in to_delete:
            del self._tokens[token]


# Global CSRF token store
_csrf_store = CSRFTokenStore()


def get_csrf_store() -> CSRFTokenStore:
    """Get the global CSRF token store."""
    return _csrf_store


def extract_csrf_token(request: Request) -> str:
    """
    Extract CSRF token from request.

    Checks in order:
    1. X-CSRF-Token header (recommended for JSON APIs)
    2. CSRF-Token header
    3. csrf_token form field (for form submissions)
    4. _csrf query parameter (fallback)
    """
    # Header-based tokens (preferred for JSON APIs)
    token = request.headers.get("X-CSRF-Token", "").strip()
    if token:
        return token

    token = request.headers.get("CSRF-Token", "").strip()
    if token:
        return token

    # Form field (for traditional form submissions)
    # Note: Will be empty for JSON requests without explicit form parsing
    if hasattr(request.state, "form_data"):
        token = request.state.form_data.get("csrf_token", "").strip()
        if token:
            return token

    # Query parameter (lowest priority, for compatibility)
    token = request.query_params.get("_csrf", "").strip()
    if token:
        return token

    return ""


async def validate_csrf_token(request: Request, token: str, session_id: str) -> bool:
    """
    Validate CSRF token for a request.

    Args:
        request: FastAPI Request object
        token: CSRF token to validate
        session_id: Session ID to validate against

    Returns:
        True if token is valid, False otherwise
    """
    if not token or not session_id:
        return False

    store = get_csrf_store()
    return store.validate_token(token, session_id)


def requires_csrf_protection(request: Request) -> bool:
    """
    Determine if a request requires CSRF protection.

    State-mutating methods (POST, PUT, PATCH, DELETE) require CSRF protection.
    Safe methods (GET, HEAD, OPTIONS) do not.
    """
    return request.method in ("POST", "PUT", "PATCH", "DELETE")

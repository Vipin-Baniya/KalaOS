# JWT Token Refresh with Automatic Blacklisting

## Overview

The token refresh mechanism allows users to rotate their access tokens without requiring password re-authentication. The old token is automatically blacklisted upon refresh, preventing replay attacks and ensuring only the latest token can be used.

## Security Architecture

### Token Rotation Flow

```
Client sends current token
              ↓
    Server validates token
              ↓
    Token is valid and exists
              ↓
    Old token is blacklisted (logout)
              ↓
    New token is generated for same user
              ↓
    Response: new token to client
              ↓
    Old token can no longer be used
```

### Key Security Properties

1. **Automatic Blacklisting**: When `refresh_token()` is called, it internally calls `logout(old_token)`, which adds the old token to the blacklist immediately.

2. **Token Rotation**: Users get a fresh token with a new expiration time, extending their session without re-authentication.

3. **Replay Attack Prevention**: The old token is invalidated as soon as the refresh succeeds. If an attacker intercepts the old token, it cannot be used after the refresh.

4. **Rate Limiting**: The refresh endpoint uses the same rate limit as login (`_login_limit`) to prevent abuse.

## Implementation Details

### Backend Function: `refresh_token()`

Located in `backend/services/auth_service.py`:

```python
def refresh_token(old_token: str) -> str:
    """
    Generate a new access token from a valid existing token.
    Automatically blacklists the old token to prevent token replay attacks.

    Args:
        old_token: Current valid session token

    Returns:
        New session token

    Raises:
        ValueError: If the token is invalid or expired
    """
    # Verify the old token is valid
    email = _verify_session_token(old_token)
    if not email:
        raise ValueError("Invalid or expired session token.")

    # Blacklist the old token to prevent its use after refresh
    logout(old_token)

    # Generate a new token for the same user
    return _make_session_token(email)
```

### API Endpoint: `POST /auth/refresh`

**Request:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "email": "user@example.com",
    "name": "User Name",
    "id": "user_id",
    "avatar_url": "https://...",
    "bio": "..."
  }
}
```

**Error Response (401 Unauthorized):**
```json
{
  "detail": "Invalid or expired session token."
}
```

## Client Usage Examples

### JavaScript / TypeScript

```javascript
// Basic token refresh
async function refreshToken(currentToken) {
  try {
    const response = await fetch('/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token: currentToken,
      }),
    });

    if (!response.ok) {
      throw new Error(`Refresh failed: ${response.statusText}`);
    }

    const data = await response.json();
    return data.token; // New token
  } catch (error) {
    console.error('Token refresh failed:', error);
    // Handle refresh failure (e.g., redirect to login)
    throw error;
  }
}

// Auto-refresh before token expires
function setupTokenRefresh(token, expirationMs) {
  const refreshBeforeExpire = expirationMs - 60000; // Refresh 1 min before expiry

  setTimeout(() => {
    refreshToken(token)
      .then((newToken) => {
        // Store new token and reschedule refresh
        localStorage.setItem('token', newToken);
        setupTokenRefresh(newToken, expirationMs);
      })
      .catch(() => {
        // Redirect to login on refresh failure
        window.location.href = '/login';
      });
  }, refreshBeforeExpire);
}
```

### Python

```python
import requests
import time

def refresh_token(current_token, api_url):
    """Refresh an access token."""
    try:
        response = requests.post(
            f"{api_url}/auth/refresh",
            json={"token": current_token},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["token"]
    except requests.exceptions.RequestException as e:
        print(f"Token refresh failed: {e}")
        raise

class TokenManager:
    def __init__(self, api_url):
        self.api_url = api_url
        self.token = None
        self.token_expiry = None

    def refresh_if_needed(self):
        """Refresh token if it's close to expiration."""
        if self.token and self.token_expiry:
            # Refresh if expiring within 5 minutes
            if time.time() > (self.token_expiry - 300):
                self.token = refresh_token(self.token, self.api_url)
                # Update expiry (assuming 24-hour tokens)
                self.token_expiry = time.time() + 86400
```

## Best Practices

### When to Use Token Refresh

1. **Periodic Rotation**: Refresh tokens regularly (e.g., every 12-24 hours) to limit the window of exposure if a token is compromised.

2. **Before API Calls**: Check token expiration time before making requests and refresh if needed.

3. **After Sensitive Operations**: Refresh tokens after sensitive operations (password change, permission changes) to invalidate potentially compromised copies.

### Security Recommendations

1. **Keep Tokens Secure**: Store tokens in secure, HTTP-only cookies or secure storage (not localStorage).

2. **Validate Server-Side**: Always validate tokens server-side before processing requests.

3. **Monitor Refresh Patterns**: Log unusual refresh patterns (e.g., multiple refreshes in quick succession) as potential security indicators.

4. **Implement Exponential Backoff**: If refresh fails, implement exponential backoff before retrying.

5. **Graceful Degradation**: Handle refresh failures gracefully by prompting for re-authentication.

## Deployment Notes

### Environment Variables

- `KALA_RATE_LIMIT_LOGIN`: Controls refresh rate limit (default: "10/minute")

### Database Considerations

The token blacklist is maintained in-memory using `_REVOKED_TOKENS_REDIS_LIKE`. For production deployments with multiple backend instances:

1. **Redis Backing**: Consider using Redis for the blacklist to share revocation state across instances.
2. **Token Expiration**: Implement automatic cleanup of expired entries.
3. **Monitoring**: Log all token refresh operations for audit trails.

## Error Handling

| Status Code | Scenario | Handling |
|-------------|----------|----------|
| 200 | Token refreshed successfully | Use new token for future requests |
| 401 | Invalid or expired token | Redirect user to login |
| 429 | Rate limit exceeded | Wait before retrying (exponential backoff) |
| 500 | Server error | Retry with exponential backoff, then redirect to login |

## Testing

### Unit Tests

```python
def test_refresh_token_valid():
    """Verify token refresh works with valid token."""
    token = auth_service.login("test@example.com", "password123")
    new_token = auth_service.refresh_token(token)

    assert new_token != token
    assert auth_service.get_user(new_token) is not None
    assert auth_service.get_user(token) is None  # Old token is blacklisted

def test_refresh_token_invalid():
    """Verify refresh fails with invalid token."""
    with pytest.raises(ValueError, match="Invalid or expired"):
        auth_service.refresh_token("invalid.token.here")

def test_refresh_blacklists_old_token():
    """Verify old token is blacklisted after refresh."""
    token = auth_service.login("test@example.com", "password123")
    new_token = auth_service.refresh_token(token)

    # Old token should no longer work
    assert auth_service.get_user(token) is None
    # New token should work
    assert auth_service.get_user(new_token) is not None
```

### Integration Tests

```python
def test_refresh_endpoint():
    """Verify /auth/refresh endpoint works."""
    # Login
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = response.json()["token"]

    # Refresh
    response = client.post("/auth/refresh", json={"token": token})
    assert response.status_code == 200
    new_token = response.json()["token"]

    # Verify old token no longer works
    response = client.get("/auth/me", params={"token": token})
    assert response.status_code == 401

    # Verify new token works
    response = client.get("/auth/me", params={"token": new_token})
    assert response.status_code == 200
```

## Future Enhancements

1. **Refresh Token Rotation**: Implement separate refresh tokens with longer TTL for better security.
2. **Token Binding**: Bind tokens to client IP or device fingerprint.
3. **Revocation Verification**: Check Redis/database for revoked tokens instead of in-memory store.
4. **Audit Logging**: Log all token refresh operations for compliance.
5. **Device Management**: Track devices and allow users to revoke tokens by device.

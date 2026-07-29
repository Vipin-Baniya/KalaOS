# CSRF Protection for State-Mutating Endpoints

## Overview

KalaOS implements CSRF (Cross-Site Request Forgery) protection using the **Synchronizer Token Pattern** for state-mutating endpoints like profile updates. This prevents attackers from submitting forms on behalf of authenticated users without their knowledge.

## Vulnerability

### The Attack

A malicious website could exploit CSRF to modify a user's profile:

```html
<!-- Attacker's website -->
<form method="POST" action="https://kalaos.app/auth/update-profile">
  <input name="token" value="[user's session token from cookie]">
  <input name="name" value="Hacked">
  <input name="csrf_token" value="">
</form>
<script>document.forms[0].submit();</script>
```

### Why It Works (Without CSRF Protection)

1. User is logged into KalaOS (has valid session token)
2. User visits malicious website
3. Malicious form auto-submits using user's session token
4. Browser sends session cookie along with the request
5. Profile is updated without user's consent

### Why Our Protection Stops It

- The malicious site cannot obtain a valid CSRF token (tokens are server-generated and session-specific)
- Attacker's form submission fails validation
- Profile update is rejected

## Implementation

### CSRF Token Lifecycle

```
1. Client requests CSRF token
   GET /auth/csrf-token?token=[session_token]
   
2. Server generates token
   - Tied to user's session
   - Expires after 1 hour
   - Single-use only
   
3. Client includes token in state-mutating request
   POST /auth/update-profile
   {
     "token": "[session_token]",
     "csrf_token": "[csrf_token]",
     "name": "New Name"
   }
   
4. Server validates token
   - Checks token exists and hasn't expired
   - Verifies token belongs to this session
   - Deletes token (single-use enforcement)
   - Processes request if valid
```

### Protected Endpoints

- `POST /auth/update-profile` – Update user profile

### Public Functions

**In `auth_service.py`:**

```python
def generate_csrf_token(session_token: str) -> str:
    """
    Generate a CSRF token for a session.
    Returns a cryptographically secure token valid for 1 hour.
    """

def validate_csrf_token(csrf_token: str, session_token: str) -> bool:
    """
    Validate a CSRF token for a given session.
    Tokens are single-use — deleted after validation.
    Returns True if valid, False otherwise.
    """
```

## Client Implementation

### JavaScript/React

```javascript
// Step 1: Get CSRF token when user is ready to update profile
async function getCsrfToken(sessionToken) {
  const response = await fetch('/auth/csrf-token?token=' + sessionToken);
  const data = await response.json();
  return data.csrf_token;
}

// Step 2: Use token when submitting profile update
async function updateProfile(sessionToken, name, avatarUrl, bio) {
  // Get CSRF token first
  const csrfToken = await getCsrfToken(sessionToken);
  
  // Submit with CSRF token
  const response = await fetch('/auth/update-profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token: sessionToken,
      csrf_token: csrfToken,  // Include token
      name,
      avatar_url: avatarUrl,
      bio,
    }),
  });
  
  return await response.json();
}

// Usage
const csrfToken = await getCsrfToken(token);
await updateProfile(token, "New Name", "", "Bio");
```

### Python

```python
import requests

def get_csrf_token(session_token):
    """Get CSRF token for profile updates."""
    response = requests.get(
        'https://api.kalaos.app/auth/csrf-token',
        params={'token': session_token}
    )
    response.raise_for_status()
    return response.json()['csrf_token']

def update_profile(session_token, name, avatar_url=None, bio=None):
    """Update user profile with CSRF protection."""
    # Get CSRF token
    csrf_token = get_csrf_token(session_token)
    
    # Submit update with token
    response = requests.post(
        'https://api.kalaos.app/auth/update-profile',
        json={
            'token': session_token,
            'csrf_token': csrf_token,
            'name': name,
            'avatar_url': avatar_url,
            'bio': bio,
        }
    )
    response.raise_for_status()
    return response.json()

# Usage
csrf = get_csrf_token(token)
result = update_profile(token, "New Name")
```

## Security Properties

### Single-Use Tokens

- Each token can only be used once
- After validation, token is immediately deleted
- Attackers cannot reuse captured tokens

### Short Expiration (1 hour)

- Tokens expire after 1 hour
- Reduces window of vulnerability if token is captured
- User must request fresh token for operations after expiry

### Session-Bound

- Token is tied to specific session
- Cannot be transferred to different user
- Validates that token belongs to current session

### Cryptographically Secure Generation

- Uses `secrets.token_urlsafe(32)` for token generation
- 256+ bits of entropy
- Resistant to brute-force attacks

## Testing

### Unit Tests

```python
def test_csrf_token_generation():
    """Verify CSRF token generation."""
    token = auth_service.login("test@example.com", "password123")
    csrf_token = auth_service.generate_csrf_token(token)
    
    assert csrf_token is not None
    assert len(csrf_token) > 20

def test_csrf_token_validation():
    """Verify CSRF token validation works."""
    token = auth_service.login("test@example.com", "password123")
    csrf_token = auth_service.generate_csrf_token(token)
    
    # Valid token should validate
    assert auth_service.validate_csrf_token(csrf_token, token) is True

def test_csrf_token_single_use():
    """Verify tokens are single-use."""
    token = auth_service.login("test@example.com", "password123")
    csrf_token = auth_service.generate_csrf_token(token)
    
    # First use succeeds
    assert auth_service.validate_csrf_token(csrf_token, token) is True
    
    # Second use fails (already consumed)
    assert auth_service.validate_csrf_token(csrf_token, token) is False

def test_csrf_token_expiration():
    """Verify tokens expire after 1 hour."""
    token = auth_service.login("test@example.com", "password123")
    csrf_token = auth_service.generate_csrf_token(token)
    
    # Artificially expire the token
    with auth_service._csrf_lock:
        _, exp = auth_service._CSRF_TOKENS[csrf_token]
        auth_service._CSRF_TOKENS[csrf_token] = (token, int(time.time()) - 1)
    
    # Expired token should fail
    assert auth_service.validate_csrf_token(csrf_token, token) is False
```

### Integration Tests

```python
def test_profile_update_requires_csrf_token(client):
    """Verify profile update requires CSRF token."""
    # Login
    token = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    }).json()["token"]
    
    # Profile update without CSRF token should fail
    response = client.post("/auth/update-profile", json={
        "token": token,
        "name": "New Name"
    })
    assert response.status_code == 400
    assert "CSRF token is required" in response.json()["detail"]

def test_profile_update_with_csrf_token(client):
    """Verify profile update succeeds with valid CSRF token."""
    # Login
    token = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    }).json()["token"]
    
    # Get CSRF token
    csrf_token = client.get(
        "/auth/csrf-token",
        params={"token": token}
    ).json()["csrf_token"]
    
    # Profile update with CSRF token should succeed
    response = client.post("/auth/update-profile", json={
        "token": token,
        "csrf_token": csrf_token,
        "name": "New Name"
    })
    assert response.status_code == 200
    assert response.json()["success"] is True
```

## Deployment Notes

### Configuration

No special configuration required. CSRF protection is enabled by default for all state-mutating endpoints.

### Monitoring

Log CSRF validation failures to detect potential attack attempts:

```python
# Implement logging in auth_service
logger.warning(f"CSRF token validation failed for session {email}")
```

### Performance

- CSRF token generation: O(1) — generates random string
- CSRF token validation: O(1) — dictionary lookup with single-use deletion
- Token cleanup: Lazy pruning during validation (no background task needed)

### Future Enhancements

1. **Double-Submit Cookie Pattern**: Store CSRF token in cookie and body
2. **SameSite Cookies**: Complement CSRF tokens with SameSite=Strict
3. **X-CSRF-Token Header**: Support CSRF token in request headers
4. **Custom Headers**: Allow CSRF token in `X-CSRF-Token` header for AJAX

## References

- OWASP: [Cross-Site Request Forgery (CSRF)](https://owasp.org/www-community/attacks/csrf)
- CWE-352: [Cross-Site Request Forgery (CSRF)](https://cwe.mitre.org/data/definitions/352.html)

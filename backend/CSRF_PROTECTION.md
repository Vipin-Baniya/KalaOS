# CSRF Protection

## Overview

KalaOS implements the Synchronizer Token Pattern to protect against Cross-Site Request Forgery (CSRF) attacks. All state-mutating endpoints require a valid CSRF token.

## How It Works

### 1. Getting a CSRF Token

Before making any state-mutating request (POST, PUT, PATCH, DELETE), first obtain a CSRF token:

```bash
GET /auth/csrf-token?token=YOUR_SESSION_TOKEN
```

Response:
```json
{
  "success": true,
  "csrf_token": "abc123def456xyz789...",
  "message": "Include this csrf_token in X-CSRF-Token header or csrf_token field"
}
```

### 2. Including CSRF Token in Requests

Include the CSRF token in one of these ways (in order of preference):

#### Option 1: X-CSRF-Token Header (Recommended for JSON APIs)

```bash
POST /auth/update-profile
X-CSRF-Token: abc123def456xyz789...
Content-Type: application/json

{
  "token": "session_token...",
  "name": "New Name"
}
```

#### Option 2: csrf_token Form Field

```html
<form method="POST" action="/auth/update-profile">
  <input type="hidden" name="csrf_token" value="abc123def456xyz789...">
  <input type="hidden" name="token" value="session_token...">
  <input type="text" name="name" value="New Name">
  <button type="submit">Update Profile</button>
</form>
```

#### Option 3: Query Parameter (Lowest Priority)

```bash
POST /auth/update-profile?_csrf=abc123def456xyz789...
```

### 3. Protected Endpoints

The following endpoints require CSRF protection:

- `POST /auth/update-profile` - Update user profile
- `POST /auth/change-password` - Change password
- `POST /auth/logout` - Logout (revoke session)
- `DELETE /auth/delete-account` - Delete account

## Security Features

### Token Properties

- **Cryptographically Secure**: Uses `secrets.token_urlsafe(32)` for generation
- **Session-Specific**: Each token is tied to a session (can only be used for that session)
- **Single-Use**: Tokens are revoked after use to prevent replay attacks
- **Automatic Revocation**: All tokens for a session are revoked when user logs out or deletes account

### Validation

- Tokens are validated against the session token before processing
- Invalid or expired tokens return HTTP 403 (Forbidden)
- CSRF token validation is optional but strongly recommended

## Why This Protects Against CSRF

Traditional CSRF attacks exploit the browser's automatic cookie sending:

1. User logs into kalaos.app (browser stores session cookie)
2. User visits attacker.com
3. Attacker's page makes a cross-origin request: `<form method="POST" action="https://kalaos.app/api/profile/update">`
4. Browser automatically sends session cookie
5. Request succeeds (no CSRF protection)

With CSRF tokens:

1. Steps 1-2 same as above
2. Attacker's page tries to POST to `/api/profile/update`
3. **But attacker doesn't have the CSRF token** (stored server-side, not in cookies)
4. Browser can't automatically include it from a different origin
5. **Request fails** with 403 Forbidden

The key difference: CSRF tokens are **not stored in cookies**, so the attacker can't access them via cross-origin requests.

## Implementation Details

### Token Storage

CSRF tokens are stored in an in-memory dictionary mapping tokens to session IDs:

```python
_csrf_store = CSRFTokenStore()  # { token: session_id }
```

This provides:
- Fast O(1) token validation
- Automatic cleanup when sessions end
- No persistent storage needed

### Combined with Session Tokens

The current KalaOS architecture already has strong CSRF resistance because:

1. **Session tokens are NOT in cookies** - they're passed in request bodies
2. **Browsers can't auto-include body data** from cross-origin requests
3. **Form submissions can't easily send JSON** content-type

CSRF tokens add **defense in depth** for additional protection.

## Deployment Notes

### SameSite Cookies

While KalaOS doesn't currently use cookies for session management, if cookies are added in the future, always set the `SameSite` attribute:

```python
response.set_cookie(
    "session_token",
    token,
    httpOnly=True,
    secure=True,
    sameSite="Strict"  # Prevents cookie from being sent in cross-origin requests
)
```

`SameSite=Strict` is recommended over `Lax` for sensitive applications.

### Content Security Policy

Combine CSRF tokens with a strong Content Security Policy (CSP) for defense in depth:

```
Content-Security-Policy: default-src 'self'; script-src 'self'
```

This prevents inline scripts on attacker.com from reading CSRF tokens or making requests to your API.

## Migration Guide

### For Existing Clients

If your client is already using KalaOS:

1. After login, call `GET /auth/csrf-token` to get a token
2. Include the token in all subsequent state-mutating requests
3. Handle 403 responses by refreshing the CSRF token and retrying

### Example JavaScript Client

```javascript
class KalaOSClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.sessionToken = null;
    this.csrfToken = null;
  }

  async login(email, password) {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();
    this.sessionToken = data.token;

    // Get CSRF token
    await this.refreshCSRFToken();
    return data;
  }

  async refreshCSRFToken() {
    const response = await fetch(
      `${this.baseUrl}/auth/csrf-token?token=${this.sessionToken}`
    );
    const data = await response.json();
    this.csrfToken = data.csrf_token;
  }

  async updateProfile(name, avatarUrl) {
    try {
      const response = await fetch(`${this.baseUrl}/auth/update-profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': this.csrfToken  // Include CSRF token
        },
        body: JSON.stringify({
          token: this.sessionToken,
          name,
          avatar_url: avatarUrl
        })
      });

      if (response.status === 403) {
        // CSRF token expired, refresh and retry
        await this.refreshCSRFToken();
        return this.updateProfile(name, avatarUrl);
      }

      return await response.json();
    } catch (error) {
      console.error('Update profile failed:', error);
      throw error;
    }
  }
}
```

## Testing

### Test Valid CSRF Token

```bash
# 1. Login
LOGIN=$(curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"password123"}')

TOKEN=$(echo $LOGIN | jq -r '.token')

# 2. Get CSRF token
CSRF=$(curl "http://localhost:8000/auth/csrf-token?token=$TOKEN" | jq -r '.csrf_token')

# 3. Use CSRF token in update
curl -X POST http://localhost:8000/auth/update-profile \
  -H "X-CSRF-Token: $CSRF" \
  -H 'Content-Type: application/json' \
  -d "{\"token\":\"$TOKEN\",\"name\":\"New Name\"}"
```

### Test Invalid CSRF Token

```bash
# Use wrong CSRF token
curl -X POST http://localhost:8000/auth/update-profile \
  -H "X-CSRF-Token: wrong_token_here" \
  -H 'Content-Type: application/json' \
  -d "{\"token\":\"$TOKEN\",\"name\":\"New Name\"}"

# Should return 403 Forbidden
```

## References

- [OWASP CSRF Prevention](https://owasp.org/www-community/attacks/csrf)
- [Synchronizer Token Pattern](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#synchronizer-token-pattern)
- [MDN: SameSite Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite)

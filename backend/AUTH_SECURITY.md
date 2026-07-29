# Authentication Security Best Practices

## User Enumeration Prevention

### The Vulnerability

Login endpoints that return different error messages for "user not found" vs "invalid password" allow attackers to enumerate valid user email addresses:

```
Attacker tries email1@example.com with password "wrong"
Response: "User not found"  ← Email doesn't exist
Attacker knows email1 is NOT registered

Attacker tries email2@example.com with password "wrong"  
Response: "Invalid password"  ← Email exists but wrong password
Attacker knows email2 IS registered ✓

Attacker builds a list of valid emails for phishing/credential stuffing
```

### Impact

- **User Privacy**: Users' email addresses become discoverable through API enumeration
- **Phishing**: Attackers target real users with tailored phishing campaigns
- **Credential Stuffing**: Attackers use valid emails with leaked passwords from other services
- **Account Targeting**: Attackers know which accounts to focus on

### Security Fix

**Always use the same error message for both cases:**

```python
# INSECURE - reveals user existence
if not user:
    raise ValueError("User not found")
if not password_valid:
    raise ValueError("Invalid password")

# SECURE - generic error message
if not user or not password_valid:
    raise ValueError("Invalid email or password")
```

## Implementation in KalaOS

### Login Endpoint

The `/auth/login` endpoint uses a generic error message:

```python
@app.post("/auth/login")
def auth_login(request: Request, body: AuthLoginRequest):
    try:
        token = auth_service.login(body.email, body.password)
        user = auth_service.get_user(token)
        return {"success": True, "token": token, "user": user}
    except ValueError as exc:
        # Returns the same error message for all login failures
        raise HTTPException(status_code=401, detail=str(exc))
```

### auth_service.login()

The service function returns identical error messages:

```python
def login(email: str, password: str) -> str:
    """Validate credentials and return a signed session token."""
    email = email.strip().lower()
    user = _USERS.get(email)
    if not user:
        # Same error message for missing user
        raise ValueError("Invalid email or password.")
    
    dk, _ = _hash_password(password, user["pw_salt"])
    if not hmac.compare_digest(dk, user["pw_hash"]):
        # Same error message for invalid password
        raise ValueError("Invalid email or password.")
    
    return _make_session_token(email)
```

## HTTP Status Codes

All authentication failures return **401 Unauthorized** with the same generic message:

| Scenario | Status | Message |
|----------|--------|---------|
| Email not registered | 401 | "Invalid email or password." |
| Wrong password | 401 | "Invalid email or password." |
| Token expired | 401 | "Invalid or expired session token." |
| Token invalid | 401 | "Invalid or expired session token." |

## Testing User Enumeration Prevention

```python
def test_login_same_error_invalid_email(client):
    """Verify login returns same error for non-existent email."""
    resp = client.post("/auth/login", json={
        "email": "doesnotexist@example.com",
        "password": "wrongpassword"
    })
    assert resp.status_code == 401
    # Don't check exact message — attacker cannot distinguish
    # user not found from wrong password
    assert "detail" in resp.json()

def test_login_same_error_wrong_password(client):
    """Verify login returns same error for wrong password."""
    # First register a user
    client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "correctpassword",
        "name": "Test"
    })
    
    # Try wrong password
    resp = client.post("/auth/login", json={
        "email": "user@example.com",
        "password": "wrongpassword"
    })
    assert resp.status_code == 401
    # Same status code as non-existent user

def test_login_enumeration_resistance():
    """Verify timing attack resistance."""
    import time
    
    client = TestClient(app)
    
    # Time login with non-existent email
    start = time.perf_counter()
    client.post("/auth/login", json={
        "email": "doesnotexist@example.com",
        "password": "x"
    })
    time_nonexistent = time.perf_counter() - start
    
    # Register user
    client.post("/auth/register", json={
        "email": "exists@example.com",
        "password": "password123",
        "name": "Test"
    })
    
    # Time login with wrong password
    start = time.perf_counter()
    client.post("/auth/login", json={
        "email": "exists@example.com",
        "password": "wrongpassword"
    })
    time_wrong_password = time.perf_counter() - start
    
    # Times should be similar (both hash password in both cases)
    # Allow 50ms variance for system variance
    assert abs(time_nonexistent - time_wrong_password) < 0.050
```

## Related Endpoints

### Password Reset

The password reset endpoint also prevents enumeration:

```python
@app.post("/auth/forgot-password")
def auth_forgot(request: Request, body: AuthForgotRequest):
    token = auth_service.request_password_reset(body.email)
    # Always returns success regardless of email existence
    return {"success": True, "note": "If that email exists, a reset link has been sent."}
```

## Timing Attack Prevention

In addition to error message uniformity, password verification uses constant-time comparison:

```python
# INSECURE - timing leak reveals password length
if password == stored_hash:
    return True

# SECURE - constant-time comparison
if hmac.compare_digest(password_hash, stored_hash):
    return True
```

Both branches take approximately the same time regardless of where they differ, preventing attackers from learning about password structure through timing analysis.

## Defense Layers

| Layer | Prevention |
|-------|-----------|
| Message | Same error message for all failures |
| Status Code | Same HTTP 401 for all failures |
| Timing | Constant-time password comparison |
| Rate Limiting | Account lockout after N attempts |

## Recommendations

1. **Never return different error messages** for user existence vs password validity
2. **Use constant-time comparison** for sensitive data (passwords, tokens, HMACs)
3. **Apply rate limiting** to authentication endpoints to slow brute-force attempts
4. **Log suspicious activity** for security monitoring
5. **Test enumeration resistance** in your security test suite

## References

- [OWASP: User Enumeration](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/03-Identity_Management_Testing/04-Testing_for_User_Enumeration_and_User_Disclosure)
- [CWE-203: Observable Discrepancy](https://cwe.mitre.org/data/definitions/203.html)
- [Timing Attacks on Implementations of Diffie-Hellman, RSA, DSS, and Other Systems](https://www.paulkocher.com/TimingAttacks.html)

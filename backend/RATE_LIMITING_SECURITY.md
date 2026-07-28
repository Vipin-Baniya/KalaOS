# Rate Limiting Security

## Protecting Against X-Forwarded-For Header Spoofing

The KalaOS API implements secure rate limiting that prevents attackers from bypassing IP-based rate limits via X-Forwarded-For header spoofing.

## Configuration

### Trusted Proxies

By default, X-Forwarded-For headers are **not trusted** and only the direct connection IP is used for rate limiting.

To enable X-Forwarded-For header support (for deployments behind a reverse proxy), configure the trusted proxy IPs:

```bash
export KALA_TRUSTED_PROXIES="10.0.0.1,10.0.0.2"
```

Only X-Forwarded-For headers from these IPs will be trusted. This prevents an attacker from spoofing the header if they don't have access to the proxy.

### Rate Limit Thresholds

Customize rate limit thresholds per endpoint:

```bash
export KALA_RATE_LIMIT_LOGIN="10/minute"
export KALA_RATE_LIMIT_REGISTER="5/minute"
export KALA_RATE_LIMIT_FORGOT="5/minute"
```

## Implementation Details

### Secure IP Extraction

The `services/rate_limit_service.py` module provides secure IP extraction:

```python
from services.rate_limit_service import get_client_ip

# In rate limiter setup:
limiter = Limiter(key_func=get_client_ip, default_limits=[])

# Key function automatically:
# - Validates X-Forwarded-For only from trusted proxies
# - Falls back to direct connection IP
# - Validates IP format
```

### Per-User Rate Limiting

For authenticated endpoints, use per-user rate limiting to prevent bypass via IP spoofing:

```python
from services.rate_limit_service import get_user_or_ip

@app.post("/api/sensitive-endpoint")
@limiter.limit("5/minute", key_func=get_user_or_ip)
def sensitive_endpoint(request: Request):
    # If user is authenticated (request.state.user_id is set), 
    # limit is per-user, not per-IP
    # Unauthenticated requests are limited per-IP
```

## Security Considerations

### Threat: X-Forwarded-For Spoofing

**Attack Vector:**
1. Attacker sends 100 requests with different X-Forwarded-For values
2. Rate limiter treats each as from a different IP
3. Brute-force attack succeeds without triggering rate limits

**Mitigation:**
- Only trust X-Forwarded-For from configured proxy IPs
- Assume attackers can control headers if they can reach the application directly

### Threat: Bypass via User ID

**Attack Vector:**
1. Attacker steals a user ID or email
2. Creates many accounts and uses different user IDs for rate limiting bypass

**Mitigation:**
- Per-user limits are effective only if user ID is properly validated by auth middleware
- Ensure `request.state.user_id` is only set after successful authentication
- Account creation endpoints should use IP-based rate limiting

## Testing

### Verify X-Forwarded-For Rejection

```bash
# Without KALA_TRUSTED_PROXIES, this should be rejected/rate-limited
curl -H "X-Forwarded-For: 8.8.8.8" http://localhost:8000/auth/login -X POST

# With KALA_TRUSTED_PROXIES="10.0.0.1", same header should be trusted
# (if request actually comes from 10.0.0.1)
```

### Verify Per-User Rate Limiting

```bash
# After successful login, verify that subsequent requests are limited per-user,
# not per-IP. Rotating X-Forwarded-For should not bypass the limit for that user.
```

## References

- [RFC 7239 - Forwarded HTTP Extension](https://tools.ietf.org/html/rfc7239)
- [Express "trust proxy" Security](https://expressjs.com/en/guide/behind-proxies.html)
- [OWASP Rate Limiting](https://owasp.org/www-community/attacks/Rate_Limiting)

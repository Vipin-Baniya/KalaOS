# Rate Limiting Security with X-Forwarded-For Validation

## Overview

KalaOS implements rate limiting with secure X-Forwarded-For header validation to prevent attackers from bypassing rate limits by spoofing IPs through reverse proxy headers.

## Vulnerability

### The Attack

An attacker can bypass rate limits by rotating the `X-Forwarded-For` header value:

```bash
# Each request appears to come from a different IP
for i in {1..100}; do
  curl -H "X-Forwarded-For: 1.0.0.$i" https://api.kalaos.app/auth/login \
    -d '{"email":"user@example.com","password":"wrongpassword"}'
done

# Result: All 100 requests succeed (no 429 responses)
# Expected: After 10 requests, rate limiting should block further attempts
```

### Why It Works (Without Fix)

1. Reverse proxy sets `X-Forwarded-For` to show original client IP
2. Without validation, application trusts all `X-Forwarded-For` values
3. Attacker spoofs different IPs in each request
4. Each IP appears as a separate client, bypassing per-IP rate limits
5. Brute-force and DoS attacks proceed unhindered

### Why Our Protection Stops It

- Only trusted proxy IPs can set `X-Forwarded-For`
- Untrusted headers are ignored
- All requests from untrusted sources use direct connection IP
- Attacker cannot spoof different client IPs

## Implementation

### Rate Limiting Flow

```
Client Request
      ↓
   FastAPI
      ↓
Limiter checks key_func(request)
      ↓
get_rate_limit_key() called
      ↓
Is request from trusted proxy?
  ├→ No: Use direct connection IP
  ├→ Yes: Validate X-Forwarded-For header
  │         ├→ Invalid format: Use direct IP
  │         ├→ Missing header: Use direct IP
  │         └→ Valid IP: Use forwarded IP
      ↓
Get rate limit bucket for IP
      ↓
Check request count in time window
      ├→ Within limit: Allow (200)
└→ Limit exceeded: Reject (429)
```

### Configuration

#### Default Behavior (No Trusted Proxies)

If `KALA_TRUSTED_PROXIES` is not set:
- X-Forwarded-For header is completely ignored
- All requests are keyed by direct connection IP
- Safe for single-server deployments

```bash
# No environment variable needed
# X-Forwarded-For is ignored
```

#### Behind a Single Trusted Proxy

Set the proxy's IP address:

```bash
export KALA_TRUSTED_PROXIES="10.0.0.1"

# nginx/reverse proxy sets:
# X-Forwarded-For: {client_ip}, 10.0.0.1
# 
# KalaOS uses the client_ip from the header
# because 10.0.0.1 is trusted
```

#### Behind Multiple Trusted Proxies

Set all proxy IPs (comma-separated):

```bash
export KALA_TRUSTED_PROXIES="10.0.0.1,10.0.0.2,10.0.0.3"

# Multiple nginx instances or load balancers
# Each trusted proxy can add to X-Forwarded-For
```

### Rate-Limited Endpoints

- `POST /auth/register` – 5 requests per minute
- `POST /auth/login` – 10 requests per minute
- `POST /auth/forgot-password` – 5 requests per minute

## Security Properties

### 1. Proxy IP Validation

Only IPs listed in `KALA_TRUSTED_PROXIES` can set `X-Forwarded-For`:

```python
# Example: direct_ip = 10.0.0.1 (trusted proxy)
#          KALA_TRUSTED_PROXIES = "10.0.0.1"

# Valid: Use X-Forwarded-For
X-Forwarded-For: 203.0.113.42, 10.0.0.1  → Uses 203.0.113.42

# Invalid: direct_ip not in trusted list, ignore header
# (direct_ip = 192.0.2.1, KALA_TRUSTED_PROXIES = "10.0.0.1")
X-Forwarded-For: 203.0.113.42, 10.0.0.1  → Uses 192.0.2.1
```

### 2. IP Format Validation

Extracted IPs must be valid IPv4 addresses:

```python
# Valid IPs used for rate limiting
"203.0.113.42"  → Valid
"192.0.2.1"     → Valid
"::1"            → Invalid (IPv6, rejected)
"999.999.999.999" → Invalid (out of range)
"not-an-ip"     → Invalid (format error)
```

### 3. Fallback to Direct IP

If anything goes wrong with the header:

```python
# X-Forwarded-For missing
→ Use direct IP

# X-Forwarded-For malformed
→ Use direct IP

# X-Forwarded-For contains invalid IPs
→ Use direct IP

# Direct connection not from trusted proxy
→ Use direct IP (ignore header)
```

### 4. No Header Injection

Header injection via multiple X-Forwarded-For headers is prevented:

```python
# Multiple X-Forwarded-For headers
# (each line is separate header)
X-Forwarded-For: 203.0.113.1
X-Forwarded-For: 203.0.113.2

# First header is used: 203.0.113.1
# (HTTP spec: duplicate headers, first wins or concatenate)
```

## Deployment

### Docker/Kubernetes

Set environment variable when running container:

```bash
# Single proxy
docker run -e KALA_TRUSTED_PROXIES="10.0.0.1" kalaos:latest

# Multiple proxies (K8s)
env:
  - name: KALA_TRUSTED_PROXIES
    value: "10.0.0.1,10.0.0.2,10.0.0.3"
```

### Nginx Reverse Proxy Configuration

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.kalaos.app;

    location / {
        proxy_pass http://backend;
        
        # Set X-Forwarded-For so app knows original client IP
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Application Configuration

In KalaOS (start command):

```bash
# Set trusted proxy to your nginx server
export KALA_TRUSTED_PROXIES="127.0.0.1"  # If nginx is localhost
export KALA_TRUSTED_PROXIES="10.0.1.5"   # If nginx is on specific IP

# Start the application
python -m uvicorn backend.main:app
```

## Testing

### Test 1: Bypassing Rate Limit Without Fix

```bash
# This would work without the security fix
for i in {1..100}; do
  curl -H "X-Forwarded-For: 1.0.0.$i" \
    http://localhost:8000/auth/login \
    -d '{"email":"test@example.com","password":"wrong"}'
done
# Expected before fix: All succeed
# Expected after fix: 10 succeed, rest get 429 (unauthorized)
```

### Test 2: With Trusted Proxy Configured

```bash
export KALA_TRUSTED_PROXIES="127.0.0.1"

# Legitimate reverse proxy request
curl -H "X-Forwarded-For: 203.0.113.42" \
  http://localhost:8000/auth/login \
  -d '{"email":"test@example.com","password":"wrong"}'
# Result: Counted against 203.0.113.42's rate limit

# Direct attack with spoofed header (no proxy)
curl -H "X-Forwarded-For: 203.0.113.99" \
  -H "Host: localhost" \
  http://localhost:8000/auth/login \
  -d '{"email":"test@example.com","password":"wrong"}'
# Result: Counted against localhost's rate limit (direct IP)
# Because direct connection is not from 127.0.0.1 (not the proxy)
```

### Test 3: Invalid IP Format

```bash
export KALA_TRUSTED_PROXIES="127.0.0.1"

# Invalid IPv6 address in header
curl -H "X-Forwarded-For: ::1" \
  http://localhost:8000/auth/login
# Result: Uses direct IP (127.0.0.1), not the invalid ::1

# Out-of-range IP address
curl -H "X-Forwarded-For: 999.999.999.999" \
  http://localhost:8000/auth/login
# Result: Uses direct IP, not the invalid 999.999.999.999
```

## Python Unit Tests

```python
import pytest
from fastapi.testclient import TestClient
from utils.rate_limiting import get_client_ip, _is_valid_ipv4

def test_is_valid_ipv4():
    """Verify IP validation function."""
    assert _is_valid_ipv4("192.0.2.1") is True
    assert _is_valid_ipv4("0.0.0.0") is True
    assert _is_valid_ipv4("255.255.255.255") is True
    assert _is_valid_ipv4("256.256.256.256") is False
    assert _is_valid_ipv4("::1") is False
    assert _is_valid_ipv4("not-an-ip") is False

def test_get_client_ip_no_trusted_proxies(monkeypatch):
    """Verify X-Forwarded-For is ignored without trusted proxies."""
    monkeypatch.delenv("KALA_TRUSTED_PROXIES", raising=False)
    
    from fastapi import Request
    request = Request({"type": "http", "client": ("203.0.113.42", 1234)})
    request._headers = {"x-forwarded-for": "1.0.0.1"}
    
    # Should use direct IP, not header
    assert get_client_ip(request) == "203.0.113.42"

def test_get_client_ip_untrusted_proxy(monkeypatch):
    """Verify X-Forwarded-For is ignored from untrusted proxies."""
    monkeypatch.setenv("KALA_TRUSTED_PROXIES", "10.0.0.1")
    
    # Direct connection from untrusted IP
    request = Request({"type": "http", "client": ("203.0.113.42", 1234)})
    request._headers = {"x-forwarded-for": "1.0.0.1"}
    
    # Should use direct IP (not trusted proxy)
    assert get_client_ip(request) == "203.0.113.42"

def test_get_client_ip_trusted_proxy(monkeypatch):
    """Verify X-Forwarded-For is used from trusted proxies."""
    monkeypatch.setenv("KALA_TRUSTED_PROXIES", "10.0.0.1")
    
    # Direct connection from trusted proxy
    request = Request({"type": "http", "client": ("10.0.0.1", 5678)})
    request._headers = {"x-forwarded-for": "203.0.113.42"}
    
    # Should use forwarded IP
    assert get_client_ip(request) == "203.0.113.42"

def test_get_client_ip_invalid_forwarded(monkeypatch):
    """Verify invalid X-Forwarded-For falls back to direct IP."""
    monkeypatch.setenv("KALA_TRUSTED_PROXIES", "10.0.0.1")
    
    request = Request({"type": "http", "client": ("10.0.0.1", 5678)})
    request._headers = {"x-forwarded-for": "not-an-ip"}
    
    # Should fall back to direct IP
    assert get_client_ip(request) == "10.0.0.1"
```

## References

- [OWASP: Client IP Spoofing](https://owasp.org/www-community/attacks/Client-side_attacks)
- [Cloudflare: X-Forwarded-For Header](https://support.cloudflare.com/hc/en-us/articles/200170986-How-does-Cloudflare-handle-X-Forwarded-For-headers)
- [MDN: X-Forwarded-For](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For)

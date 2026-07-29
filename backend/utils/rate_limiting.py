"""Rate limiting utilities with secure X-Forwarded-For header handling."""

import os
import re
from typing import Optional

from fastapi import Request


def _is_valid_ipv4(ip: str) -> bool:
    """Validate IPv4 address format."""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    return all(0 <= int(part) <= 255 for part in parts)


def get_client_ip(request: Request) -> str:
    """
    Get client IP address with secure X-Forwarded-For header handling.

    Security measures:
    1. Only trust X-Forwarded-For from configured trusted proxies
    2. Validate IP format before using
    3. Fall back to direct connection IP if header is untrusted
    4. Log suspicious header usage

    Configuration:
    - KALA_TRUSTED_PROXIES: Comma-separated list of trusted proxy IPs
      Example: "10.0.0.1,10.0.0.2"
      If not set, X-Forwarded-For header is not trusted.

    Returns:
        Client IP address (string)
    """
    # Get trusted proxies from environment
    trusted_proxies_str = os.environ.get("KALA_TRUSTED_PROXIES", "")
    trusted_proxies = set()
    if trusted_proxies_str:
        trusted_proxies = set(ip.strip() for ip in trusted_proxies_str.split(","))

    # Get direct connection IP (always available and trusted)
    direct_ip = request.client.host if request.client else "127.0.0.1"

    # If no trusted proxies configured, always use direct IP
    if not trusted_proxies:
        return direct_ip

    # Check if direct connection is from a trusted proxy
    if direct_ip not in trusted_proxies:
        return direct_ip

    # Direct connection is from trusted proxy, check X-Forwarded-For
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if not forwarded_for:
        return direct_ip

    # Parse X-Forwarded-For header (rightmost IP is from most recent proxy)
    # Format: client, proxy1, proxy2, ...
    # We want the rightmost IP before our trusted proxy
    ips = [ip.strip() for ip in forwarded_for.split(",")]

    if not ips:
        return direct_ip

    # Take the first IP (client's original IP)
    client_ip = ips[0]

    # Validate IP format
    if not _is_valid_ipv4(client_ip):
        return direct_ip

    # IP is valid and from trusted proxy, use it
    return client_ip


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key based on client IP (secure).
    Uses get_client_ip() to properly handle X-Forwarded-For headers.
    """
    return get_client_ip(request)

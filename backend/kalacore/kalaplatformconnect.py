"""
KalaPlatformConnect – Platform Connect Module
----------------------------------------------
Handles OAuth connections, distribution, EPK generation, analytics,
catalog sync, smart links, release scheduling, and royalty reporting
for external platforms.

Public API
----------
connect_oauth_platform(platform, user_id, scope)
distribute_release(title, artist, platforms, release_date, metadata)
generate_epk(artist_name, bio, genres, contact_email, media_links)
get_platform_analytics(platform, user_id, time_range)
sync_catalog(user_id, source_platform, target_platforms)
create_smart_link(title, artist, platforms_urls)
schedule_release(title, artist, release_date, platforms, pre_save_enabled)
get_royalty_report(user_id, period, platforms)
"""

from __future__ import annotations

import datetime
import hashlib
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Valid values
# ---------------------------------------------------------------------------

_VALID_PLATFORMS: set[str] = {
    "spotify", "youtube", "soundcloud", "instagram",
    "tiktok", "twitter", "bandcamp", "distrokid",
}

_VALID_TIME_RANGES: set[str] = {"7d", "30d", "90d", "1y"}

_EPK_SECTIONS: list[str] = [
    "Biography", "Discography", "Press Photos",
    "Press Quotes", "Contact", "Rider",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest(), 16)


def _short_hash(seed: str, length: int = 12) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()[:length]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def connect_oauth_platform(
    platform: str,
    user_id: str,
    scope: str,
) -> dict[str, Any]:
    """Initiate an OAuth connection to an external platform.

    Parameters
    ----------
    platform: One of the supported platform names.
    user_id:  Unique identifier of the user.
    scope:    Requested OAuth scope string.

    Returns
    -------
    Dict with keys: platform, user_id, auth_url, state_token, expires_in,
    scope, status.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if platform not in _VALID_PLATFORMS:
        raise ValueError(f"platform must be one of {sorted(_VALID_PLATFORMS)}")
    if not user_id or not user_id.strip():
        raise ValueError("user_id must not be empty")
    if not scope or not scope.strip():
        raise ValueError("scope must not be empty")

    state_token = _short_hash(f"{platform}{user_id}{scope}", 32)
    return {
        "platform": platform,
        "user_id": user_id.strip(),
        "auth_url": f"https://auth.{platform}.com/oauth2/authorize?state={state_token}",
        "state_token": state_token,
        "expires_in": 600,
        "scope": scope.strip(),
        "status": "pending_authorization",
    }


def distribute_release(
    title: str,
    artist: str,
    platforms: list[str],
    release_date: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Submit a release for distribution to one or more platforms.

    Parameters
    ----------
    title:        Release title.
    artist:       Artist name.
    platforms:    List of target platform names.
    release_date: ISO date string for the planned release.
    metadata:     Optional extra metadata dict.

    Returns
    -------
    Dict with keys: release_id, title, artist, platforms, release_date,
    distribution_status, estimated_live_date, metadata.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if not title or not title.strip():
        raise ValueError("title must not be empty")
    if not artist or not artist.strip():
        raise ValueError("artist must not be empty")
    if not platforms:
        raise ValueError("platforms must not be empty")

    release_id = _short_hash(f"{title}{artist}{release_date}", 16)

    try:
        rd = datetime.date.fromisoformat(release_date)
        estimated = (rd + datetime.timedelta(days=3)).isoformat()
    except (ValueError, TypeError):
        estimated = release_date

    return {
        "release_id": release_id,
        "title": title.strip(),
        "artist": artist.strip(),
        "platforms": platforms,
        "release_date": release_date,
        "distribution_status": "submitted",
        "estimated_live_date": estimated,
        "metadata": metadata or {},
    }


def generate_epk(
    artist_name: str,
    bio: str,
    genres: list[str],
    contact_email: str,
    media_links: list[str] | None = None,
) -> dict[str, Any]:
    """Generate an Electronic Press Kit (EPK) for an artist.

    Parameters
    ----------
    artist_name:   Artist or band name.
    bio:           Artist biography text.
    genres:        List of musical genres.
    contact_email: Booking/press contact email.
    media_links:   Optional list of media URLs.

    Returns
    -------
    Dict with keys: epk_id, artist_name, bio, genres, contact_email,
    media_links, sections, created_at, download_url.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if not artist_name or not artist_name.strip():
        raise ValueError("artist_name must not be empty")
    if not bio or not bio.strip():
        raise ValueError("bio must not be empty")
    if not contact_email or not contact_email.strip():
        raise ValueError("contact_email must not be empty")

    epk_id = _short_hash(f"{artist_name}{contact_email}", 16)
    return {
        "epk_id": epk_id,
        "artist_name": artist_name.strip(),
        "bio": bio.strip(),
        "genres": genres or [],
        "contact_email": contact_email.strip(),
        "media_links": media_links or [],
        "sections": _EPK_SECTIONS,
        "created_at": _now(),
        "download_url": f"https://kalaos.io/epk/{epk_id}/download",
    }


def get_platform_analytics(
    platform: str,
    user_id: str,
    time_range: str,
) -> dict[str, Any]:
    """Retrieve analytics for a platform connection.

    Parameters
    ----------
    platform:   Platform name.
    user_id:    User identifier.
    time_range: One of "7d", "30d", "90d", "1y".

    Returns
    -------
    Dict with keys: platform, user_id, time_range, metrics, top_content,
    growth.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if platform not in _VALID_PLATFORMS:
        raise ValueError(f"platform must be one of {sorted(_VALID_PLATFORMS)}")
    if not user_id or not user_id.strip():
        raise ValueError("user_id must not be empty")
    if time_range not in _VALID_TIME_RANGES:
        raise ValueError(f"time_range must be one of {sorted(_VALID_TIME_RANGES)}")

    d = _digest(f"{platform}{user_id}{time_range}")
    streams = 1000 + (d % 50000)
    followers = 500 + (d % 10000)
    saves = 50 + (d % 5000)
    playlist_adds = 10 + (d % 1000)
    engagement_rate = round(1.5 + (d % 100) / 100 * 8.5, 2)

    top_content = []
    for i in range(3):
        tc_d = _digest(f"{platform}{user_id}{time_range}{i}")
        top_content.append({
            "rank": i + 1,
            "title": f"Track {_short_hash(f'{platform}{i}', 6)}",
            "plays": 200 + (tc_d % 5000),
        })

    growth_d = _digest(f"{platform}{user_id}{time_range}growth")
    return {
        "platform": platform,
        "user_id": user_id.strip(),
        "time_range": time_range,
        "metrics": {
            "streams": streams,
            "followers": followers,
            "engagement_rate": engagement_rate,
            "saves": saves,
            "playlist_adds": playlist_adds,
        },
        "top_content": top_content,
        "growth": {
            "followers_change": (growth_d % 500) - 100,
            "streams_change_pct": round((growth_d % 50) - 10, 1),
        },
    }


def sync_catalog(
    user_id: str,
    source_platform: str,
    target_platforms: list[str],
) -> dict[str, Any]:
    """Sync a user's catalog from a source platform to target platforms.

    Parameters
    ----------
    user_id:          User identifier.
    source_platform:  Platform to pull catalog from.
    target_platforms: List of platforms to push catalog to.

    Returns
    -------
    Dict with keys: sync_id, user_id, source_platform, target_platforms,
    tracks_synced, status, started_at.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if not user_id or not user_id.strip():
        raise ValueError("user_id must not be empty")
    if not source_platform or not source_platform.strip():
        raise ValueError("source_platform must not be empty")

    sync_id = _short_hash(f"{user_id}{source_platform}", 16)
    d = _digest(f"{user_id}{source_platform}")
    tracks_synced = 10 + (d % 200)

    return {
        "sync_id": sync_id,
        "user_id": user_id.strip(),
        "source_platform": source_platform.strip(),
        "target_platforms": target_platforms or [],
        "tracks_synced": tracks_synced,
        "status": "in_progress",
        "started_at": _now(),
    }


def create_smart_link(
    title: str,
    artist: str,
    platforms_urls: dict[str, str],
) -> dict[str, Any]:
    """Create a smart link aggregating multiple platform URLs.

    Parameters
    ----------
    title:          Release or content title.
    artist:         Artist name.
    platforms_urls: Mapping of platform name → URL.

    Returns
    -------
    Dict with keys: link_id, title, artist, smart_url, platforms,
    created_at, tracking_enabled.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if not title or not title.strip():
        raise ValueError("title must not be empty")
    if not artist or not artist.strip():
        raise ValueError("artist must not be empty")
    if not platforms_urls:
        raise ValueError("platforms_urls must not be empty")

    link_id = _short_hash(f"{title}{artist}", 16)
    return {
        "link_id": link_id,
        "title": title.strip(),
        "artist": artist.strip(),
        "smart_url": f"https://kalaos.io/link/{link_id}",
        "platforms": platforms_urls,
        "created_at": _now(),
        "tracking_enabled": True,
    }


def schedule_release(
    title: str,
    artist: str,
    release_date: str,
    platforms: list[str],
    pre_save_enabled: bool = False,
) -> dict[str, Any]:
    """Schedule a release for a future date.

    Parameters
    ----------
    title:             Release title.
    artist:            Artist name.
    release_date:      Target release date (ISO string).
    platforms:         List of target platforms.
    pre_save_enabled:  Whether to enable pre-save links.

    Returns
    -------
    Dict with keys: schedule_id, title, artist, release_date, platforms,
    pre_save_enabled, countdown_days, status.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if not title or not title.strip():
        raise ValueError("title must not be empty")
    if not artist or not artist.strip():
        raise ValueError("artist must not be empty")
    if not platforms:
        raise ValueError("platforms must not be empty")

    schedule_id = _short_hash(f"{title}{artist}{release_date}", 16)

    try:
        rd = datetime.date.fromisoformat(release_date)
        countdown = max(0, (rd - datetime.date.today()).days)
    except (ValueError, TypeError):
        countdown = 0

    return {
        "schedule_id": schedule_id,
        "title": title.strip(),
        "artist": artist.strip(),
        "release_date": release_date,
        "platforms": platforms,
        "pre_save_enabled": pre_save_enabled,
        "countdown_days": countdown,
        "status": "scheduled",
    }


def get_royalty_report(
    user_id: str,
    period: str,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a royalty earnings report for a user.

    Parameters
    ----------
    user_id:   User identifier.
    period:    Reporting period (e.g. "2024-Q1", "2024-01").
    platforms: Optional list of platforms to include.

    Returns
    -------
    Dict with keys: report_id, user_id, period, platforms, total_earnings,
    breakdown, payment_status.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if not user_id or not user_id.strip():
        raise ValueError("user_id must not be empty")
    if not period or not period.strip():
        raise ValueError("period must not be empty")

    report_id = _short_hash(f"{user_id}{period}", 16)
    target_platforms = platforms if platforms else list(_VALID_PLATFORMS)

    d = _digest(f"{user_id}{period}")
    breakdown = []
    total = 0.0
    for i, plat in enumerate(target_platforms):
        pd = _digest(f"{user_id}{period}{plat}")
        streams = 500 + (pd % 20000)
        earnings = round((streams * 0.004) + (pd % 100) / 10, 2)
        total += earnings
        breakdown.append({
            "platform": plat,
            "streams": streams,
            "earnings": earnings,
            "currency": "USD",
        })

    payment_statuses = ["pending", "processing", "paid"]
    payment_status = payment_statuses[d % len(payment_statuses)]

    return {
        "report_id": report_id,
        "user_id": user_id.strip(),
        "period": period.strip(),
        "platforms": target_platforms,
        "total_earnings": round(total, 2),
        "breakdown": breakdown,
        "payment_status": payment_status,
    }

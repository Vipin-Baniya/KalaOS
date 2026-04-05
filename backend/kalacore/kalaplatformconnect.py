"""
KalaPlatformConnect – Platform Connect & Distribution Module
------------------------------------------------------------
Handles OAuth connections, distribution, EPK generation, analytics,
catalog sync, smart links, release scheduling, and royalty reporting
for external platforms. Provides functions for connecting music/content
platforms via OAuth, distributing content, retrieving analytics,
generating EPKs, and finding optimal release timing.

Public API
----------
connect_oauth_platform(platform, user_id, scope)
get_oauth_url(platform, user_id)
connect_platform(platform, user_id, auth_code)
disconnect_platform(platform, user_id)
get_connections(user_id)
get_connected_platforms(user_id)
distribute_release(title, artist, platforms, release_date, metadata)
distribute_to_platforms(user_id, platforms, content)
generate_epk(artist_name, bio, genres, contact_email, media_links)
generate_epk_for_user(user_id, artist_name, genre, bio)
get_platform_analytics(platform, user_id, time_range)
get_analytics_summary(user_id, platform)
sync_catalog(user_id, source_platform, target_platforms)
create_smart_link(title, artist, platforms_urls)
schedule_release(title, artist, release_date, platforms, pre_save_enabled)
get_royalty_report(user_id, period, platforms)
get_optimal_release_time(genre, target_region)
list_platforms()
"""

from __future__ import annotations

import datetime
import hashlib
import random
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Valid values / constants
# ---------------------------------------------------------------------------

_VALID_PLATFORMS: set[str] = {
    "spotify", "apple_music", "youtube", "instagram", "tiktok",
    "soundcloud", "bandcamp", "amazon_music", "deezer", "tidal",
    "twitter", "facebook", "twitch", "patreon", "discord",
}

_VALID_TIME_RANGES: set[str] = {"7d", "30d", "90d", "1y"}

_EPK_SECTIONS: list[str] = [
    "Biography", "Discography", "Press Photos",
    "Press Quotes", "Contact", "Rider",
]

_OAUTH_BASE_URLS: dict[str, str] = {
    "spotify":      "https://accounts.spotify.com/oauth",
    "apple_music":  "https://accounts.apple_music.com/oauth",
    "youtube":      "https://accounts.youtube.com/oauth",
    "instagram":    "https://accounts.instagram.com/oauth",
    "tiktok":       "https://accounts.tiktok.com/oauth",
    "soundcloud":   "https://accounts.soundcloud.com/oauth",
    "bandcamp":     "https://accounts.bandcamp.com/oauth",
    "amazon_music": "https://accounts.amazon_music.com/oauth",
    "deezer":       "https://accounts.deezer.com/oauth",
    "tidal":        "https://accounts.tidal.com/oauth",
    "twitter":      "https://accounts.twitter.com/oauth",
    "facebook":     "https://accounts.facebook.com/oauth",
    "twitch":       "https://accounts.twitch.com/oauth",
    "patreon":      "https://accounts.patreon.com/oauth",
    "discord":      "https://accounts.discord.com/oauth",
}

_PLATFORM_SCOPES: dict[str, str] = {
    "spotify":      "streaming user-read-playback-state user-library-read",
    "apple_music":  "music user-profile",
    "youtube":      "youtube.upload youtube.readonly",
    "instagram":    "basic media_publish",
    "tiktok":       "video.upload user.info.basic",
    "soundcloud":   "non-expiring",
    "bandcamp":     "fan_dashboard",
    "amazon_music": "music profile",
    "deezer":       "basic_access manage_library",
    "tidal":        "r_usr w_usr",
    "twitter":      "tweet.read tweet.write users.read",
    "facebook":     "pages_manage_posts pages_read_engagement",
    "twitch":       "channel:manage:broadcast clips:edit",
    "patreon":      "identity campaigns posts",
    "discord":      "identify guilds",
}

_PLATFORM_CLIENT_IDS: dict[str, str] = {
    "spotify":      "kalaos_spotify_client_id",
    "apple_music":  "kalaos_apple_music_client_id",
    "youtube":      "kalaos_youtube_client_id",
    "instagram":    "kalaos_instagram_client_id",
    "tiktok":       "kalaos_tiktok_client_id",
    "soundcloud":   "kalaos_soundcloud_client_id",
    "bandcamp":     "kalaos_bandcamp_client_id",
    "amazon_music": "kalaos_amazon_music_client_id",
    "deezer":       "kalaos_deezer_client_id",
    "tidal":        "kalaos_tidal_client_id",
    "twitter":      "kalaos_twitter_client_id",
    "facebook":     "kalaos_facebook_client_id",
    "twitch":       "kalaos_twitch_client_id",
    "patreon":      "kalaos_patreon_client_id",
    "discord":      "kalaos_discord_client_id",
}

_DEMO_PLATFORMS: list[str] = ["spotify", "youtube", "instagram", "tiktok", "soundcloud"]

_GENRE_RELEASE_INFO: dict[str, dict[str, Any]] = {
    "pop":        {"day": "Friday",    "reasoning": "Pop audiences peak on Fridays with playlist refreshes", "multiplier": 2.1},
    "hip-hop":    {"day": "Friday",    "reasoning": "Hip-hop drops on Fridays align with streaming chart cycles", "multiplier": 2.3},
    "rap":        {"day": "Friday",    "reasoning": "Rap releases on Fridays capture weekend listening sessions", "multiplier": 2.2},
    "rock":       {"day": "Friday",    "reasoning": "Rock fans discover new music on Fridays via editorial playlists", "multiplier": 1.8},
    "electronic": {"day": "Thursday",  "reasoning": "Electronic music gets mid-week traction ahead of weekend events", "multiplier": 1.9},
    "edm":        {"day": "Thursday",  "reasoning": "EDM releases Thursday to build hype for weekend club plays", "multiplier": 2.0},
    "jazz":       {"day": "Wednesday", "reasoning": "Jazz listeners engage mid-week during relaxed listening hours", "multiplier": 1.3},
    "classical":  {"day": "Wednesday", "reasoning": "Classical audiences prefer mid-week discovery sessions", "multiplier": 1.2},
    "r&b":        {"day": "Friday",    "reasoning": "R&B performs best on Fridays with new music Friday playlists", "multiplier": 2.0},
    "country":    {"day": "Friday",    "reasoning": "Country radio spins align with Friday release windows", "multiplier": 1.7},
    "latin":      {"day": "Thursday",  "reasoning": "Latin music benefits from Thursday releases for weekend parties", "multiplier": 1.9},
    "indie":      {"day": "Friday",    "reasoning": "Indie fans check new releases on Fridays via curated playlists", "multiplier": 1.6},
    "metal":      {"day": "Friday",    "reasoning": "Metal fans rally on Fridays around new album drops", "multiplier": 1.8},
    "folk":       {"day": "Wednesday", "reasoning": "Folk audiences discover music mid-week in reflective listening contexts", "multiplier": 1.4},
    "soul":       {"day": "Friday",    "reasoning": "Soul music resonates on Friday evenings with after-work listeners", "multiplier": 1.9},
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest(), 16)


def _short_hash(seed: str, length: int = 12) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()[:length]


def _validate_platform(platform: str) -> None:
    if platform not in _VALID_PLATFORMS:
        raise ValueError(
            f"platform must be one of {sorted(_VALID_PLATFORMS)}, got '{platform}'"
        )


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


def get_oauth_url(platform: str, user_id: str) -> dict[str, Any]:
    """Return an OAuth URL for the given platform.

    Parameters
    ----------
    platform: Target platform name.
    user_id:  Requesting user's ID.

    Returns
    -------
    Dict with platform, oauth_url, client_id, scope, state.

    Raises
    ------
    ValueError for unknown platforms.
    """
    _validate_platform(platform)
    state = f"kalaos_{user_id}_{platform}_{random.randint(100000, 999999)}"
    return {
        "platform":  platform,
        "oauth_url": _OAUTH_BASE_URLS[platform],
        "client_id": _PLATFORM_CLIENT_IDS[platform],
        "scope":     _PLATFORM_SCOPES[platform],
        "state":     state,
    }


def connect_platform(platform: str, user_id: str, auth_code: str) -> dict[str, Any]:
    """Simulate connecting a platform via OAuth auth code.

    Parameters
    ----------
    platform:  Target platform name.
    user_id:   User performing the connection.
    auth_code: OAuth authorization code.

    Returns
    -------
    Connection result dict.

    Raises
    ------
    ValueError for unknown platforms or empty inputs.
    """
    _validate_platform(platform)
    if not auth_code or not auth_code.strip():
        raise ValueError("auth_code must not be empty")
    return {
        "platform":     platform,
        "user_id":      user_id,
        "connected":    True,
        "username":     f"{platform}_user_{user_id[:6]}",
        "followers":    random.randint(1, 100000),
        "connected_at": _now(),
    }


def disconnect_platform(platform: str, user_id: str) -> dict[str, Any]:
    """Disconnect a previously connected platform.

    Parameters
    ----------
    platform: Target platform name.
    user_id:  User performing the disconnection.

    Returns
    -------
    Disconnection result dict.

    Raises
    ------
    ValueError for unknown platforms.
    """
    _validate_platform(platform)
    return {
        "platform":        platform,
        "user_id":         user_id,
        "connected":       False,
        "disconnected_at": _now(),
    }


def get_connected_platforms(user_id: str) -> dict[str, Any]:
    """Return the list of connected platforms for a user.

    Parameters
    ----------
    user_id: Target user ID.

    Returns
    -------
    Dict with user_id and a list of platform connection dicts.
    """
    platforms = [
        {
            "platform":  p,
            "connected": False,
            "username":  None,
            "followers": 0,
        }
        for p in _DEMO_PLATFORMS
    ]
    return {"user_id": user_id, "platforms": platforms}


def distribute_to_platforms(
    user_id: str,
    platforms: list[str],
    content: dict[str, Any],
) -> dict[str, Any]:
    """Queue content for distribution to multiple platforms.

    Parameters
    ----------
    user_id:   User initiating the distribution.
    platforms: Non-empty list of target platform names.
    content:   Dict with at least 'title' and 'type' keys.

    Returns
    -------
    Distribution manifest dict.

    Raises
    ------
    ValueError for empty platforms list or missing content fields.
    """
    if not platforms:
        raise ValueError("platforms must be a non-empty list")
    title = content.get("title", "track")
    distributed = [
        {
            "platform":  p,
            "status":    "queued",
            "track_url": f"https://{p}.com/{user_id}/tracks/{title}",
        }
        for p in platforms
    ]
    return {
        "user_id":        user_id,
        "distributed_to": distributed,
        "total":          len(platforms),
        "queued":         len(platforms),
    }


def get_analytics_summary(user_id: str, platform: str = "all") -> dict[str, Any]:
    """Return an analytics summary for a user, optionally filtered by platform.

    Parameters
    ----------
    user_id:  Target user ID.
    platform: Platform filter; defaults to "all".

    Returns
    -------
    Analytics summary dict.
    """
    return {
        "user_id":          user_id,
        "platform":         platform,
        "total_plays":      random.randint(100, 1_000_000),
        "total_followers":  random.randint(100, 50_000),
        "total_revenue_usd": round(random.uniform(10, 5000), 2),
        "growth_pct":       round(random.uniform(-20, 50), 1),
        "top_content": [
            {"title": "Track 1", "plays": random.randint(50, 500_000)},
            {"title": "Track 2", "plays": random.randint(50, 500_000)},
        ],
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


def generate_epk_for_user(
    user_id: str,
    artist_name: str,
    genre: str,
    bio: str,
) -> dict[str, Any]:
    """Generate an Electronic Press Kit for a user/artist (user-centric variant).

    Parameters
    ----------
    user_id:     User/artist ID.
    artist_name: Artist's display name.
    genre:       Musical genre.
    bio:         Artist biography text.

    Returns
    -------
    EPK manifest dict.

    Raises
    ------
    ValueError for empty required fields.
    """
    if not artist_name or not artist_name.strip():
        raise ValueError("artist_name must not be empty")
    if not genre or not genre.strip():
        raise ValueError("genre must not be empty")
    if not bio or not bio.strip():
        raise ValueError("bio must not be empty")
    return {
        "user_id":       user_id,
        "artist_name":   artist_name.strip(),
        "genre":         genre.strip(),
        "bio":           bio.strip(),
        "epk_url":       f"https://kalaos.com/epk/{user_id}",
        "sections":      ["biography", "discography", "press_photos", "contact_info", "social_links"],
        "generated_at":  _now(),
        "word_count":    len(bio.split()),
        "status":        "generated",
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


def get_optimal_release_time(
    genre: str,
    target_region: str = "global",
) -> dict[str, Any]:
    """Return optimal release day and time for the given genre and region.

    Parameters
    ----------
    genre:         Musical genre.
    target_region: Target audience region (default: "global").

    Returns
    -------
    Release timing recommendation dict.
    """
    genre_lower = genre.lower().strip()
    info = _GENRE_RELEASE_INFO.get(genre_lower, {
        "day":        "Friday",
        "reasoning":  f"Friday releases maximize visibility for {genre} on new music playlists",
        "multiplier": round(random.uniform(1.1, 2.5), 1),
    })
    return {
        "genre":                    genre,
        "target_region":            target_region,
        "optimal_day":              info["day"],
        "optimal_time_utc":         "14:00",
        "reasoning":                info["reasoning"],
        "predicted_reach_multiplier": info["multiplier"],
    }

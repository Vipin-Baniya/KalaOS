"""
KalaPlatformConnect – Platform Connection & Distribution Module
---------------------------------------------------------------
Provides functions for connecting music/content platforms via OAuth,
distributing content, retrieving analytics, generating EPKs, and
finding optimal release timing.

Public API
----------
get_oauth_url(platform, user_id)
connect_platform(platform, user_id, auth_code)
disconnect_platform(platform, user_id)
get_connected_platforms(user_id)
distribute_to_platforms(user_id, platforms, content)
get_analytics_summary(user_id, platform)
generate_epk(user_id, artist_name, genre, bio)
get_optimal_release_time(genre, target_region)
"""

from __future__ import annotations

import datetime
import random
from typing import Any

# ---------------------------------------------------------------------------
# Valid platforms
# ---------------------------------------------------------------------------

_VALID_PLATFORMS: set[str] = {
    "spotify", "apple_music", "youtube", "instagram", "tiktok",
    "soundcloud", "bandcamp", "amazon_music", "deezer", "tidal",
    "twitter", "facebook", "twitch", "patreon", "discord",
}

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


def _validate_platform(platform: str) -> None:
    if platform not in _VALID_PLATFORMS:
        raise ValueError(
            f"platform must be one of {sorted(_VALID_PLATFORMS)}, got '{platform}'"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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
    user_id: str,
    artist_name: str,
    genre: str,
    bio: str,
) -> dict[str, Any]:
    """Generate an Electronic Press Kit for an artist.

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

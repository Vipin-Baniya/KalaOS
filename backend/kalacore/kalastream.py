"""
KalaStream – Live Streaming Configuration Module
-------------------------------------------------
Provides functions for configuring live streams, retrieving analytics,
and generating stream overlay configurations.

Public API
----------
setup_stream(platform, title, quality, description)
    Returns a stream configuration dict.

get_stream_analytics(stream_id, duration_minutes)
    Returns a stream analytics dict.

generate_stream_overlay(title, style)
    Returns an overlay configuration dict.
"""

from __future__ import annotations

import datetime
import hashlib
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Valid values
# ---------------------------------------------------------------------------

_VALID_PLATFORMS: set[str] = {"youtube", "twitch", "facebook", "instagram", "tiktok"}
_VALID_QUALITIES: set[str] = {"480p", "720p", "1080p", "1440p", "4k"}
_VALID_OVERLAY_STYLES: set[str] = {"minimal", "gaming", "podcast", "creative"}

# ---------------------------------------------------------------------------
# Platform RTMP base URLs (public, non-secret)
# ---------------------------------------------------------------------------

_PLATFORM_RTMP: dict[str, str] = {
    "youtube":   "rtmp://a.rtmp.youtube.com/live2",
    "twitch":    "rtmp://live.twitch.tv/app",
    "facebook":  "rtmps://live-api-s.facebook.com:443/rtmp",
    "instagram": "rtmps://live-upload.instagram.com:443/rtmp",
    "tiktok":    "rtmp://push.tiktokv.com/rtmp",
}

# ---------------------------------------------------------------------------
# Quality → bitrate / resolution settings
# ---------------------------------------------------------------------------

_QUALITY_SETTINGS: dict[str, dict[str, Any]] = {
    "480p":  {"resolution": "854x480",   "video_bitrate_kbps": 1500,  "audio_bitrate_kbps": 128, "fps": 30},
    "720p":  {"resolution": "1280x720",  "video_bitrate_kbps": 3000,  "audio_bitrate_kbps": 192, "fps": 30},
    "1080p": {"resolution": "1920x1080", "video_bitrate_kbps": 6000,  "audio_bitrate_kbps": 256, "fps": 60},
    "1440p": {"resolution": "2560x1440", "video_bitrate_kbps": 9000,  "audio_bitrate_kbps": 320, "fps": 60},
    "4k":    {"resolution": "3840x2160", "video_bitrate_kbps": 15000, "audio_bitrate_kbps": 320, "fps": 60},
}

# ---------------------------------------------------------------------------
# Overlay style → visual elements
# ---------------------------------------------------------------------------

_OVERLAY_TEMPLATES: dict[str, dict[str, Any]] = {
    "minimal": {
        "elements": ["title_bar", "viewer_count", "elapsed_time"],
        "colors":   {"primary": "#FFFFFF", "secondary": "#000000", "accent": "#888888"},
        "fonts":    {"title": "Inter", "body": "Inter"},
    },
    "gaming": {
        "elements": ["title_bar", "viewer_count", "chat_ticker", "health_bar", "score_panel", "alert_banner"],
        "colors":   {"primary": "#00FF00", "secondary": "#1A1A1A", "accent": "#FF4500"},
        "fonts":    {"title": "Press Start 2P", "body": "Roboto Mono"},
    },
    "podcast": {
        "elements": ["title_bar", "guest_nameplate", "topic_ticker", "viewer_count", "social_handles"],
        "colors":   {"primary": "#F4A261", "secondary": "#264653", "accent": "#E9C46A"},
        "fonts":    {"title": "Playfair Display", "body": "Lato"},
    },
    "creative": {
        "elements": ["animated_title", "palette_strip", "viewer_count", "social_handles", "progress_bar", "alert_banner"],
        "colors":   {"primary": "#FF006E", "secondary": "#3A0CA3", "accent": "#4CC9F0"},
        "fonts":    {"title": "Space Grotesk", "body": "DM Sans"},
    },
}


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _deterministic_int(seed: str, lo: int, hi: int) -> int:
    """Return a deterministic int in [lo, hi] based on seed."""
    digest = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return lo + (digest % (hi - lo + 1))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def setup_stream(
    platform: str,
    title: str,
    quality: str,
    description: str = "",
) -> dict[str, Any]:
    """Set up a live-stream configuration.

    Parameters
    ----------
    platform:    Target streaming platform.
    title:       Stream title.
    quality:     Output quality setting.
    description: Optional stream description.

    Returns
    -------
    Stream config dict with keys: stream_id, platform, title, quality,
    description, rtmp_url, stream_key, settings.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if platform not in _VALID_PLATFORMS:
        raise ValueError(f"platform must be one of {sorted(_VALID_PLATFORMS)}")
    if not title or not title.strip():
        raise ValueError("title must not be empty")
    if quality not in _VALID_QUALITIES:
        raise ValueError(f"quality must be one of {sorted(_VALID_QUALITIES)}")

    stream_id = str(uuid.uuid4())
    stream_key = hashlib.sha256(f"{platform}{title}{stream_id}".encode()).hexdigest()[:32]

    return {
        "stream_id": stream_id,
        "platform": platform,
        "title": title.strip(),
        "quality": quality,
        "description": description.strip() if description else "",
        "rtmp_url": _PLATFORM_RTMP[platform],
        "stream_key": stream_key,
        "settings": _QUALITY_SETTINGS[quality],
    }


def get_stream_analytics(
    stream_id: str,
    duration_minutes: int = 60,
) -> dict[str, Any]:
    """Return analytics for a completed or in-progress stream.

    Parameters
    ----------
    stream_id:        ID of the stream.
    duration_minutes: Duration to analyse (must be > 0).

    Returns
    -------
    Analytics dict with keys: stream_id, duration_minutes, peak_viewers,
    avg_viewers, total_views, engagement_rate, donations, chat_messages,
    new_followers.

    Raises
    ------
    ValueError for invalid inputs.
    """
    if not stream_id or not stream_id.strip():
        raise ValueError("stream_id must not be empty")
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be greater than 0")

    sid = stream_id.strip()
    peak  = _deterministic_int(sid + "peak",  100, 50000)
    avg   = _deterministic_int(sid + "avg",   50,  peak)
    total = avg * duration_minutes
    eng   = round(_deterministic_int(sid + "eng", 2, 35) / 100, 4)
    dona  = _deterministic_int(sid + "dona",  0, 500)
    chat  = _deterministic_int(sid + "chat",  duration_minutes * 5, duration_minutes * 200)
    follow = _deterministic_int(sid + "follow", 10, 2000)

    return {
        "stream_id": sid,
        "duration_minutes": duration_minutes,
        "peak_viewers": peak,
        "avg_viewers": avg,
        "total_views": total,
        "engagement_rate": eng,
        "donations": dona,
        "chat_messages": chat,
        "new_followers": follow,
    }


def generate_stream_overlay(
    title: str,
    style: str,
) -> dict[str, Any]:
    """Generate a stream overlay configuration.

    Parameters
    ----------
    title: Overlay title text.
    style: Visual style for the overlay.

    Returns
    -------
    Overlay config dict with keys: title, style, elements, colors, fonts.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if not title or not title.strip():
        raise ValueError("title must not be empty")
    if style not in _VALID_OVERLAY_STYLES:
        raise ValueError(f"style must be one of {sorted(_VALID_OVERLAY_STYLES)}")

    template = _OVERLAY_TEMPLATES[style]
    return {
        "title": title.strip(),
        "style": style,
        "elements": list(template["elements"]),
        "colors": dict(template["colors"]),
        "fonts": dict(template["fonts"]),
    }

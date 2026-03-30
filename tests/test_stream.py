"""Tests for kalastream module and /stream/* endpoints."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient
from main import app
from kalacore.kalastream import setup_stream, get_stream_analytics, generate_stream_overlay

client = TestClient(app)


# ---------------------------------------------------------------------------
# setup_stream – unit tests
# ---------------------------------------------------------------------------

def test_setup_stream_valid():
    cfg = setup_stream("youtube", "My Stream", "1080p", "A fun stream")
    assert cfg["platform"] == "youtube"
    assert cfg["title"] == "My Stream"
    assert cfg["quality"] == "1080p"
    assert "stream_id" in cfg
    assert "rtmp_url" in cfg
    assert "stream_key" in cfg
    assert "settings" in cfg
    assert cfg["settings"]["resolution"] == "1920x1080"


def test_setup_stream_all_platforms():
    for platform in ("youtube", "twitch", "facebook", "instagram", "tiktok"):
        cfg = setup_stream(platform, "Title", "720p")
        assert cfg["platform"] == platform
        assert "rtmp_url" in cfg


def test_setup_stream_all_qualities():
    for quality in ("480p", "720p", "1080p", "1440p", "4k"):
        cfg = setup_stream("twitch", "Title", quality)
        assert cfg["quality"] == quality


def test_setup_stream_invalid_platform():
    with pytest.raises(ValueError, match="platform"):
        setup_stream("discord", "Title", "720p")


def test_setup_stream_invalid_quality():
    with pytest.raises(ValueError, match="quality"):
        setup_stream("twitch", "Title", "8k")


def test_setup_stream_empty_title():
    with pytest.raises(ValueError, match="title"):
        setup_stream("youtube", "", "720p")


def test_setup_stream_whitespace_title():
    with pytest.raises(ValueError, match="title"):
        setup_stream("youtube", "   ", "720p")


def test_setup_stream_unique_ids():
    c1 = setup_stream("twitch", "Same Title", "720p")
    c2 = setup_stream("twitch", "Same Title", "720p")
    assert c1["stream_id"] != c2["stream_id"]


# ---------------------------------------------------------------------------
# get_stream_analytics – unit tests
# ---------------------------------------------------------------------------

def test_get_stream_analytics_valid():
    a = get_stream_analytics("stream-abc-123", 60)
    assert a["stream_id"] == "stream-abc-123"
    assert a["duration_minutes"] == 60
    assert a["peak_viewers"] >= a["avg_viewers"]
    assert "engagement_rate" in a
    assert "donations" in a
    assert "chat_messages" in a
    assert "new_followers" in a


def test_get_stream_analytics_deterministic():
    a1 = get_stream_analytics("stream-xyz", 30)
    a2 = get_stream_analytics("stream-xyz", 30)
    assert a1["peak_viewers"] == a2["peak_viewers"]
    assert a1["avg_viewers"] == a2["avg_viewers"]


def test_get_stream_analytics_invalid_stream_id():
    with pytest.raises(ValueError, match="stream_id"):
        get_stream_analytics("")


def test_get_stream_analytics_invalid_duration():
    with pytest.raises(ValueError, match="duration_minutes"):
        get_stream_analytics("stream-abc", 0)


# ---------------------------------------------------------------------------
# generate_stream_overlay – unit tests
# ---------------------------------------------------------------------------

def test_generate_stream_overlay_valid():
    overlay = generate_stream_overlay("Game Night", "gaming")
    assert overlay["title"] == "Game Night"
    assert overlay["style"] == "gaming"
    assert isinstance(overlay["elements"], list)
    assert isinstance(overlay["colors"], dict)
    assert isinstance(overlay["fonts"], dict)


def test_generate_stream_overlay_all_styles():
    for style in ("minimal", "gaming", "podcast", "creative"):
        o = generate_stream_overlay("Test", style)
        assert o["style"] == style
        assert len(o["elements"]) > 0


def test_generate_stream_overlay_invalid_style():
    with pytest.raises(ValueError, match="style"):
        generate_stream_overlay("Title", "neon")


def test_generate_stream_overlay_empty_title():
    with pytest.raises(ValueError, match="title"):
        generate_stream_overlay("", "minimal")


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

def test_api_stream_setup():
    resp = client.post("/stream/setup", json={
        "platform": "twitch",
        "title": "My Twitch Stream",
        "quality": "1080p",
        "description": "Live coding session",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["platform"] == "twitch"
    assert data["title"] == "My Twitch Stream"
    assert "stream_key" in data


def test_api_stream_setup_invalid_platform():
    resp = client.post("/stream/setup", json={
        "platform": "discord",
        "title": "Title",
        "quality": "720p",
    })
    assert resp.status_code == 422


def test_api_stream_setup_invalid_quality():
    resp = client.post("/stream/setup", json={
        "platform": "youtube",
        "title": "Title",
        "quality": "360p",
    })
    assert resp.status_code == 422


def test_api_stream_analytics():
    resp = client.get("/stream/test-stream-001/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stream_id"] == "test-stream-001"
    assert data["duration_minutes"] == 60  # default
    assert "peak_viewers" in data
    assert "avg_viewers" in data
    assert "engagement_rate" in data
    assert "donations" in data
    assert "chat_messages" in data
    assert "new_followers" in data
    assert data["peak_viewers"] >= data["avg_viewers"]


def test_api_stream_analytics_custom_duration():
    resp = client.get("/stream/test-stream-001/analytics?duration_minutes=30")
    assert resp.status_code == 200
    data = resp.json()
    assert data["duration_minutes"] == 30


def test_api_stream_overlay():
    resp = client.post("/stream/overlay", json={
        "title": "Podcast Live",
        "style": "podcast",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["style"] == "podcast"
    assert "elements" in data


def test_api_stream_overlay_invalid_style():
    resp = client.post("/stream/overlay", json={
        "title": "Title",
        "style": "unknown_style",
    })
    assert resp.status_code == 422

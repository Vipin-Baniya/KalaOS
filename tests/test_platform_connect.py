"""Tests for kalaplatformconnect module, platform-connect/studio and /platform-connect/* endpoints."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient
from main import app
from kalacore.kalaplatformconnect import (
    connect_oauth_platform,
    distribute_release,
    generate_epk,
    get_platform_analytics,
    sync_catalog,
    create_smart_link,
    schedule_release,
    get_royalty_report,
    get_oauth_url,
    connect_platform,
    disconnect_platform,
    get_connected_platforms,
    distribute_to_platforms,
    get_analytics_summary,
    get_optimal_release_time,
    _VALID_PLATFORMS,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# connect_oauth_platform – unit tests
# ---------------------------------------------------------------------------

def test_connect_oauth_valid():
    result = connect_oauth_platform("spotify", "user123", "streaming:read")
    assert result["platform"] == "spotify"
    assert result["user_id"] == "user123"
    assert result["status"] == "pending_authorization"
    assert "auth_url" in result
    assert "state_token" in result
    assert "expires_in" in result
    assert result["scope"] == "streaming:read"


def test_connect_oauth_all_platforms():
    platforms = ["spotify", "youtube", "soundcloud", "instagram", "tiktok", "twitter", "bandcamp", "distrokid"]
    for p in platforms:
        r = connect_oauth_platform(p, "user1", "read")
        assert r["platform"] == p
        assert r["status"] == "pending_authorization"


def test_connect_oauth_invalid_platform():
    with pytest.raises(ValueError, match="platform"):
        connect_oauth_platform("napster", "user1", "read")


def test_connect_oauth_empty_user_id():
    with pytest.raises(ValueError, match="user_id"):
        connect_oauth_platform("spotify", "", "read")


def test_connect_oauth_whitespace_user_id():
    with pytest.raises(ValueError, match="user_id"):
        connect_oauth_platform("spotify", "   ", "read")


def test_connect_oauth_empty_scope():
    with pytest.raises(ValueError, match="scope"):
        connect_oauth_platform("spotify", "user1", "")


def test_connect_oauth_state_token_present():
    r = connect_oauth_platform("youtube", "alice", "upload:write")
    assert len(r["state_token"]) == 32
    assert r["expires_in"] == 600


# ---------------------------------------------------------------------------
# distribute_release – unit tests
# ---------------------------------------------------------------------------

def test_distribute_release_valid():
    r = distribute_release("My Album", "Artist One", ["spotify", "youtube"], "2025-06-01", {})
    assert r["title"] == "My Album"
    assert r["artist"] == "Artist One"
    assert r["distribution_status"] == "submitted"
    assert "release_id" in r
    assert "estimated_live_date" in r


def test_distribute_release_estimated_date_plus_3():
    r = distribute_release("EP", "Band", ["spotify"], "2025-07-01", {})
    assert r["estimated_live_date"] == "2025-07-04"


def test_distribute_release_empty_title():
    with pytest.raises(ValueError, match="title"):
        distribute_release("", "Artist", ["spotify"], "2025-01-01", {})


def test_distribute_release_empty_artist():
    with pytest.raises(ValueError, match="artist"):
        distribute_release("Title", "", ["spotify"], "2025-01-01", {})


def test_distribute_release_empty_platforms():
    with pytest.raises(ValueError, match="platforms"):
        distribute_release("Title", "Artist", [], "2025-01-01", {})


def test_distribute_release_metadata_passed():
    meta = {"label": "Indie Records", "genre": "pop"}
    r = distribute_release("Track", "Artist", ["spotify"], "2025-01-01", meta)
    assert r["metadata"]["label"] == "Indie Records"


def test_distribute_release_multiple_platforms():
    platforms = ["spotify", "youtube", "tiktok"]
    r = distribute_release("Single", "DJ", platforms, "2025-03-15", {})
    assert r["platforms"] == platforms


# ---------------------------------------------------------------------------
# generate_epk – unit tests
# ---------------------------------------------------------------------------

def test_generate_epk_valid():
    r = generate_epk("Cool Band", "We rock.", ["rock", "indie"], "booking@cool.com", [])
    assert r["artist_name"] == "Cool Band"
    assert r["bio"] == "We rock."
    assert r["contact_email"] == "booking@cool.com"
    assert "epk_id" in r
    assert "download_url" in r
    assert "created_at" in r
    assert r["sections"] == ["Biography", "Discography", "Press Photos", "Press Quotes", "Contact", "Rider"]


def test_generate_epk_empty_artist_name():
    with pytest.raises(ValueError, match="artist_name"):
        generate_epk("", "Bio text", ["rock"], "a@b.com")


def test_generate_epk_empty_bio():
    with pytest.raises(ValueError, match="bio"):
        generate_epk("Artist", "", ["rock"], "a@b.com")


def test_generate_epk_empty_contact_email():
    with pytest.raises(ValueError, match="contact_email"):
        generate_epk("Artist", "Bio", ["rock"], "")


def test_generate_epk_media_links():
    links = ["http://youtube.com/1", "http://soundcloud.com/2"]
    r = generate_epk("Band", "Bio text", [], "contact@band.com", links)
    assert r["media_links"] == links


def test_generate_epk_no_genres():
    r = generate_epk("Band", "Bio text", [], "contact@band.com")
    assert r["genres"] == []


# ---------------------------------------------------------------------------
# get_platform_analytics – unit tests
# ---------------------------------------------------------------------------

def test_get_platform_analytics_valid():
    r = get_platform_analytics("spotify", "user1", "30d")
    assert r["platform"] == "spotify"
    assert r["user_id"] == "user1"
    assert r["time_range"] == "30d"
    assert "metrics" in r
    assert "streams" in r["metrics"]
    assert "followers" in r["metrics"]
    assert "engagement_rate" in r["metrics"]
    assert "saves" in r["metrics"]
    assert "playlist_adds" in r["metrics"]
    assert "top_content" in r
    assert "growth" in r


def test_get_platform_analytics_all_time_ranges():
    for tr in ("7d", "30d", "90d", "1y"):
        r = get_platform_analytics("youtube", "user2", tr)
        assert r["time_range"] == tr


def test_get_platform_analytics_invalid_platform():
    with pytest.raises(ValueError, match="platform"):
        get_platform_analytics("myspace", "user1", "30d")


def test_get_platform_analytics_invalid_time_range():
    with pytest.raises(ValueError, match="time_range"):
        get_platform_analytics("spotify", "user1", "2y")


def test_get_platform_analytics_empty_user_id():
    with pytest.raises(ValueError, match="user_id"):
        get_platform_analytics("spotify", "", "30d")


def test_get_platform_analytics_top_content_length():
    r = get_platform_analytics("tiktok", "user5", "7d")
    assert len(r["top_content"]) == 3


# ---------------------------------------------------------------------------
# sync_catalog – unit tests
# ---------------------------------------------------------------------------

def test_sync_catalog_valid():
    r = sync_catalog("user1", "spotify", ["youtube", "soundcloud"])
    assert r["user_id"] == "user1"
    assert r["source_platform"] == "spotify"
    assert r["target_platforms"] == ["youtube", "soundcloud"]
    assert "sync_id" in r
    assert "tracks_synced" in r
    assert r["status"] == "in_progress"
    assert "started_at" in r


def test_sync_catalog_empty_user_id():
    with pytest.raises(ValueError, match="user_id"):
        sync_catalog("", "spotify", [])


def test_sync_catalog_empty_source_platform():
    with pytest.raises(ValueError, match="source_platform"):
        sync_catalog("user1", "", ["youtube"])


def test_sync_catalog_no_target_platforms():
    r = sync_catalog("user1", "spotify", [])
    assert r["target_platforms"] == []


# ---------------------------------------------------------------------------
# create_smart_link – unit tests
# ---------------------------------------------------------------------------

def test_create_smart_link_valid():
    r = create_smart_link("My Track", "DJ Cool", {"spotify": "http://sp.co/1", "youtube": "http://yt.co/1"})
    assert r["title"] == "My Track"
    assert r["artist"] == "DJ Cool"
    assert "link_id" in r
    assert "smart_url" in r
    assert r["tracking_enabled"] is True
    assert "created_at" in r


def test_create_smart_link_empty_title():
    with pytest.raises(ValueError, match="title"):
        create_smart_link("", "Artist", {"spotify": "url"})


def test_create_smart_link_empty_artist():
    with pytest.raises(ValueError, match="artist"):
        create_smart_link("Title", "", {"spotify": "url"})


def test_create_smart_link_empty_platforms_urls():
    with pytest.raises(ValueError, match="platforms_urls"):
        create_smart_link("Title", "Artist", {})


def test_create_smart_link_url_in_result():
    r = create_smart_link("Song", "Band", {"spotify": "https://spotify.com/track/abc"})
    assert "kalaos.io/link/" in r["smart_url"]


# ---------------------------------------------------------------------------
# schedule_release – unit tests
# ---------------------------------------------------------------------------

def test_schedule_release_valid():
    r = schedule_release("Album Drop", "Artist X", "2026-01-01", ["spotify", "youtube"], True)
    assert r["title"] == "Album Drop"
    assert r["artist"] == "Artist X"
    assert r["status"] == "scheduled"
    assert r["pre_save_enabled"] is True
    assert "schedule_id" in r
    assert "countdown_days" in r


def test_schedule_release_empty_title():
    with pytest.raises(ValueError, match="title"):
        schedule_release("", "Artist", "2026-01-01", ["spotify"])


def test_schedule_release_empty_artist():
    with pytest.raises(ValueError, match="artist"):
        schedule_release("Title", "", "2026-01-01", ["spotify"])


def test_schedule_release_empty_platforms():
    with pytest.raises(ValueError, match="platforms"):
        schedule_release("Title", "Artist", "2026-01-01", [])


def test_schedule_release_countdown_non_negative():
    r = schedule_release("Title", "Artist", "2020-01-01", ["spotify"])
    assert r["countdown_days"] == 0


# ---------------------------------------------------------------------------
# get_royalty_report – unit tests
# ---------------------------------------------------------------------------

def test_get_royalty_report_valid():
    r = get_royalty_report("user1", "2024-Q1", ["spotify", "youtube"])
    assert r["user_id"] == "user1"
    assert r["period"] == "2024-Q1"
    assert "report_id" in r
    assert "total_earnings" in r
    assert "breakdown" in r
    assert "payment_status" in r
    assert isinstance(r["breakdown"], list)


def test_get_royalty_report_breakdown_structure():
    r = get_royalty_report("user2", "2024-Q2", ["spotify"])
    b = r["breakdown"][0]
    assert "platform" in b
    assert "streams" in b
    assert "earnings" in b
    assert "currency" in b
    assert b["currency"] == "USD"


def test_get_royalty_report_all_platforms_default():
    r = get_royalty_report("user3", "2024-Q3", None)
    assert len(r["breakdown"]) == 8  # all 8 platforms


def test_get_royalty_report_empty_user_id():
    with pytest.raises(ValueError, match="user_id"):
        get_royalty_report("", "2024-Q1")


def test_get_royalty_report_empty_period():
    with pytest.raises(ValueError, match="period"):
        get_royalty_report("user1", "")


def test_get_royalty_report_total_earnings_sum():
    r = get_royalty_report("user4", "2024-Q4", ["spotify", "youtube"])
    total = sum(b["earnings"] for b in r["breakdown"])
    assert abs(r["total_earnings"] - total) < 0.01


# ---------------------------------------------------------------------------
# /platform-connect/oauth API tests
# ---------------------------------------------------------------------------

def test_api_oauth_valid():
    resp = client.post("/platform-connect/oauth", json={
        "platform": "spotify",
        "user_id": "user123",
        "scope": "streaming:read",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["platform"] == "spotify"
    assert data["status"] == "pending_authorization"


def test_api_oauth_invalid_platform():
    resp = client.post("/platform-connect/oauth", json={
        "platform": "napster",
        "user_id": "user1",
        "scope": "read",
    })
    assert resp.status_code == 422


def test_api_oauth_empty_user_id():
    resp = client.post("/platform-connect/oauth", json={
        "platform": "spotify",
        "user_id": "",
        "scope": "read",
    })
    assert resp.status_code == 422


def test_api_oauth_empty_scope():
    resp = client.post("/platform-connect/oauth", json={
        "platform": "spotify",
        "user_id": "user1",
        "scope": "",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /platform-connect/distribute API tests
# ---------------------------------------------------------------------------

def test_api_distribute_valid():
    resp = client.post("/platform-connect/distribute", json={
        "title": "My EP",
        "artist": "Band X",
        "platforms": ["spotify"],
        "release_date": "2025-08-01",
        "metadata": {},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["distribution_status"] == "submitted"


def test_api_distribute_empty_title():
    resp = client.post("/platform-connect/distribute", json={
        "title": "",
        "artist": "Artist",
        "platforms": ["spotify"],
        "release_date": "2025-01-01",
    })
    assert resp.status_code == 422


def test_api_distribute_empty_platforms():
    resp = client.post("/platform-connect/distribute", json={
        "title": "Song",
        "artist": "Artist",
        "platforms": [],
        "release_date": "2025-01-01",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /platform-connect/epk API tests
# ---------------------------------------------------------------------------

def test_api_epk_valid():
    resp = client.post("/platform-connect/epk", json={
        "artist_name": "The Waves",
        "bio": "A great band from the coast.",
        "genres": ["indie", "surf"],
        "contact_email": "waves@music.com",
        "media_links": [],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["artist_name"] == "The Waves"
    assert len(data["sections"]) == 6


def test_api_epk_missing_bio():
    resp = client.post("/platform-connect/epk", json={
        "artist_name": "Band",
        "bio": "",
        "genres": [],
        "contact_email": "a@b.com",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /platform-connect/analytics API tests
# ---------------------------------------------------------------------------

def test_api_analytics_valid():
    resp = client.post("/platform-connect/analytics", json={
        "platform": "youtube",
        "user_id": "creator99",
        "time_range": "90d",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["platform"] == "youtube"
    assert "metrics" in data


def test_api_analytics_invalid_time_range():
    resp = client.post("/platform-connect/analytics", json={
        "platform": "spotify",
        "user_id": "user1",
        "time_range": "2y",
    })
    assert resp.status_code == 422


def test_api_analytics_invalid_platform():
    resp = client.post("/platform-connect/analytics", json={
        "platform": "myspace",
        "user_id": "user1",
        "time_range": "30d",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /platform-connect/sync-catalog API tests
# ---------------------------------------------------------------------------

def test_api_sync_catalog_valid():
    resp = client.post("/platform-connect/sync-catalog", json={
        "user_id": "user1",
        "source_platform": "spotify",
        "target_platforms": ["youtube"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "in_progress"


def test_api_sync_catalog_empty_user_id():
    resp = client.post("/platform-connect/sync-catalog", json={
        "user_id": "",
        "source_platform": "spotify",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /platform-connect/smart-link API tests
# ---------------------------------------------------------------------------

def test_api_smart_link_valid():
    resp = client.post("/platform-connect/smart-link", json={
        "title": "Summer Hit",
        "artist": "Sunny Days",
        "platforms_urls": {"spotify": "https://sp.co/1"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracking_enabled"] is True
    assert "smart_url" in data


def test_api_smart_link_empty_platforms_urls():
    resp = client.post("/platform-connect/smart-link", json={
        "title": "Track",
        "artist": "Artist",
        "platforms_urls": {},
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /platform-connect/schedule-release API tests
# ---------------------------------------------------------------------------

def test_api_schedule_release_valid():
    resp = client.post("/platform-connect/schedule-release", json={
        "title": "Big Drop",
        "artist": "DJ X",
        "release_date": "2026-06-15",
        "platforms": ["spotify", "tiktok"],
        "pre_save_enabled": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "scheduled"
    assert data["pre_save_enabled"] is True


def test_api_schedule_release_empty_platforms():
    resp = client.post("/platform-connect/schedule-release", json={
        "title": "Track",
        "artist": "Artist",
        "release_date": "2026-01-01",
        "platforms": [],
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /platform-connect/royalty-report API tests
# ---------------------------------------------------------------------------

def test_api_royalty_report_valid():
    resp = client.post("/platform-connect/royalty-report", json={
        "user_id": "artist1",
        "period": "2024-Q2",
        "platforms": ["spotify"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "artist1"
    assert "total_earnings" in data
    assert isinstance(data["breakdown"], list)


def test_api_royalty_report_empty_user_id():
    resp = client.post("/platform-connect/royalty-report", json={
        "user_id": "",
        "period": "2024-Q1",
    })
    assert resp.status_code == 422


def test_api_royalty_report_empty_period():
    resp = client.post("/platform-connect/royalty-report", json={
        "user_id": "user1",
        "period": "",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /music-studio/sampler-bank API tests
# ---------------------------------------------------------------------------

def test_api_sampler_bank_valid():
    resp = client.post("/music-studio/sampler-bank", json={
        "prompt": "dark trap beats",
        "kit_style": "electronic",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "bank_id" in data
    assert len(data["samples"]) == 8
    assert "bpm" in data
    assert "kit_name" in data


def test_api_sampler_bank_default_style():
    resp = client.post("/music-studio/sampler-bank", json={
        "prompt": "warm acoustic samples",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["samples"][0]["name"].startswith("acoustic_")


def test_api_sampler_bank_all_kit_styles():
    for style in ("acoustic", "electronic", "hip-hop", "jazz", "orchestral"):
        resp = client.post("/music-studio/sampler-bank", json={"prompt": "test", "kit_style": style})
        assert resp.status_code == 200


def test_api_sampler_bank_invalid_kit_style():
    resp = client.post("/music-studio/sampler-bank", json={
        "prompt": "test",
        "kit_style": "country",
    })
    assert resp.status_code == 422


def test_api_sampler_bank_empty_prompt():
    resp = client.post("/music-studio/sampler-bank", json={"prompt": ""})
    assert resp.status_code == 422


def test_api_sampler_bank_sample_structure():
    resp = client.post("/music-studio/sampler-bank", json={"prompt": "lo-fi chill"})
    assert resp.status_code == 200
    s = resp.json()["samples"][0]
    assert "name" in s
    assert "type" in s
    assert "pitch" in s
    assert "velocity" in s
    assert "duration_ms" in s


# ---------------------------------------------------------------------------
# /music-studio/keyboard-config API tests
# ---------------------------------------------------------------------------

def test_api_keyboard_config_valid():
    resp = client.post("/music-studio/keyboard-config", json={
        "scale": "major",
        "root_note": "C",
        "octave_range": 2,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "config_id" in data
    assert data["scale"] == "major"
    assert data["root_note"] == "C"
    assert "key_bindings" in data


def test_api_keyboard_config_all_scales():
    for scale in ("major", "minor", "pentatonic", "blues", "chromatic", "dorian", "mixolydian"):
        resp = client.post("/music-studio/keyboard-config", json={"scale": scale})
        assert resp.status_code == 200


def test_api_keyboard_config_invalid_scale():
    resp = client.post("/music-studio/keyboard-config", json={"scale": "wholetone"})
    assert resp.status_code == 422


def test_api_keyboard_config_octave_range():
    resp = client.post("/music-studio/keyboard-config", json={"scale": "major", "octave_range": 4})
    assert resp.status_code == 200
    assert resp.json()["octave_range"] == 4


# ---------------------------------------------------------------------------
# /video-studio/apply-effect API tests
# ---------------------------------------------------------------------------

def test_api_apply_effect_valid():
    resp = client.post("/video-studio/apply-effect", json={
        "scene_id": "scene-001",
        "effect_name": "color-grade",
        "parameters": {"contrast": 1.2},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["effect_name"] == "color-grade"
    assert data["scene_id"] == "scene-001"
    assert "effect_id" in data
    assert "preview_url" in data


def test_api_apply_effect_all_effects():
    effects = ["color-grade", "slow-motion", "blur", "vignette", "zoom", "glitch", "film-grain", "neon-glow"]
    for e in effects:
        resp = client.post("/video-studio/apply-effect", json={"scene_id": "s1", "effect_name": e})
        assert resp.status_code == 200


def test_api_apply_effect_invalid_effect():
    resp = client.post("/video-studio/apply-effect", json={
        "scene_id": "s1",
        "effect_name": "teleport",
    })
    assert resp.status_code == 422


def test_api_apply_effect_empty_scene_id():
    resp = client.post("/video-studio/apply-effect", json={
        "scene_id": "",
        "effect_name": "blur",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /video-studio/ai-tool API tests
# ---------------------------------------------------------------------------

def test_api_video_ai_tool_valid():
    resp = client.post("/video-studio/ai-tool", json={
        "tool_name": "background-remove",
        "input": "footage_clip_001.mp4",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_name"] == "background-remove"
    assert "tool_id" in data
    assert "confidence" in data
    assert "processing_time_ms" in data


def test_api_video_ai_tool_all_tools():
    tools = ["background-remove", "upscale", "stabilize", "denoise", "auto-edit", "scene-detect", "object-track"]
    for t in tools:
        resp = client.post("/video-studio/ai-tool", json={"tool_name": t, "input": "video.mp4"})
        assert resp.status_code == 200


def test_api_video_ai_tool_invalid_tool():
    resp = client.post("/video-studio/ai-tool", json={"tool_name": "magic-wand", "input": "file.mp4"})
    assert resp.status_code == 422


def test_api_video_ai_tool_empty_input():
    resp = client.post("/video-studio/ai-tool", json={"tool_name": "upscale", "input": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /text-studio/analyze-document API tests
# ---------------------------------------------------------------------------

def test_api_analyze_document_valid():
    resp = client.post("/text-studio/analyze-document", json={
        "content": "Hello world. This is a test document.\n\nSecond paragraph here.",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "analysis_id" in data
    assert data["word_count"] > 0
    assert "sentiment" in data
    assert "key_themes" in data
    assert "language_stats" in data


def test_api_analyze_document_word_count():
    resp = client.post("/text-studio/analyze-document", json={"content": "one two three four five"})
    assert resp.status_code == 200
    assert resp.json()["word_count"] == 5


def test_api_analyze_document_empty_content():
    resp = client.post("/text-studio/analyze-document", json={"content": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /text-studio/generate-outline API tests
# ---------------------------------------------------------------------------

def test_api_generate_outline_valid():
    resp = client.post("/text-studio/generate-outline", json={
        "topic": "The future of AI music",
        "outline_type": "article",
        "sections_count": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "outline_id" in data
    assert len(data["sections"]) == 5
    assert "suggested_hooks" in data
    assert data["estimated_word_count"] > 0


def test_api_generate_outline_all_types():
    for otype in ("article", "essay", "story", "script", "report", "blog"):
        resp = client.post("/text-studio/generate-outline", json={"topic": "test", "outline_type": otype})
        assert resp.status_code == 200


def test_api_generate_outline_invalid_type():
    resp = client.post("/text-studio/generate-outline", json={"topic": "test", "outline_type": "tweet"})
    assert resp.status_code == 422


def test_api_generate_outline_empty_topic():
    resp = client.post("/text-studio/generate-outline", json={"topic": ""})
    assert resp.status_code == 422


def test_api_generate_outline_section_count():
    resp = client.post("/text-studio/generate-outline", json={"topic": "Science", "sections_count": 3})
    assert resp.status_code == 200
    assert len(resp.json()["sections"]) == 3


# ---------------------------------------------------------------------------
# /visual-studio/generate-3d-scene API tests
# ---------------------------------------------------------------------------

def test_api_generate_3d_scene_valid():
    resp = client.post("/visual-studio/generate-3d-scene", json={
        "prompt": "futuristic city at night",
        "style": "sci-fi",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "scene_id" in data
    assert data["prompt"] == "futuristic city at night"
    assert "objects" in data
    assert "lighting" in data
    assert "camera" in data
    assert "render_settings" in data


def test_api_generate_3d_scene_all_styles():
    for style in ("realistic", "cartoon", "abstract", "sci-fi", "fantasy", "minimalist"):
        resp = client.post("/visual-studio/generate-3d-scene", json={"prompt": "landscape", "style": style})
        assert resp.status_code == 200


def test_api_generate_3d_scene_invalid_style():
    resp = client.post("/visual-studio/generate-3d-scene", json={"prompt": "scene", "style": "voxel"})
    assert resp.status_code == 422


def test_api_generate_3d_scene_empty_prompt():
    resp = client.post("/visual-studio/generate-3d-scene", json={"prompt": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /visual-studio/ai-photo-edit API tests
# ---------------------------------------------------------------------------

def test_api_ai_photo_edit_valid():
    resp = client.post("/visual-studio/ai-photo-edit", json={
        "image_description": "sunset on a beach with warm tones",
        "edits": ["brighten", "saturation-boost"],
        "style": "vibrant",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "edit_id" in data
    assert data["export_ready"] is True
    assert "enhancement_score" in data
    assert "style_match" in data


def test_api_ai_photo_edit_default_edits():
    resp = client.post("/visual-studio/ai-photo-edit", json={
        "image_description": "portrait in studio",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "auto-enhance" in data["edits_applied"]


def test_api_ai_photo_edit_empty_description():
    resp = client.post("/visual-studio/ai-photo-edit", json={"image_description": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /animation/export-mp4 API tests
# ---------------------------------------------------------------------------

def test_api_export_mp4_valid():
    resp = client.post("/animation/export-mp4", json={
        "animation_id": "anim-001",
        "fps": 30,
        "resolution": "1080p",
        "quality": "high",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "mp4"
    assert data["fps"] == 30
    assert data["resolution"] == "1080p"
    assert data["status"] == "completed"
    assert "export_id" in data
    assert "file_size_kb" in data
    assert data["codec"] == "h264"


def test_api_export_mp4_all_resolutions():
    for res in ("720p", "1080p", "2k", "4k"):
        resp = client.post("/animation/export-mp4", json={"animation_id": "a1", "resolution": res})
        assert resp.status_code == 200


def test_api_export_mp4_all_qualities():
    for quality in ("draft", "standard", "high", "ultra"):
        resp = client.post("/animation/export-mp4", json={"animation_id": "a1", "quality": quality})
        assert resp.status_code == 200


def test_api_export_mp4_invalid_resolution():
    resp = client.post("/animation/export-mp4", json={
        "animation_id": "a1",
        "resolution": "8k",
    })
    assert resp.status_code == 422


def test_api_export_mp4_invalid_quality():
    resp = client.post("/animation/export-mp4", json={
        "animation_id": "a1",
        "quality": "supreme",
    })
    assert resp.status_code == 422


def test_api_export_mp4_empty_animation_id():
    resp = client.post("/animation/export-mp4", json={"animation_id": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Additional unit tests – connect_oauth_platform
# ---------------------------------------------------------------------------

def test_connect_oauth_auth_url_contains_state():
    r = connect_oauth_platform("tiktok", "creator1", "video:read")
    assert r["state_token"] in r["auth_url"]


def test_connect_oauth_whitespace_trimmed():
    r = connect_oauth_platform("spotify", "  user1  ", "  read  ")
    assert r["user_id"] == "user1"
    assert r["scope"] == "read"


def test_connect_oauth_bandcamp_valid():
    r = connect_oauth_platform("bandcamp", "artist99", "album:write")
    assert r["platform"] == "bandcamp"


def test_connect_oauth_distrokid_valid():
    r = connect_oauth_platform("distrokid", "label42", "distribute")
    assert r["platform"] == "distrokid"


def test_connect_oauth_soundcloud_valid():
    r = connect_oauth_platform("soundcloud", "dj99", "stream:read")
    assert r["platform"] == "soundcloud"


# ---------------------------------------------------------------------------
# Additional unit tests – distribute_release
# ---------------------------------------------------------------------------

def test_distribute_release_whitespace_title_rejected():
    with pytest.raises(ValueError, match="title"):
        distribute_release("   ", "Artist", ["spotify"], "2025-01-01", {})


def test_distribute_release_whitespace_artist_rejected():
    with pytest.raises(ValueError, match="artist"):
        distribute_release("Title", "   ", ["spotify"], "2025-01-01", {})


def test_distribute_release_none_metadata_becomes_empty():
    r = distribute_release("Track", "Artist", ["spotify"], "2025-01-01", None)
    assert r["metadata"] == {}


def test_distribute_release_release_date_preserved():
    r = distribute_release("Song", "Band", ["spotify"], "2025-12-25", {})
    assert r["release_date"] == "2025-12-25"


def test_distribute_release_id_is_hex_string():
    r = distribute_release("Track", "Artist", ["spotify"], "2025-01-01", {})
    assert all(c in "0123456789abcdef" for c in r["release_id"])


# ---------------------------------------------------------------------------
# Additional unit tests – generate_epk
# ---------------------------------------------------------------------------

def test_generate_epk_download_url_format():
    r = generate_epk("Band", "Bio here.", ["rock"], "a@b.com")
    assert r["download_url"].startswith("https://kalaos.io/epk/")
    assert r["download_url"].endswith("/download")


def test_generate_epk_whitespace_artist_rejected():
    with pytest.raises(ValueError, match="artist_name"):
        generate_epk("   ", "Bio", ["pop"], "a@b.com")


def test_generate_epk_whitespace_bio_rejected():
    with pytest.raises(ValueError, match="bio"):
        generate_epk("Artist", "   ", ["pop"], "a@b.com")


def test_generate_epk_whitespace_email_rejected():
    with pytest.raises(ValueError, match="contact_email"):
        generate_epk("Artist", "Bio text", ["pop"], "   ")


def test_generate_epk_six_sections():
    r = generate_epk("X", "Bio.", [], "x@x.com")
    assert len(r["sections"]) == 6


def test_generate_epk_genres_list():
    genres = ["jazz", "blues", "soul"]
    r = generate_epk("Artist", "Bio.", genres, "a@b.com")
    assert r["genres"] == genres


# ---------------------------------------------------------------------------
# Additional unit tests – get_platform_analytics
# ---------------------------------------------------------------------------

def test_get_platform_analytics_metrics_positive():
    r = get_platform_analytics("spotify", "user1", "7d")
    for key in ("streams", "followers", "saves", "playlist_adds"):
        assert r["metrics"][key] > 0


def test_get_platform_analytics_engagement_rate_range():
    r = get_platform_analytics("youtube", "user2", "1y")
    assert 0 < r["metrics"]["engagement_rate"] < 15


def test_get_platform_analytics_top_content_ranked():
    r = get_platform_analytics("tiktok", "user3", "30d")
    ranks = [item["rank"] for item in r["top_content"]]
    assert ranks == [1, 2, 3]


def test_get_platform_analytics_whitespace_user_id_rejected():
    with pytest.raises(ValueError, match="user_id"):
        get_platform_analytics("spotify", "  ", "30d")


def test_get_platform_analytics_instagram_valid():
    r = get_platform_analytics("instagram", "influencer1", "90d")
    assert r["platform"] == "instagram"


# ---------------------------------------------------------------------------
# Additional unit tests – sync_catalog
# ---------------------------------------------------------------------------

def test_sync_catalog_tracks_synced_positive():
    r = sync_catalog("user1", "spotify", ["youtube"])
    assert r["tracks_synced"] > 0


def test_sync_catalog_sync_id_is_hex():
    r = sync_catalog("user1", "spotify", [])
    assert all(c in "0123456789abcdef" for c in r["sync_id"])


def test_sync_catalog_whitespace_user_id_rejected():
    with pytest.raises(ValueError, match="user_id"):
        sync_catalog("   ", "spotify", [])


def test_sync_catalog_whitespace_source_rejected():
    with pytest.raises(ValueError, match="source_platform"):
        sync_catalog("user1", "   ", [])


def test_sync_catalog_multiple_targets():
    targets = ["youtube", "tiktok", "bandcamp"]
    r = sync_catalog("user1", "spotify", targets)
    assert r["target_platforms"] == targets


# ---------------------------------------------------------------------------
# Additional unit tests – create_smart_link
# ---------------------------------------------------------------------------

def test_create_smart_link_smart_url_contains_link_id():
    r = create_smart_link("Track", "Artist", {"spotify": "url"})
    assert r["link_id"] in r["smart_url"]


def test_create_smart_link_whitespace_title_rejected():
    with pytest.raises(ValueError, match="title"):
        create_smart_link("   ", "Artist", {"spotify": "url"})


def test_create_smart_link_whitespace_artist_rejected():
    with pytest.raises(ValueError, match="artist"):
        create_smart_link("Title", "   ", {"spotify": "url"})


def test_create_smart_link_multiple_platforms():
    urls = {"spotify": "sp_url", "youtube": "yt_url", "tiktok": "tt_url"}
    r = create_smart_link("Song", "Band", urls)
    assert len(r["platforms"]) == 3


def test_create_smart_link_tracking_always_enabled():
    r = create_smart_link("Track", "Artist", {"spotify": "url"})
    assert r["tracking_enabled"] is True


# ---------------------------------------------------------------------------
# Additional unit tests – schedule_release
# ---------------------------------------------------------------------------

def test_schedule_release_whitespace_title_rejected():
    with pytest.raises(ValueError, match="title"):
        schedule_release("   ", "Artist", "2026-01-01", ["spotify"])


def test_schedule_release_whitespace_artist_rejected():
    with pytest.raises(ValueError, match="artist"):
        schedule_release("Title", "   ", "2026-01-01", ["spotify"])


def test_schedule_release_no_presave_default():
    r = schedule_release("Track", "Artist", "2026-06-01", ["spotify"])
    assert r["pre_save_enabled"] is False


def test_schedule_release_schedule_id_hex():
    r = schedule_release("Track", "Artist", "2026-01-01", ["spotify"])
    assert all(c in "0123456789abcdef" for c in r["schedule_id"])


def test_schedule_release_multiple_platforms():
    platforms = ["spotify", "youtube", "tiktok", "bandcamp"]
    r = schedule_release("Album", "Band", "2026-06-01", platforms)
    assert r["platforms"] == platforms


# ---------------------------------------------------------------------------
# Additional unit tests – get_royalty_report
# ---------------------------------------------------------------------------

def test_get_royalty_report_whitespace_user_id_rejected():
    with pytest.raises(ValueError, match="user_id"):
        get_royalty_report("   ", "2024-Q1")


def test_get_royalty_report_whitespace_period_rejected():
    with pytest.raises(ValueError, match="period"):
        get_royalty_report("user1", "   ")


def test_get_royalty_report_earnings_positive():
    r = get_royalty_report("user1", "2024-Q1", ["spotify"])
    assert r["total_earnings"] > 0


def test_get_royalty_report_payment_status_valid():
    r = get_royalty_report("user1", "2024-Q1", ["spotify"])
    assert r["payment_status"] in ("pending", "processing", "paid")


def test_get_royalty_report_report_id_hex():
    r = get_royalty_report("user1", "2024-Q1", ["spotify"])
    assert all(c in "0123456789abcdef" for c in r["report_id"])


# ---------------------------------------------------------------------------
# Additional API tests – platform connect
# ---------------------------------------------------------------------------

def test_api_oauth_all_platforms_via_api():
    for platform in ("spotify", "youtube", "soundcloud", "instagram", "tiktok", "twitter", "bandcamp", "distrokid"):
        resp = client.post("/platform-connect/oauth", json={
            "platform": platform, "user_id": "u1", "scope": "read"
        })
        assert resp.status_code == 200


def test_api_distribute_estimated_date_returned():
    resp = client.post("/platform-connect/distribute", json={
        "title": "Track", "artist": "Band",
        "platforms": ["spotify"], "release_date": "2025-09-01",
    })
    assert resp.status_code == 200
    assert "estimated_live_date" in resp.json()


def test_api_epk_sections_count():
    resp = client.post("/platform-connect/epk", json={
        "artist_name": "X", "bio": "Bio text here.", "genres": [],
        "contact_email": "x@x.com",
    })
    assert resp.status_code == 200
    assert len(resp.json()["sections"]) == 6


def test_api_analytics_metrics_keys():
    resp = client.post("/platform-connect/analytics", json={
        "platform": "spotify", "user_id": "u1", "time_range": "7d",
    })
    assert resp.status_code == 200
    m = resp.json()["metrics"]
    assert all(k in m for k in ("streams", "followers", "engagement_rate", "saves", "playlist_adds"))


def test_api_sync_catalog_in_progress_status():
    resp = client.post("/platform-connect/sync-catalog", json={
        "user_id": "u1", "source_platform": "spotify",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_api_smart_link_smart_url_format():
    resp = client.post("/platform-connect/smart-link", json={
        "title": "T", "artist": "A", "platforms_urls": {"spotify": "sp://1"},
    })
    assert resp.status_code == 200
    assert "kalaos.io/link/" in resp.json()["smart_url"]


def test_api_schedule_release_countdown_field():
    resp = client.post("/platform-connect/schedule-release", json={
        "title": "T", "artist": "A", "release_date": "2030-01-01", "platforms": ["spotify"],
    })
    assert resp.status_code == 200
    assert "countdown_days" in resp.json()


def test_api_royalty_report_breakdown_is_list():
    resp = client.post("/platform-connect/royalty-report", json={
        "user_id": "u1", "period": "2024-Q1",
    })
    assert resp.status_code == 200
    assert isinstance(resp.json()["breakdown"], list)


# ---------------------------------------------------------------------------
# Additional API tests – studio endpoints
# ---------------------------------------------------------------------------

def test_api_sampler_bank_bpm_range():
    resp = client.post("/music-studio/sampler-bank", json={"prompt": "jazz vibes", "kit_style": "jazz"})
    assert resp.status_code == 200
    bpm = resp.json()["bpm"]
    assert 80 <= bpm < 160


def test_api_sampler_bank_sample_velocity_range():
    resp = client.post("/music-studio/sampler-bank", json={"prompt": "test"})
    assert resp.status_code == 200
    for s in resp.json()["samples"]:
        assert 64 <= s["velocity"] <= 127


def test_api_keyboard_config_key_bindings_present():
    resp = client.post("/music-studio/keyboard-config", json={"scale": "pentatonic", "root_note": "A"})
    assert resp.status_code == 200
    assert len(resp.json()["key_bindings"]) == 5


def test_api_keyboard_config_blues_key_count():
    resp = client.post("/music-studio/keyboard-config", json={"scale": "blues"})
    assert resp.status_code == 200
    assert len(resp.json()["key_bindings"]) == 6


def test_api_apply_effect_parameters_preserved():
    params = {"intensity": 0.7, "blur_radius": 5}
    resp = client.post("/video-studio/apply-effect", json={
        "scene_id": "s1", "effect_name": "blur", "parameters": params
    })
    assert resp.status_code == 200
    assert resp.json()["parameters"]["intensity"] == 0.7


def test_api_video_ai_tool_confidence_range():
    resp = client.post("/video-studio/ai-tool", json={"tool_name": "upscale", "input": "video.mp4"})
    assert resp.status_code == 200
    confidence = resp.json()["confidence"]
    assert 0.75 <= confidence <= 1.0


def test_api_analyze_document_readability_range():
    resp = client.post("/text-studio/analyze-document", json={"content": "This is a simple sentence."})
    assert resp.status_code == 200
    score = resp.json()["readability_score"]
    assert 40 <= score <= 100


def test_api_analyze_document_language_stats_keys():
    resp = client.post("/text-studio/analyze-document", json={"content": "Hello world test."})
    assert resp.status_code == 200
    stats = resp.json()["language_stats"]
    assert all(k in stats for k in ("avg_word_length", "avg_sentence_length", "unique_words"))


def test_api_generate_outline_hooks_count():
    resp = client.post("/text-studio/generate-outline", json={"topic": "AI music creation"})
    assert resp.status_code == 200
    assert len(resp.json()["suggested_hooks"]) == 3


def test_api_generate_outline_invalid_sections_count():
    resp = client.post("/text-studio/generate-outline", json={"topic": "test", "sections_count": 0})
    assert resp.status_code == 422


def test_api_generate_3d_scene_objects_count():
    resp = client.post("/visual-studio/generate-3d-scene", json={"prompt": "forest", "style": "fantasy"})
    assert resp.status_code == 200
    assert len(resp.json()["objects"]) == 3


def test_api_generate_3d_scene_render_settings():
    resp = client.post("/visual-studio/generate-3d-scene", json={"prompt": "space station"})
    assert resp.status_code == 200
    rs = resp.json()["render_settings"]
    assert "samples" in rs
    assert "resolution" in rs
    assert "engine" in rs


def test_api_ai_photo_edit_enhancement_score_range():
    resp = client.post("/visual-studio/ai-photo-edit", json={
        "image_description": "mountain landscape at dawn"
    })
    assert resp.status_code == 200
    score = resp.json()["enhancement_score"]
    assert 0.6 <= score <= 1.0


def test_api_export_mp4_duration_positive():
    resp = client.post("/animation/export-mp4", json={"animation_id": "a1"})
    assert resp.status_code == 200
    assert resp.json()["duration_seconds"] > 0


def test_api_export_mp4_file_size_positive():
    resp = client.post("/animation/export-mp4", json={
        "animation_id": "a1", "resolution": "4k", "quality": "ultra"
    })
    assert resp.status_code == 200
    assert resp.json()["file_size_kb"] > 0


def test_api_export_mp4_invalid_fps_zero():
    resp = client.post("/animation/export-mp4", json={"animation_id": "a1", "fps": 0})
    assert resp.status_code == 422


def test_api_export_mp4_invalid_fps_too_high():
    resp = client.post("/animation/export-mp4", json={"animation_id": "a1", "fps": 200})
    assert resp.status_code == 422


def test_api_export_mp4_codec_is_h264():
    resp = client.post("/animation/export-mp4", json={"animation_id": "test-anim"})
    assert resp.status_code == 200
    assert resp.json()["codec"] == "h264"


# ---------------------------------------------------------------------------
# Additional comprehensive tests
# ---------------------------------------------------------------------------

def test_connect_oauth_instagram_valid():
    r = connect_oauth_platform("instagram", "influencer42", "media:read")
    assert r["platform"] == "instagram"
    assert r["status"] == "pending_authorization"


def test_connect_oauth_twitter_valid():
    r = connect_oauth_platform("twitter", "tweeter1", "tweets:read")
    assert r["platform"] == "twitter"


def test_connect_oauth_auth_url_contains_platform():
    r = connect_oauth_platform("spotify", "user1", "read")
    assert "spotify" in r["auth_url"]


def test_distribute_release_id_consistent():
    r1 = distribute_release("Song", "Artist", ["spotify"], "2025-01-01", {})
    r2 = distribute_release("Song", "Artist", ["spotify"], "2025-01-01", {})
    assert r1["release_id"] == r2["release_id"]


def test_generate_epk_id_consistent():
    r1 = generate_epk("Band", "Bio.", [], "a@b.com")
    r2 = generate_epk("Band", "Bio.", [], "a@b.com")
    assert r1["epk_id"] == r2["epk_id"]


def test_sync_catalog_id_consistent():
    r1 = sync_catalog("user1", "spotify", [])
    r2 = sync_catalog("user1", "spotify", [])
    assert r1["sync_id"] == r2["sync_id"]


def test_create_smart_link_id_consistent():
    r1 = create_smart_link("Track", "Band", {"sp": "url"})
    r2 = create_smart_link("Track", "Band", {"sp": "url"})
    assert r1["link_id"] == r2["link_id"]


def test_schedule_release_id_consistent():
    r1 = schedule_release("T", "A", "2026-01-01", ["spotify"])
    r2 = schedule_release("T", "A", "2026-01-01", ["spotify"])
    assert r1["schedule_id"] == r2["schedule_id"]


def test_royalty_report_id_consistent():
    r1 = get_royalty_report("u1", "2024-Q1", ["spotify"])
    r2 = get_royalty_report("u1", "2024-Q1", ["spotify"])
    assert r1["report_id"] == r2["report_id"]


def test_api_distribute_empty_artist():
    resp = client.post("/platform-connect/distribute", json={
        "title": "Song", "artist": "", "platforms": ["spotify"], "release_date": "2025-01-01",
    })
    assert resp.status_code == 422


def test_api_epk_empty_artist_name():
    resp = client.post("/platform-connect/epk", json={
        "artist_name": "", "bio": "Bio.", "genres": [], "contact_email": "a@b.com",
    })
    assert resp.status_code == 422


def test_api_epk_empty_contact_email():
    resp = client.post("/platform-connect/epk", json={
        "artist_name": "Band", "bio": "Bio.", "genres": [], "contact_email": "",
    })
    assert resp.status_code == 422


def test_api_analytics_empty_user_id():
    resp = client.post("/platform-connect/analytics", json={
        "platform": "spotify", "user_id": "", "time_range": "30d",
    })
    assert resp.status_code == 422


def test_api_sync_catalog_empty_source():
    resp = client.post("/platform-connect/sync-catalog", json={
        "user_id": "u1", "source_platform": "",
    })
    assert resp.status_code == 422


def test_api_smart_link_empty_title():
    resp = client.post("/platform-connect/smart-link", json={
        "title": "", "artist": "A", "platforms_urls": {"sp": "url"},
    })
    assert resp.status_code == 422


def test_api_smart_link_empty_artist():
    resp = client.post("/platform-connect/smart-link", json={
        "title": "T", "artist": "", "platforms_urls": {"sp": "url"},
    })
    assert resp.status_code == 422


def test_api_schedule_release_empty_title():
    resp = client.post("/platform-connect/schedule-release", json={
        "title": "", "artist": "A", "release_date": "2026-01-01", "platforms": ["sp"],
    })
    assert resp.status_code == 422


def test_api_schedule_release_empty_artist():
    resp = client.post("/platform-connect/schedule-release", json={
        "title": "T", "artist": "", "release_date": "2026-01-01", "platforms": ["sp"],
    })
    assert resp.status_code == 422


def test_api_royalty_report_period_preserved():
    resp = client.post("/platform-connect/royalty-report", json={
        "user_id": "u1", "period": "2024-Q3",
    })
    assert resp.status_code == 200
    assert resp.json()["period"] == "2024-Q3"


def test_api_sampler_bank_hip_hop_kit():
    resp = client.post("/music-studio/sampler-bank", json={
        "prompt": "boom bap", "kit_style": "hip-hop",
    })
    assert resp.status_code == 200
    assert "hip-hop" in resp.json()["kit_name"].lower()


def test_api_sampler_bank_orchestral_kit():
    resp = client.post("/music-studio/sampler-bank", json={
        "prompt": "symphony", "kit_style": "orchestral",
    })
    assert resp.status_code == 200


def test_api_keyboard_config_chromatic_12_notes():
    resp = client.post("/music-studio/keyboard-config", json={"scale": "chromatic"})
    assert resp.status_code == 200
    assert len(resp.json()["key_bindings"]) == 12


def test_api_keyboard_config_dorian_scale():
    resp = client.post("/music-studio/keyboard-config", json={"scale": "dorian", "root_note": "D"})
    assert resp.status_code == 200
    assert resp.json()["scale"] == "dorian"


def test_api_keyboard_config_mixolydian_scale():
    resp = client.post("/music-studio/keyboard-config", json={"scale": "mixolydian"})
    assert resp.status_code == 200
    assert resp.json()["scale"] == "mixolydian"


def test_api_apply_effect_neon_glow():
    resp = client.post("/video-studio/apply-effect", json={
        "scene_id": "sc-42", "effect_name": "neon-glow",
    })
    assert resp.status_code == 200
    assert resp.json()["effect_name"] == "neon-glow"


def test_api_apply_effect_film_grain():
    resp = client.post("/video-studio/apply-effect", json={
        "scene_id": "sc-43", "effect_name": "film-grain",
    })
    assert resp.status_code == 200


def test_api_video_ai_tool_scene_detect():
    resp = client.post("/video-studio/ai-tool", json={
        "tool_name": "scene-detect", "input": "movie.mp4",
    })
    assert resp.status_code == 200
    assert "result" in resp.json()


def test_api_video_ai_tool_object_track():
    resp = client.post("/video-studio/ai-tool", json={
        "tool_name": "object-track", "input": "clip.mp4",
    })
    assert resp.status_code == 200


def test_api_analyze_document_sentiment_valid():
    resp = client.post("/text-studio/analyze-document", json={"content": "Great music makes the world better."})
    assert resp.status_code == 200
    assert resp.json()["sentiment"] in ("positive", "neutral", "negative", "mixed")


def test_api_analyze_document_key_themes_list():
    resp = client.post("/text-studio/analyze-document", json={"content": "Music is art."})
    assert resp.status_code == 200
    assert isinstance(resp.json()["key_themes"], list)


def test_api_generate_outline_story_type():
    resp = client.post("/text-studio/generate-outline", json={"topic": "The lone musician", "outline_type": "story"})
    assert resp.status_code == 200
    assert "story" in resp.json()["title"].lower()


def test_api_generate_outline_script_type():
    resp = client.post("/text-studio/generate-outline", json={"topic": "Music video", "outline_type": "script"})
    assert resp.status_code == 200


def test_api_generate_3d_scene_minimalist_style():
    resp = client.post("/visual-studio/generate-3d-scene", json={"prompt": "empty room", "style": "minimalist"})
    assert resp.status_code == 200
    assert resp.json()["environment"] == "minimalist"


def test_api_generate_3d_scene_cartoon_style():
    resp = client.post("/visual-studio/generate-3d-scene", json={"prompt": "cartoon world", "style": "cartoon"})
    assert resp.status_code == 200


def test_api_ai_photo_edit_custom_edits():
    resp = client.post("/visual-studio/ai-photo-edit", json={
        "image_description": "concert photo",
        "edits": ["crop", "sharpen", "exposure"],
    })
    assert resp.status_code == 200
    assert "crop" in resp.json()["edits_applied"]


def test_api_export_mp4_draft_quality():
    resp = client.post("/animation/export-mp4", json={
        "animation_id": "anim-test", "quality": "draft",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_api_export_mp4_720p_resolution():
    resp = client.post("/animation/export-mp4", json={
        "animation_id": "anim-test", "resolution": "720p",
    })
    assert resp.status_code == 200
    assert resp.json()["resolution"] == "720p"


def test_api_export_mp4_2k_resolution():
    resp = client.post("/animation/export-mp4", json={
        "animation_id": "anim-2k", "resolution": "2k",
    })
    assert resp.status_code == 200


def test_distribute_release_trimmed_inputs():
    r = distribute_release("  My Album  ", "  My Artist  ", ["spotify"], "2025-01-01", {})
    assert r["title"] == "My Album"
    assert r["artist"] == "My Artist"


def test_get_royalty_report_custom_platforms():
    platforms = ["spotify", "bandcamp"]
    r = get_royalty_report("user9", "2024-Q2", platforms)
    assert len(r["breakdown"]) == 2
    assert r["breakdown"][0]["platform"] in platforms


# ---------------------------------------------------------------------------
# Final unit tests to reach target count
# ---------------------------------------------------------------------------

def test_connect_oauth_youtube_valid():
    r = connect_oauth_platform("youtube", "creator100", "upload:write")
    assert r["platform"] == "youtube"
    assert "youtube" in r["auth_url"]


def test_distribute_release_status_submitted():
    r = distribute_release("Album", "Band", ["spotify", "bandcamp"], "2025-11-01", {})
    assert r["distribution_status"] == "submitted"


def test_generate_epk_sections_order():
    r = generate_epk("X", "Bio.", [], "x@x.com")
    assert r["sections"][0] == "Biography"
    assert r["sections"][-1] == "Rider"


def test_get_platform_analytics_growth_keys():
    r = get_platform_analytics("spotify", "u1", "1y")
    assert "followers_change" in r["growth"]
    assert "streams_change_pct" in r["growth"]


def test_sync_catalog_started_at_present():
    r = sync_catalog("user1", "bandcamp", ["distrokid"])
    assert "Z" in r["started_at"] or "+" in r["started_at"]


def test_create_smart_link_platforms_count():
    urls = {"sp": "u1", "yt": "u2", "sc": "u3", "tt": "u4"}
    r = create_smart_link("Big Release", "Superstar", urls)
    assert len(r["platforms"]) == 4


def test_schedule_release_status_scheduled():
    r = schedule_release("EP", "Solo Artist", "2026-03-01", ["spotify"])
    assert r["status"] == "scheduled"


def test_get_royalty_report_breakdown_earnings_positive():
    r = get_royalty_report("user5", "2024-Q4", ["spotify", "youtube", "tiktok"])
    for b in r["breakdown"]:
        assert b["earnings"] > 0


def test_connect_oauth_scope_preserved():
    scope = "user-read-private user-read-email playlist-read-collaborative"
    r = connect_oauth_platform("spotify", "user1", scope)
    assert r["scope"] == scope


def test_distribute_release_platforms_preserved():
    platforms = ["spotify", "youtube", "soundcloud", "tiktok"]
    r = distribute_release("Compilation", "Various", platforms, "2025-06-15", {})
    assert r["platforms"] == platforms


def test_generate_epk_created_at_present():
    r = generate_epk("Artist", "Bio text.", ["pop"], "e@mail.com")
    assert "created_at" in r
    assert len(r["created_at"]) > 10


def test_sync_catalog_user_id_preserved():
    r = sync_catalog("  alice123  ", "spotify", [])
    assert r["user_id"] == "alice123"


def test_schedule_release_pre_save_true():
    r = schedule_release("Collab", "Artists", "2026-12-01", ["spotify"], True)
    assert r["pre_save_enabled"] is True


def test_get_royalty_report_user_id_preserved():
    r = get_royalty_report("  artist99  ", "2024-Q1", ["spotify"])
    assert r["user_id"] == "artist99"


def test_get_royalty_report_period_trimmed():
    r = get_royalty_report("user1", "  2024-Q2  ", ["spotify"])
    assert r["period"] == "2024-Q2"


def test_connect_oauth_expires_in_600():
    for p in ("spotify", "youtube", "bandcamp"):
        r = connect_oauth_platform(p, "u1", "read")
        assert r["expires_in"] == 600


def test_distribute_release_multiple_calls_same_id():
    r1 = distribute_release("Fixed Title", "Fixed Artist", ["sp"], "2025-06-01", {})
    r2 = distribute_release("Fixed Title", "Fixed Artist", ["sp"], "2025-06-01", {})
    assert r1["release_id"] == r2["release_id"]


def test_generate_epk_no_media_links_default():
    r = generate_epk("Band", "Bio.", ["rock"], "b@b.com", None)
    assert r["media_links"] == []


def test_sync_catalog_status_in_progress():
    r = sync_catalog("user9", "distrokid", ["spotify", "youtube"])
    assert r["status"] == "in_progress"
    assert len(r["target_platforms"]) == 2


def test_get_platform_analytics_consistent():
    r1 = get_platform_analytics("spotify", "u1", "30d")
    r2 = get_platform_analytics("spotify", "u1", "30d")
    assert r1["metrics"]["streams"] == r2["metrics"]["streams"]



# ---------------------------------------------------------------------------
# Additional tests from origin/main (refactored platform-connect API)
# ---------------------------------------------------------------------------


def test_get_oauth_url_spotify():
    result = get_oauth_url("spotify", "user123")
    assert result["platform"] == "spotify"
    assert "spotify" in result["oauth_url"]
    assert result["client_id"] == "kalaos_spotify_client_id"
    assert "state" in result
    assert "scope" in result

def test_get_oauth_url_all_platforms():
    for platform in _VALID_PLATFORMS:
        result = get_oauth_url(platform, "user_abc")
        assert result["platform"] == platform
        assert result["oauth_url"].startswith("https://")
        assert "client_id" in result
        assert "scope" in result
        assert "state" in result

def test_get_oauth_url_state_contains_user_id():
    result = get_oauth_url("youtube", "user999")
    assert "user999" in result["state"]

def test_get_oauth_url_state_unique():
    r1 = get_oauth_url("spotify", "userX")
    r2 = get_oauth_url("spotify", "userX")
    assert r1["state"] != r2["state"]

def test_get_oauth_url_invalid_platform():
    with pytest.raises(ValueError, match="platform"):
        get_oauth_url("myspace", "user123")

def test_get_oauth_url_unknown_platform_raises():
    with pytest.raises(ValueError):
        get_oauth_url("nonexistent_platform", "uid")


# ---------------------------------------------------------------------------
# connect_platform – unit tests
# ---------------------------------------------------------------------------

def test_connect_platform_basic():
    result = connect_platform("spotify", "user123", "auth_code_abc")
    assert result["platform"] == "spotify"
    assert result["user_id"] == "user123"
    assert result["connected"] is True
    assert "username" in result
    assert "followers" in result
    assert "connected_at" in result

def test_connect_platform_username_format():
    result = connect_platform("tiktok", "abcdef1234", "code")
    assert result["username"] == "tiktok_user_abcdef"

def test_connect_platform_short_user_id():
    result = connect_platform("instagram", "abc", "code")
    assert "username" in result
    assert result["connected"] is True

def test_connect_platform_followers_range():
    result = connect_platform("youtube", "user1", "code")
    assert 1 <= result["followers"] <= 100000

def test_connect_platform_invalid_platform():
    with pytest.raises(ValueError, match="platform"):
        connect_platform("myspace", "user1", "code")

def test_connect_platform_empty_auth_code():
    with pytest.raises(ValueError, match="auth_code"):
        connect_platform("spotify", "user1", "")

def test_connect_platform_whitespace_auth_code():
    with pytest.raises(ValueError, match="auth_code"):
        connect_platform("spotify", "user1", "   ")


# ---------------------------------------------------------------------------
# disconnect_platform – unit tests
# ---------------------------------------------------------------------------

def test_disconnect_platform_basic():
    result = disconnect_platform("spotify", "user123")
    assert result["platform"] == "spotify"
    assert result["user_id"] == "user123"
    assert result["connected"] is False
    assert "disconnected_at" in result

def test_disconnect_platform_invalid_platform():
    with pytest.raises(ValueError, match="platform"):
        disconnect_platform("napster", "user1")

def test_disconnect_platform_all_platforms():
    for platform in _VALID_PLATFORMS:
        result = disconnect_platform(platform, "u1")
        assert result["connected"] is False


# ---------------------------------------------------------------------------
# get_connected_platforms – unit tests
# ---------------------------------------------------------------------------

def test_get_connected_platforms_structure():
    result = get_connected_platforms("user42")
    assert result["user_id"] == "user42"
    assert "platforms" in result
    assert isinstance(result["platforms"], list)
    assert len(result["platforms"]) == 5

def test_get_connected_platforms_defaults_to_not_connected():
    result = get_connected_platforms("user42")
    for p in result["platforms"]:
        assert p["connected"] is False

def test_get_connected_platforms_fields():
    result = get_connected_platforms("userX")
    for p in result["platforms"]:
        assert "platform" in p
        assert "connected" in p
        assert "username" in p
        assert "followers" in p

def test_get_connected_platforms_includes_demo_platforms():
    result = get_connected_platforms("demo_user")
    platform_names = {p["platform"] for p in result["platforms"]}
    assert "spotify" in platform_names
    assert "youtube" in platform_names


# ---------------------------------------------------------------------------
# distribute_to_platforms – unit tests
# ---------------------------------------------------------------------------

def test_distribute_to_platforms_basic():
    content = {"title": "My Track", "type": "audio", "description": "A great track"}
    result = distribute_to_platforms("user1", ["spotify", "tiktok"], content)
    assert result["user_id"] == "user1"
    assert result["total"] == 2
    assert result["queued"] == 2
    assert len(result["distributed_to"]) == 2

def test_distribute_to_platforms_track_url_format():
    content = {"title": "AwesomeSong", "type": "audio"}
    result = distribute_to_platforms("u1", ["spotify"], content)
    track_url = result["distributed_to"][0]["track_url"]
    assert "spotify" in track_url
    assert "u1" in track_url
    assert "AwesomeSong" in track_url

def test_distribute_to_platforms_status_queued():
    content = {"title": "Track", "type": "audio"}
    result = distribute_to_platforms("u1", ["youtube", "soundcloud"], content)
    for item in result["distributed_to"]:
        assert item["status"] == "queued"

def test_distribute_to_platforms_empty_platforms():
    with pytest.raises(ValueError, match="platforms"):
        distribute_to_platforms("u1", [], {"title": "Track", "type": "audio"})


# ---------------------------------------------------------------------------
# get_analytics_summary – unit tests
# ---------------------------------------------------------------------------

def test_get_analytics_summary_all():
    result = get_analytics_summary("user1")
    assert result["user_id"] == "user1"
    assert result["platform"] == "all"
    assert "total_plays" in result
    assert "total_followers" in result
    assert "total_revenue_usd" in result
    assert "growth_pct" in result
    assert "top_content" in result

def test_get_analytics_summary_specific_platform():
    result = get_analytics_summary("user1", "spotify")
    assert result["platform"] == "spotify"

def test_get_analytics_summary_top_content():
    result = get_analytics_summary("user1")
    assert len(result["top_content"]) == 2
    for item in result["top_content"]:
        assert "title" in item
        assert "plays" in item

def test_get_analytics_summary_ranges():
    result = get_analytics_summary("user1")
    assert 100 <= result["total_plays"] <= 1_000_000
    assert 100 <= result["total_followers"] <= 50_000
    assert 10 <= result["total_revenue_usd"] <= 5000
    assert -20 <= result["growth_pct"] <= 50


# ---------------------------------------------------------------------------
# generate_epk – unit tests
# ---------------------------------------------------------------------------

def test_generate_epk_basic():
    result = generate_epk("u1", "DJ Kala", "Electronic", "An artist from London.")
    assert result["user_id"] == "u1"
    assert result["artist_name"] == "DJ Kala"
    assert result["genre"] == "Electronic"
    assert result["status"] == "generated"
    assert "epk_url" in result
    assert "generated_at" in result

def test_generate_epk_url_contains_user_id():
    result = generate_epk("uid999", "Artist", "Pop", "My bio here.")
    assert "uid999" in result["epk_url"]

def test_generate_epk_sections():
    result = generate_epk("u1", "A", "Pop", "Bio text.")
    assert "sections" in result
    assert "biography" in result["sections"]
    assert "discography" in result["sections"]

def test_generate_epk_word_count():
    result = generate_epk("u1", "Artist", "Rock", "One two three four five")
    assert result["word_count"] == 5

def test_generate_epk_empty_genre():
    with pytest.raises(ValueError, match="genre"):
        generate_epk("u1", "Artist", "", "Some bio")

def test_get_optimal_release_time_pop():
    result = get_optimal_release_time("pop")
    assert result["genre"] == "pop"
    assert result["optimal_day"] in ["Friday", "Thursday", "Wednesday"]
    assert result["optimal_time_utc"] == "14:00"
    assert "reasoning" in result
    assert result["predicted_reach_multiplier"] > 1.0

def test_get_optimal_release_time_known_genres():
    for genre in ("hip-hop", "electronic", "jazz", "classical", "r&b"):
        result = get_optimal_release_time(genre)
        assert "optimal_day" in result

def test_get_optimal_release_time_target_region():
    result = get_optimal_release_time("pop", "europe")
    assert result["target_region"] == "europe"

def test_get_optimal_release_time_default_region():
    result = get_optimal_release_time("rock")
    assert result["target_region"] == "global"

def test_get_optimal_release_time_all_known_genres():
    from kalacore.kalaplatformconnect import _GENRE_RELEASE_INFO
    for genre in _GENRE_RELEASE_INFO:
        result = get_optimal_release_time(genre)
        assert result["optimal_day"] in ["Friday", "Thursday", "Wednesday"]
        assert result["predicted_reach_multiplier"] > 1.0
        assert "reasoning" in result

def test_get_optimal_release_time_unknown_genre():
    result = get_optimal_release_time("polka")
    assert "optimal_day" in result
    assert "reasoning" in result


# ---------------------------------------------------------------------------
# API endpoint tests – oauth-url
# ---------------------------------------------------------------------------

def test_api_oauth_url_spotify():
    resp = client.get("/platform-connect/oauth-url", params={"platform": "spotify", "user_id": "u1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["platform"] == "spotify"
    assert "oauth_url" in data

def test_api_oauth_url_all_platforms():
    for platform in _VALID_PLATFORMS:
        resp = client.get("/platform-connect/oauth-url", params={"platform": platform, "user_id": "u1"})
        assert resp.status_code == 200

def test_api_oauth_url_invalid_platform():
    resp = client.get("/platform-connect/oauth-url", params={"platform": "myspace", "user_id": "u1"})
    assert resp.status_code == 422

def test_api_oauth_url_missing_params():
    resp = client.get("/platform-connect/oauth-url", params={"platform": "spotify"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# API endpoint tests – connect
# ---------------------------------------------------------------------------

def test_api_connect_valid():
    resp = client.post("/platform-connect/connect", json={
        "platform": "spotify", "user_id": "user1", "auth_code": "abc123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["platform"] == "spotify"

def test_api_connect_invalid_platform():
    resp = client.post("/platform-connect/connect", json={
        "platform": "myspace", "user_id": "user1", "auth_code": "abc"
    })
    assert resp.status_code == 422

def test_api_connect_empty_auth_code():
    resp = client.post("/platform-connect/connect", json={
        "platform": "spotify", "user_id": "user1", "auth_code": ""
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# API endpoint tests – disconnect
# ---------------------------------------------------------------------------

def test_api_disconnect_valid():
    resp = client.post("/platform-connect/disconnect", json={
        "platform": "spotify", "user_id": "user1"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False

def test_api_disconnect_invalid_platform():
    resp = client.post("/platform-connect/disconnect", json={
        "platform": "napster", "user_id": "user1"
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# API endpoint tests – platforms/{user_id}
# ---------------------------------------------------------------------------

def test_api_get_platforms():
    resp = client.get("/platform-connect/platforms/user42")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user42"
    assert len(data["platforms"]) == 5

def test_api_get_platforms_not_connected():
    resp = client.get("/platform-connect/platforms/testuser")
    data = resp.json()
    for p in data["platforms"]:
        assert p["connected"] is False


# ---------------------------------------------------------------------------
# API endpoint tests – distribute
# ---------------------------------------------------------------------------

def test_api_distribute_missing_title():
    resp = client.post("/platform-connect/distribute", json={
        "user_id": "user1",
        "platforms": ["spotify"],
        "content": {"type": "audio"},
    })
    assert resp.status_code == 422

def test_api_distribute_missing_type():
    resp = client.post("/platform-connect/distribute", json={
        "user_id": "user1",
        "platforms": ["spotify"],
        "content": {"title": "My Track"},
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# API endpoint tests – analytics
# ---------------------------------------------------------------------------

def test_api_analytics_all():
    resp = client.get("/platform-connect/analytics/user1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user1"
    assert data["platform"] == "all"

def test_api_analytics_specific_platform():
    resp = client.get("/platform-connect/analytics/user1", params={"platform": "spotify"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["platform"] == "spotify"

def test_api_analytics_has_top_content():
    resp = client.get("/platform-connect/analytics/user1")
    data = resp.json()
    assert "top_content" in data
    assert len(data["top_content"]) == 2


# ---------------------------------------------------------------------------
# API endpoint tests – epk
# ---------------------------------------------------------------------------

def test_api_epk_empty_genre():
    resp = client.post("/platform-connect/epk", json={
        "user_id": "u1",
        "artist_name": "Artist",
        "genre": "",
        "bio": "Some bio",
    })
    assert resp.status_code == 422

def test_api_epk_empty_bio():
    resp = client.post("/platform-connect/epk", json={
        "user_id": "u1",
        "artist_name": "Artist",
        "genre": "Pop",
        "bio": "",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# API endpoint tests – optimal-release
# ---------------------------------------------------------------------------

def test_api_optimal_release_pop():
    resp = client.get("/platform-connect/optimal-release", params={"genre": "pop"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["genre"] == "pop"
    assert data["optimal_day"] in ["Friday", "Thursday", "Wednesday"]
    assert data["optimal_time_utc"] == "14:00"

def test_api_optimal_release_with_region():
    resp = client.get("/platform-connect/optimal-release", params={"genre": "hip-hop", "target_region": "us"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_region"] == "us"

def test_api_optimal_release_missing_genre():
    resp = client.get("/platform-connect/optimal-release")
    assert resp.status_code == 422

def test_api_optimal_release_unknown_genre():
    resp = client.get("/platform-connect/optimal-release", params={"genre": "polka"})
    assert resp.status_code == 200
    data = resp.json()
    assert "optimal_day" in data


# ---------------------------------------------------------------------------
# V2 tests from origin/main refactored API (renamed to avoid duplicate test names)
# ---------------------------------------------------------------------------


def test_generate_epk_empty_artist_name_v2():
    with pytest.raises(ValueError, match="artist_name"):
        generate_epk("u1", "", "Pop", "Some bio")

def test_generate_epk_empty_bio_v2():
    with pytest.raises(ValueError, match="bio"):
        generate_epk("u1", "Artist", "Pop", "")


# ---------------------------------------------------------------------------
# get_optimal_release_time – unit tests
# ---------------------------------------------------------------------------

def test_api_distribute_valid_v2():
    resp = client.post("/platform-connect/distribute", json={
        "user_id": "user1",
        "platforms": ["spotify", "youtube"],
        "content": {"title": "My Track", "type": "audio", "description": "desc"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["queued"] == 2

def test_api_distribute_empty_platforms_v2():
    resp = client.post("/platform-connect/distribute", json={
        "user_id": "user1",
        "platforms": [],
        "content": {"title": "My Track", "type": "audio"},
    })
    assert resp.status_code == 422

def test_api_epk_valid_v2():
    resp = client.post("/platform-connect/epk", json={
        "user_id": "u1",
        "artist_name": "DJ Kala",
        "genre": "Electronic",
        "bio": "An electronic artist from the future.",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "generated"
    assert data["artist_name"] == "DJ Kala"
    assert "epk_url" in data

def test_api_epk_empty_artist_name_v2():
    resp = client.post("/platform-connect/epk", json={
        "user_id": "u1",
        "artist_name": "",
        "genre": "Pop",
        "bio": "Some bio",
    })
    assert resp.status_code == 422

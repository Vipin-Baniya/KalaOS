"""Tests for kalaplatformconnect module and /platform-connect/* endpoints."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient
from main import app
from kalacore.kalaplatformconnect import (
    get_oauth_url,
    connect_platform,
    disconnect_platform,
    get_connected_platforms,
    distribute_to_platforms,
    get_analytics_summary,
    generate_epk,
    get_optimal_release_time,
    _VALID_PLATFORMS,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# get_oauth_url – unit tests
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


def test_generate_epk_empty_artist_name():
    with pytest.raises(ValueError, match="artist_name"):
        generate_epk("u1", "", "Pop", "Some bio")


def test_generate_epk_empty_genre():
    with pytest.raises(ValueError, match="genre"):
        generate_epk("u1", "Artist", "", "Some bio")


def test_generate_epk_empty_bio():
    with pytest.raises(ValueError, match="bio"):
        generate_epk("u1", "Artist", "Pop", "")


# ---------------------------------------------------------------------------
# get_optimal_release_time – unit tests
# ---------------------------------------------------------------------------

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

def test_api_distribute_valid():
    resp = client.post("/platform-connect/distribute", json={
        "user_id": "user1",
        "platforms": ["spotify", "youtube"],
        "content": {"title": "My Track", "type": "audio", "description": "desc"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["queued"] == 2


def test_api_distribute_empty_platforms():
    resp = client.post("/platform-connect/distribute", json={
        "user_id": "user1",
        "platforms": [],
        "content": {"title": "My Track", "type": "audio"},
    })
    assert resp.status_code == 422


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

def test_api_epk_valid():
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


def test_api_epk_empty_artist_name():
    resp = client.post("/platform-connect/epk", json={
        "user_id": "u1",
        "artist_name": "",
        "genre": "Pop",
        "bio": "Some bio",
    })
    assert resp.status_code == 422


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

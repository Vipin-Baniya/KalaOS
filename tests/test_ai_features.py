"""Tests for AI feature endpoints."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# POST /ai/content-generator
# ---------------------------------------------------------------------------

def test_ai_content_generator_text_to_image():
    resp = client.post("/ai/content-generator", json={
        "type": "text_to_image",
        "content": "A futuristic cityscape at night",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "text_to_image"
    assert "image_concept" in data
    assert "style_suggestions" in data
    assert data["status"] == "generated"


def test_ai_content_generator_image_to_video():
    resp = client.post("/ai/content-generator", json={
        "type": "image_to_video",
        "content": "landscape.png",
        "options": {"animation_style": "zoom-in", "duration_seconds": 8},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "image_to_video"
    assert data["animation_style"] == "zoom-in"
    assert data["duration_seconds"] == 8
    assert "transitions" in data


def test_ai_content_generator_auto_caption():
    resp = client.post("/ai/content-generator", json={
        "type": "auto_caption",
        "content": "This is a sample video description that needs automatic captions generated",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "auto_caption"
    assert "captions" in data
    assert isinstance(data["captions"], list)
    assert len(data["captions"]) > 0


def test_ai_content_generator_invalid_type():
    resp = client.post("/ai/content-generator", json={
        "type": "text_to_audio",
        "content": "some content",
    })
    assert resp.status_code == 422


def test_ai_content_generator_empty_content():
    resp = client.post("/ai/content-generator", json={
        "type": "text_to_image",
        "content": "",
    })
    assert resp.status_code == 422


def test_ai_content_generator_whitespace_content():
    resp = client.post("/ai/content-generator", json={
        "type": "text_to_image",
        "content": "   ",
    })
    assert resp.status_code == 422


def test_ai_content_generator_with_options():
    resp = client.post("/ai/content-generator", json={
        "type": "text_to_image",
        "content": "A serene mountain lake",
        "options": {"dimensions": "512x512"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["dimensions"] == "512x512"


# ---------------------------------------------------------------------------
# POST /ai/analytics
# ---------------------------------------------------------------------------

def test_ai_analytics_valid():
    resp = client.post("/ai/analytics", json={
        "content_id": "post-abc-123",
        "content_type": "video",
        "time_range": "30d",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["content_id"] == "post-abc-123"
    assert data["content_type"] == "video"
    assert data["time_range"] == "30d"
    assert "performance" in data
    assert "audience" in data
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)


def test_ai_analytics_performance_fields():
    resp = client.post("/ai/analytics", json={
        "content_id": "post-xyz",
        "content_type": "image",
    })
    assert resp.status_code == 200
    perf = resp.json()["performance"]
    assert "views" in perf
    assert "likes" in perf
    assert "shares" in perf
    assert "comments" in perf
    assert "engagement_rate_pct" in perf


def test_ai_analytics_empty_content_id():
    resp = client.post("/ai/analytics", json={
        "content_id": "",
        "content_type": "video",
    })
    assert resp.status_code == 422


def test_ai_analytics_empty_content_type():
    resp = client.post("/ai/analytics", json={
        "content_id": "post-001",
        "content_type": "",
    })
    assert resp.status_code == 422


def test_ai_analytics_deterministic():
    payload = {"content_id": "stable-id-9999", "content_type": "music"}
    r1 = client.post("/ai/analytics", json=payload).json()
    r2 = client.post("/ai/analytics", json=payload).json()
    assert r1["performance"]["views"] == r2["performance"]["views"]


# ---------------------------------------------------------------------------
# POST /ai/smart-search
# ---------------------------------------------------------------------------

def test_ai_smart_search_valid():
    resp = client.post("/ai/smart-search", json={
        "query": "jazz piano improvisation",
        "limit": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "jazz piano improvisation"
    assert "results" in data
    assert "total_results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) <= 5


def test_ai_smart_search_result_fields():
    resp = client.post("/ai/smart-search", json={"query": "abstract art"})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) > 0
    r = results[0]
    assert "result_id" in r
    assert "title" in r
    assert "studio" in r
    assert "relevance_score" in r


def test_ai_smart_search_empty_query():
    resp = client.post("/ai/smart-search", json={"query": ""})
    assert resp.status_code == 422


def test_ai_smart_search_invalid_limit():
    resp = client.post("/ai/smart-search", json={"query": "test", "limit": 0})
    assert resp.status_code == 422


def test_ai_smart_search_with_content_types():
    resp = client.post("/ai/smart-search", json={
        "query": "rhythm and blues",
        "content_types": ["music", "video"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["content_types_searched"] == ["music", "video"]


# ---------------------------------------------------------------------------
# POST /ai/quality-check
# ---------------------------------------------------------------------------

def test_ai_quality_check_valid():
    resp = client.post("/ai/quality-check", json={
        "export_id": "exp-001",
        "format": "mp4",
        "content_preview": "video preview text",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["export_id"] == "exp-001"
    assert data["format"] == "mp4"
    assert "quality_score" in data
    assert "grade" in data
    assert "issues" in data
    assert "passed" in data
    assert isinstance(data["passed"], bool)


def test_ai_quality_check_grade_values():
    resp = client.post("/ai/quality-check", json={
        "export_id": "exp-gradetest",
        "format": "png",
    })
    assert resp.status_code == 200
    assert resp.json()["grade"] in ("A", "B", "C", "D")


def test_ai_quality_check_grade_logic():
    # exp-0 → score=65 → D, exp-1 → score=98 → A, exp-7 → score=87 → B, exp-3 → score=71 → C
    cases = [("exp-0", "D"), ("exp-1", "A"), ("exp-7", "B"), ("exp-3", "C")]
    for export_id, expected_grade in cases:
        resp = client.post("/ai/quality-check", json={"export_id": export_id, "format": "mp3"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["grade"] == expected_grade, f"{export_id}: expected {expected_grade}, got {data['grade']} (score={data['quality_score']})"


def test_ai_quality_check_empty_export_id():
    resp = client.post("/ai/quality-check", json={
        "export_id": "",
        "format": "mp4",
    })
    assert resp.status_code == 422


def test_ai_quality_check_empty_format():
    resp = client.post("/ai/quality-check", json={
        "export_id": "exp-001",
        "format": "",
    })
    assert resp.status_code == 422


def test_ai_quality_check_deterministic():
    payload = {"export_id": "stable-exp-42", "format": "wav"}
    r1 = client.post("/ai/quality-check", json=payload).json()
    r2 = client.post("/ai/quality-check", json=payload).json()
    assert r1["quality_score"] == r2["quality_score"]
    assert r1["grade"] == r2["grade"]

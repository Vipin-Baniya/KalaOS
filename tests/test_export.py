"""Tests for kalaexport module and /export/* endpoints."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient
from main import app
from kalacore.kalaexport import prepare_export, import_from_url, batch_export

client = TestClient(app)


# ---------------------------------------------------------------------------
# prepare_export – unit tests
# ---------------------------------------------------------------------------

def test_prepare_export_audio():
    for fmt in ("mp3", "wav", "flac", "ogg", "aac"):
        manifest = prepare_export("music", fmt, "audio content here", "high")
        assert manifest["studio"] == "music"
        assert manifest["format"] == fmt
        assert "export_id" in manifest
        assert "estimated_size_mb" in manifest
        assert manifest["status"] == "ready"


def test_prepare_export_video():
    for fmt in ("mp4", "webm", "mov", "avi", "mkv"):
        manifest = prepare_export("video", fmt, "video content here", "high")
        assert manifest["studio"] == "video"
        assert manifest["format"] == fmt


def test_prepare_export_image():
    for fmt in ("png", "jpg", "webp", "svg", "bmp"):
        manifest = prepare_export("visual", fmt, "image content", "medium")
        assert manifest["studio"] == "visual"
        assert manifest["format"] == fmt


def test_prepare_export_document():
    for fmt in ("pdf", "docx", "txt", "markdown"):
        manifest = prepare_export("text", fmt, "document content", "high")
        assert manifest["studio"] == "text"
        assert manifest["format"] == fmt


def test_prepare_export_animation():
    for fmt in ("mp4", "webm", "gif"):
        manifest = prepare_export("animation", fmt, "animation frames", "high")
        assert manifest["studio"] == "animation"


def test_prepare_export_mixed_studio():
    manifest = prepare_export("mixed", "mp4", "mixed content")
    assert manifest["studio"] == "mixed"


def test_prepare_export_invalid_format_for_studio():
    with pytest.raises(ValueError, match="format"):
        prepare_export("music", "mp4", "content")  # mp4 not valid for music


def test_prepare_export_invalid_studio():
    with pytest.raises(ValueError, match="studio"):
        prepare_export("3d", "mp4", "content")


def test_prepare_export_empty_content():
    with pytest.raises(ValueError, match="content"):
        prepare_export("music", "mp3", "")


def test_prepare_export_invalid_quality():
    with pytest.raises(ValueError, match="quality"):
        prepare_export("music", "mp3", "content", "ultra")


def test_prepare_export_content_preview_truncated():
    long_content = "a" * 300
    manifest = prepare_export("text", "txt", long_content)
    assert len(manifest["content_preview"]) <= 120


def test_prepare_export_unique_ids():
    m1 = prepare_export("music", "mp3", "same content")
    m2 = prepare_export("music", "mp3", "same content")
    assert m1["export_id"] != m2["export_id"]


# ---------------------------------------------------------------------------
# import_from_url – unit tests
# ---------------------------------------------------------------------------

def test_import_from_url_https():
    m = import_from_url("https://example.com/audio.mp3", "music")
    assert m["url"] == "https://example.com/audio.mp3"
    assert m["studio"] == "music"
    assert m["detected_format"] == "mp3"
    assert "import_id" in m
    assert m["status"] == "pending"


def test_import_from_url_http():
    m = import_from_url("http://example.com/video.mp4", "video")
    assert m["detected_format"] == "mp4"


def test_import_from_url_ftp():
    m = import_from_url("ftp://files.example.com/doc.pdf", "text")
    assert m["detected_format"] == "pdf"
    assert m["studio"] == "text"


def test_import_from_url_unknown_extension():
    m = import_from_url("https://example.com/file", "mixed")
    assert m["detected_format"] == "unknown"


def test_import_from_url_empty():
    with pytest.raises(ValueError, match="url"):
        import_from_url("", "music")


def test_import_from_url_no_scheme():
    with pytest.raises(ValueError, match="url"):
        import_from_url("example.com/audio.mp3", "music")


def test_import_from_url_invalid_scheme():
    with pytest.raises(ValueError, match="url"):
        import_from_url("ssh://example.com/file.mp3", "music")


def test_import_from_url_invalid_studio():
    with pytest.raises(ValueError, match="studio"):
        import_from_url("https://example.com/file.mp3", "podcast")


# ---------------------------------------------------------------------------
# batch_export – unit tests
# ---------------------------------------------------------------------------

def test_batch_export_valid():
    items = [
        {"studio": "music", "format": "mp3", "content": "track 1", "quality": "high"},
        {"studio": "video", "format": "mp4", "content": "scene 1", "quality": "medium"},
    ]
    result = batch_export(items)
    assert result["total_items"] == 2
    assert "batch_id" in result
    assert len(result["items"]) == 2
    assert result["status"] == "ready"
    assert result["estimated_total_size_mb"] > 0


def test_batch_export_single_item():
    items = [{"studio": "text", "format": "pdf", "content": "document text", "quality": "high"}]
    result = batch_export(items)
    assert result["total_items"] == 1


def test_batch_export_empty_items():
    with pytest.raises(ValueError, match="items"):
        batch_export([])


def test_batch_export_uses_default_quality():
    items = [{"studio": "music", "format": "wav", "content": "audio content"}]
    result = batch_export(items)
    assert result["items"][0]["quality"] == "high"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

def test_api_export_prepare():
    resp = client.post("/export/prepare", json={
        "studio": "music",
        "format": "mp3",
        "content": "My awesome track",
        "quality": "high",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["studio"] == "music"
    assert data["format"] == "mp3"
    assert "export_id" in data


def test_api_export_prepare_invalid_format():
    resp = client.post("/export/prepare", json={
        "studio": "music",
        "format": "mp4",
        "content": "audio content",
    })
    assert resp.status_code == 422


def test_api_export_prepare_invalid_studio():
    resp = client.post("/export/prepare", json={
        "studio": "radio",
        "format": "mp3",
        "content": "audio",
    })
    assert resp.status_code == 422


def test_api_export_import_url():
    resp = client.post("/export/import-url", json={
        "url": "https://example.com/track.wav",
        "studio": "music",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected_format"] == "wav"
    assert data["status"] == "pending"


def test_api_export_import_url_no_scheme():
    resp = client.post("/export/import-url", json={
        "url": "example.com/track.wav",
        "studio": "music",
    })
    assert resp.status_code == 422


def test_api_export_batch():
    resp = client.post("/export/batch", json={
        "items": [
            {"studio": "visual", "format": "png", "content": "image data", "quality": "high"},
            {"studio": "text", "format": "txt", "content": "text data", "quality": "low"},
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["quality"] == "high"
    assert data["items"][1]["quality"] == "low"
    assert data["items"][0]["studio"] == "visual"
    assert data["items"][1]["studio"] == "text"
    assert "estimated_total_size_mb" in data
    assert data["status"] == "ready"


def test_api_export_batch_empty():
    resp = client.post("/export/batch", json={"items": []})
    assert resp.status_code == 422

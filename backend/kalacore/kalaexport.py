"""
KalaExport – Export & Import Module
-------------------------------------
Provides functions for preparing file exports, importing from URLs,
and processing batch export manifests across all KalaOS studios.

Public API
----------
prepare_export(studio, format, content, quality)
    Returns an export manifest dict.

import_from_url(url, studio)
    Returns an import manifest dict.

batch_export(items)
    Returns a batch export manifest dict.
"""

from __future__ import annotations

import datetime
import hashlib
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Valid values
# ---------------------------------------------------------------------------

_VALID_STUDIOS: set[str] = {"text", "music", "visual", "animation", "video", "mixed"}

_STUDIO_FORMATS: dict[str, set[str]] = {
    "music":     {"mp3", "wav", "flac", "ogg", "aac"},
    "video":     {"mp4", "webm", "mov", "avi", "mkv"},
    "visual":    {"png", "jpg", "webp", "svg", "bmp"},
    "text":      {"pdf", "docx", "txt", "markdown"},
    "animation": {"mp4", "webm", "gif"},
    "mixed": {
        "mp3", "wav", "flac", "ogg", "aac",
        "mp4", "webm", "mov", "avi", "mkv",
        "png", "jpg", "webp", "svg", "bmp",
        "pdf", "docx", "txt", "markdown", "gif",
    },
}

# ---------------------------------------------------------------------------
# Format → estimated MB per minute / per unit
# ---------------------------------------------------------------------------

_FORMAT_SIZE_MB: dict[str, float] = {
    "mp3": 1.0, "wav": 10.0, "flac": 5.0, "ogg": 0.9, "aac": 0.8,
    "mp4": 30.0, "webm": 20.0, "mov": 40.0, "avi": 50.0, "mkv": 35.0,
    "png": 2.0, "jpg": 0.5, "webp": 0.3, "svg": 0.1, "bmp": 5.0,
    "pdf": 0.5, "docx": 0.2, "txt": 0.01, "markdown": 0.01,
    "gif": 8.0,
}

# ---------------------------------------------------------------------------
# Valid quality values
# ---------------------------------------------------------------------------

_VALID_QUALITIES: set[str] = {"low", "medium", "high", "lossless"}

_QUALITY_MULTIPLIER: dict[str, float] = {
    "low": 0.5,
    "medium": 1.0,
    "high": 1.8,
    "lossless": 3.0,
}

# ---------------------------------------------------------------------------
# Detected format from URL extension
# ---------------------------------------------------------------------------

_EXTENSION_FORMAT: dict[str, str] = {
    ".mp3": "mp3", ".wav": "wav", ".flac": "flac", ".ogg": "ogg", ".aac": "aac",
    ".mp4": "mp4", ".webm": "webm", ".mov": "mov", ".avi": "avi", ".mkv": "mkv",
    ".png": "png", ".jpg": "jpg", ".jpeg": "jpg", ".webp": "webp",
    ".svg": "svg", ".bmp": "bmp",
    ".pdf": "pdf", ".docx": "docx", ".txt": "txt", ".md": "markdown",
    ".gif": "gif",
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _estimate_size(fmt: str, quality: str, content_len: int) -> float:
    base = _FORMAT_SIZE_MB.get(fmt, 1.0)
    multiplier = _QUALITY_MULTIPLIER.get(quality, 1.0)
    length_factor = max(1.0, content_len / 500)
    return round(base * multiplier * length_factor, 2)


def _detect_format(url: str) -> str:
    lower = url.lower()
    for ext, fmt in _EXTENSION_FORMAT.items():
        if lower.endswith(ext):
            return fmt
    return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def prepare_export(
    studio: str,
    format: str,
    content: str,
    quality: str = "high",
) -> dict[str, Any]:
    """Prepare an export manifest for the given studio and format.

    Parameters
    ----------
    studio:  Source studio type.
    format:  Target file format.
    content: Content to export (text representation or identifier).
    quality: Export quality level.

    Returns
    -------
    Export manifest dict with keys: export_id, studio, format,
    content_preview, quality, estimated_size_mb, settings, status.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if studio not in _VALID_STUDIOS:
        raise ValueError(f"studio must be one of {sorted(_VALID_STUDIOS)}")
    if not content or not content.strip():
        raise ValueError("content must not be empty")
    if quality not in _VALID_QUALITIES:
        raise ValueError(f"quality must be one of {sorted(_VALID_QUALITIES)}")

    valid_formats = _STUDIO_FORMATS[studio]
    if format not in valid_formats:
        raise ValueError(
            f"format '{format}' is not valid for studio '{studio}'. "
            f"Valid formats: {sorted(valid_formats)}"
        )

    export_id = str(uuid.uuid4())
    content_stripped = content.strip()
    estimated_size = _estimate_size(format, quality, len(content_stripped))

    return {
        "export_id": export_id,
        "studio": studio,
        "format": format,
        "content_preview": content_stripped[:120],
        "quality": quality,
        "estimated_size_mb": estimated_size,
        "settings": {
            "quality_multiplier": _QUALITY_MULTIPLIER[quality],
            "base_size_mb": _FORMAT_SIZE_MB.get(format, 1.0),
        },
        "status": "ready",
    }


def import_from_url(
    url: str,
    studio: str,
) -> dict[str, Any]:
    """Create an import manifest from a remote URL.

    Parameters
    ----------
    url:    Source URL (must start with http://, https://, or ftp://).
    studio: Target studio for the imported content.

    Returns
    -------
    Import manifest dict with keys: import_id, url, studio,
    detected_format, status, metadata.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if not url or not url.strip():
        raise ValueError("url must not be empty")
    stripped_url = url.strip()
    if not (
        stripped_url.startswith("http://")
        or stripped_url.startswith("https://")
        or stripped_url.startswith("ftp://")
    ):
        raise ValueError("url must start with http://, https://, or ftp://")
    if studio not in _VALID_STUDIOS:
        raise ValueError(f"studio must be one of {sorted(_VALID_STUDIOS)}")

    import_id = str(uuid.uuid4())
    detected_format = _detect_format(stripped_url)

    return {
        "import_id": import_id,
        "url": stripped_url,
        "studio": studio,
        "detected_format": detected_format,
        "status": "pending",
        "metadata": {
            "url_hash": hashlib.md5(stripped_url.encode()).hexdigest(),
            "queued_at": _now(),
        },
    }


def batch_export(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Process a batch of export requests.

    Parameters
    ----------
    items: Non-empty list of dicts, each with keys:
           studio, format, content, quality.

    Returns
    -------
    Batch manifest dict with keys: batch_id, total_items,
    items (list of export manifests), estimated_total_size_mb, status.

    Raises
    ------
    ValueError for invalid inputs.
    """
    if not items:
        raise ValueError("items must be a non-empty list")

    batch_id = str(uuid.uuid4())
    export_manifests: list[dict[str, Any]] = []
    total_size = 0.0

    for idx, item in enumerate(items):
        studio  = item.get("studio", "")
        fmt     = item.get("format", "")
        content = item.get("content", "")
        quality = item.get("quality", "high")
        manifest = prepare_export(studio, fmt, content, quality)
        export_manifests.append(manifest)
        total_size += manifest["estimated_size_mb"]

    return {
        "batch_id": batch_id,
        "total_items": len(export_manifests),
        "items": export_manifests,
        "estimated_total_size_mb": round(total_size, 2),
        "status": "ready",
    }

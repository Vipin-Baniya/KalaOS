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
from typing import Any, Optional

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


_EXPORT_REGISTRY: dict[str, dict[str, Any]] = {}


def clear_export_registry() -> None:
    """Test helper: wipe registered exports."""
    _EXPORT_REGISTRY.clear()


def get_export(export_id: str) -> Optional[dict[str, Any]]:
    if not export_id or not str(export_id).strip():
        return None
    return _EXPORT_REGISTRY.get(str(export_id).strip())


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

    manifest = {
        "export_id": export_id,
        "studio": studio,
        "format": format,
        "content": content_stripped,
        "content_preview": content_stripped[:120],
        "quality": quality,
        "estimated_size_mb": estimated_size,
        "settings": {
            "quality_multiplier": _QUALITY_MULTIPLIER[quality],
            "base_size_mb": _FORMAT_SIZE_MB.get(format, 1.0),
        },
        "status": "ready",
        "created_at": _now(),
    }
    # Persist for quality checks / later retrieval (without exposing full content in API copies).
    _EXPORT_REGISTRY[export_id] = dict(manifest)
    public = dict(manifest)
    public.pop("content", None)
    return public


def analyze_export_quality(
    export_id: str,
    format: str,
    content_preview: str = "",
) -> dict[str, Any]:
    """Score a registered export from measurable content properties.

    Raises
    ------
    FileNotFoundError if export_id is unknown.
    ValueError for invalid inputs / format mismatch / empty artifact content.
    """
    if not export_id or not str(export_id).strip():
        raise ValueError("export_id must not be empty")
    if not format or not str(format).strip():
        raise ValueError("format must not be empty")

    export_id = str(export_id).strip()
    fmt = str(format).strip().lower()
    record = get_export(export_id)
    if record is None:
        raise FileNotFoundError(f"export '{export_id}' not found")

    stored_fmt = str(record.get("format", "")).lower()
    if stored_fmt and stored_fmt != fmt:
        raise ValueError(
            f"format '{fmt}' does not match registered export format '{stored_fmt}'"
        )

    content = str(record.get("content") or "").strip()
    if not content:
        raise ValueError("registered export has no analyzable content")

    # Preview text must not override artifact analysis.
    preview = (content_preview or "").strip()
    preview_ignored = bool(preview) and preview != content and preview != content[:120]

    length = len(content)
    unique_ratio = len(set(content.lower())) / max(1, length)
    quality = str(record.get("quality") or "medium")
    size_mb = float(record.get("estimated_size_mb") or 0)

    score = 40
    issues: list[str] = []
    suggestions: list[str] = [
        "Verify codec compatibility with target platform",
        "Run a preview before final distribution",
    ]

    # Length / substance
    if length < 20:
        score -= 15
        issues.append("Export content is very short")
    elif length < 80:
        score += 5
    else:
        score += 15

    # Diversity of content characters
    if unique_ratio < 0.08:
        score -= 20
        issues.append("Content looks repetitive or low-entropy")
    elif unique_ratio > 0.2:
        score += 10

    # Format-aware heuristics
    if fmt in {"mp3", "wav", "flac", "ogg", "aac", "mp4", "webm", "mov", "avi", "mkv", "gif"}:
        if size_mb < 0.5:
            score -= 10
            issues.append("Estimated media size is unusually small")
        if quality in {"high", "lossless"}:
            score += 8
        elif quality == "low":
            score -= 8
            issues.append("Export quality is set to low")
    elif fmt in {"png", "jpg", "webp", "svg", "bmp"}:
        if length < 40:
            issues.append("Visual export payload metadata is thin")
            score -= 5
        else:
            score += 8
    elif fmt in {"pdf", "docx", "txt", "markdown"}:
        words = [w for w in content.replace("\n", " ").split(" ") if w]
        if len(words) < 10:
            issues.append("Text export has few words")
            score -= 8
        else:
            score += 10

    score = max(0, min(100, int(round(score))))
    grade = "A" if score >= 90 else ("B" if score >= 80 else ("C" if score >= 70 else "D"))
    if score < 75:
        issues.append("Bitrate / quality below recommended threshold")
    if score < 85 and "Consider increasing export quality setting" not in issues:
        issues.append("Consider increasing export quality setting")

    return {
        "export_id": export_id,
        "format": fmt,
        "quality_score": score,
        "grade": grade,
        "issues": issues,
        "suggestions": suggestions,
        "passed": score >= 70,
        "analysis_source": "registered_export",
        "preview_ignored": preview_ignored,
        "content_length": length,
        "studio": record.get("studio"),
        "export_quality": quality,
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

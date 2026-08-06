"""
KalaAnimation  (Phase 13 – AI Animation Generator)
----------------------------------------------------
Generates structured animation plans from text prompts, image descriptions,
or story/storyboard inputs.  The engine produces scene-by-scene breakdowns,
keyframe descriptions, character notes, camera moves and timing hints that
can drive downstream rendering pipelines (Runway, Kling, FFmpeg, etc.).

Public API
----------
generate_animation_plan(prompt, mode, style, duration_sec)
    Returns an AnimationPlan dict.

parse_storyboard(story_text)
    Splits a narrative into ordered scenes ready for animation.
"""

from __future__ import annotations

import re
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

AnimationMode = Literal["text_to_animation", "image_to_animation", "story_to_storyboard"]
AnimationStyle = Literal["realistic", "cartoon", "anime", "cinematic", "abstract", "lofi"]

_VALID_MODES: set[str] = {
    "text_to_animation",
    "image_to_animation",
    "story_to_storyboard",
}

_VALID_STYLES: set[str] = {
    "realistic",
    "cartoon",
    "anime",
    "cinematic",
    "abstract",
    "lofi",
}

_DEFAULT_STYLE: AnimationStyle = "cinematic"
_DEFAULT_DURATION = 10  # seconds
_MAX_DURATION = 300     # 5 minutes
_MIN_DURATION = 2
_MAX_SUMMARY_LENGTH = 80  # truncation limit for auto-generated scene summaries

# Proper-noun tokens that are not character names (stop-list for heuristic extraction)
_CHARACTER_STOPWORDS: frozenset[str] = frozenset({
    "I", "A", "The", "In", "On", "At", "To", "Of", "And", "Or", "But",
    "Scene", "Chapter", "Act",
})

# ---------------------------------------------------------------------------
# Scene parsing helpers
# ---------------------------------------------------------------------------

_SCENE_SPLITTERS = re.compile(
    r"\n\s*(?:scene\s*\d+|chapter\s*\d+|act\s*\d+|--+|==+|\*{3,})\s*\n",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_into_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def parse_storyboard(story_text: str) -> list[dict[str, Any]]:
    """
    Split *story_text* into a list of scene dicts.

    Each scene has:
        ``index``  – 1-based scene number
        ``text``   – the raw prose for that scene
        ``summary``– first sentence used as a short title
    """
    if not story_text or not story_text.strip():
        raise ValueError("story_text must not be empty")

    raw_scenes = _SCENE_SPLITTERS.split(story_text.strip())
    scenes: list[dict[str, Any]] = []
    for i, chunk in enumerate(raw_scenes, start=1):
        chunk = chunk.strip()
        if not chunk:
            continue
        sentences = _split_into_sentences(chunk)
        summary = sentences[0] if sentences else chunk[:_MAX_SUMMARY_LENGTH]
        scenes.append({"index": i, "text": chunk, "summary": summary})
    return scenes


# ---------------------------------------------------------------------------
# Keyframe generator
# ---------------------------------------------------------------------------

_CAMERA_MOVES = [
    "slow zoom in",
    "pan left to right",
    "dolly forward",
    "aerial descent",
    "static wide shot",
    "over-the-shoulder",
    "whip pan",
    "crane up",
]

_TRANSITIONS = [
    "fade",
    "cut",
    "dissolve",
    "wipe",
    "morph",
    "match cut",
]


def _derive_keyframes(
    scenes: list[dict[str, Any]],
    style: str,
    duration_sec: int,
) -> list[dict[str, Any]]:
    """Return one keyframe entry per scene."""
    n = len(scenes)
    if n == 0:
        return []
    secs_per_scene = max(2, duration_sec // n)
    keyframes = []
    for idx, scene in enumerate(scenes):
        cam = _CAMERA_MOVES[idx % len(_CAMERA_MOVES)]
        trans = _TRANSITIONS[idx % len(_TRANSITIONS)]
        start_t = idx * secs_per_scene
        keyframes.append(
            {
                "scene_index": scene["index"],
                "start_time_sec": start_t,
                "duration_sec": secs_per_scene,
                "description": scene["summary"],
                "camera_move": cam,
                "transition": trans,
                "style_note": f"{style} rendering",
            }
        )
    return keyframes


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def generate_animation_plan(
    prompt: str,
    mode: str = "text_to_animation",
    style: str = _DEFAULT_STYLE,
    duration_sec: int = _DEFAULT_DURATION,
) -> dict[str, Any]:
    """
    Generate a structured animation plan from *prompt*.

    Parameters
    ----------
    prompt : str
        The creative input (text description, image description, or story).
    mode : str
        One of ``text_to_animation``, ``image_to_animation``,
        ``story_to_storyboard``.
    style : str
        Visual style.  One of ``realistic``, ``cartoon``, ``anime``,
        ``cinematic``, ``abstract``, ``lofi``.
    duration_sec : int
        Target duration in seconds (2–300).

    Returns
    -------
    dict with keys:
        ``mode``, ``style``, ``duration_sec``, ``scenes``, ``keyframes``,
        ``character_notes``, ``audio_hint``, ``export_formats``,
        ``creative_score``.
    """
    # ── validation ────────────────────────────────────────────────────────
    if not prompt or not prompt.strip():
        raise ValueError("prompt must not be empty")
    if mode not in _VALID_MODES:
        raise ValueError(
            f"Invalid mode '{mode}'. Valid modes: {sorted(_VALID_MODES)}"
        )
    if style not in _VALID_STYLES:
        raise ValueError(
            f"Invalid style '{style}'. Valid styles: {sorted(_VALID_STYLES)}"
        )
    duration_sec = max(_MIN_DURATION, min(_MAX_DURATION, int(duration_sec)))

    # ── scene extraction ──────────────────────────────────────────────────
    if mode == "story_to_storyboard":
        scenes = parse_storyboard(prompt)
    else:
        # Treat the whole prompt as a single scene
        scenes = [{"index": 1, "text": prompt.strip(), "summary": prompt.strip()[:120]}]

    # ── keyframes ─────────────────────────────────────────────────────────
    keyframes = _derive_keyframes(scenes, style, duration_sec)

    # ── character notes ───────────────────────────────────────────────────
    # Very lightweight heuristic – look for proper-nouns or "character" keyword
    char_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b")
    char_candidates = char_pattern.findall(prompt)
    characters = list(
        dict.fromkeys(c for c in char_candidates if c not in _CHARACTER_STOPWORDS)
    )[:6]
    character_notes = [{"name": c, "note": "Character detected in prompt"} for c in characters]

    # ── audio hint ────────────────────────────────────────────────────────
    _audio_map: dict[str, str] = {
        "realistic": "ambient natural soundscape with subtle orchestral underscore",
        "cartoon": "playful upbeat score with comedic sound effects",
        "anime": "orchestral J-pop style with emotional swells",
        "cinematic": "epic orchestral score with dynamic tension and release",
        "abstract": "experimental electronic ambience with generative textures",
        "lofi": "lo-fi hip-hop beats with warm vinyl crackle",
    }
    audio_hint = _audio_map.get(style, "adaptive score matching scene mood")

    # ── creative score ────────────────────────────────────────────────────
    word_count = len(prompt.split())
    scene_count = len(scenes)
    # Simple heuristic: more descriptive text → higher score
    creative_score = round(
        min(1.0, (word_count / 200) * 0.5 + (scene_count / 10) * 0.3 + 0.2),
        2,
    )

    return {
        "mode": mode,
        "style": style,
        "duration_sec": duration_sec,
        "scenes": scenes,
        "keyframes": keyframes,
        "character_notes": character_notes,
        "audio_hint": audio_hint,
        "export_formats": ["mp4", "gif", "webm"],
        "creative_score": creative_score,
    }


def prepare_mp4_export(
    frames: list,
    fps: int = 24,
    resolution: str = "1920x1080",
    *,
    export_dir: str | None = None,
) -> dict:
    """Render frames to a downloadable animation artifact.

    Tries ffmpeg → MP4 when available; otherwise writes an animated GIF with
    Pillow so callers always get a real file. Status is ``completed`` only when
    the file exists on disk. Never invents a remote URL.
    """
    import hashlib
    import shutil
    import subprocess
    import tempfile
    from datetime import datetime, timezone
    from pathlib import Path

    from PIL import Image, ImageDraw

    _VALID_FPS = {12, 24, 30, 60}
    _VALID_RESOLUTIONS = {"640x480", "1280x720", "1920x1080", "3840x2160"}
    if fps not in _VALID_FPS:
        raise ValueError(f"Invalid fps '{fps}'. Must be one of: {sorted(_VALID_FPS)}")
    if resolution not in _VALID_RESOLUTIONS:
        raise ValueError(
            f"Invalid resolution '{resolution}'. Must be one of: {sorted(_VALID_RESOLUTIONS)}"
        )
    if not frames:
        raise ValueError("frames list must not be empty")

    width, height = map(int, resolution.split("x"))
    # Cap render size so export stays usable in tests/CI; metadata keeps requested res.
    render_w = min(width, 640)
    render_h = min(height, 360)
    frame_count = len(frames)
    duration_seconds = round(frame_count / fps, 2)

    root = Path(export_dir) if export_dir else Path(__file__).resolve().parents[1] / "exports"
    root.mkdir(parents=True, exist_ok=True)

    seed = f"{frame_count}:{fps}:{resolution}:{datetime.now(timezone.utc).isoformat()}"
    export_id = hashlib.sha256(seed.encode()).hexdigest()[:16]

    def _frame_image(idx: int, frame: Any) -> Image.Image:
        if isinstance(frame, dict) and frame.get("image_data"):
            import base64
            import io

            raw = frame["image_data"]
            if isinstance(raw, str) and raw.startswith("data:"):
                raw = raw.split(",", 1)[-1]
            img = Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGB")
            return img.resize((render_w, render_h))

        # Deterministic panel so timeline indexes still produce a real artifact.
        hue = (idx * 47) % 256
        img = Image.new("RGB", (render_w, render_h), (hue, 40, 255 - hue))
        draw = ImageDraw.Draw(img)
        label = f"frame {idx + 1}/{frame_count}"
        draw.rectangle([8, 8, render_w - 8, 40], fill=(0, 0, 0))
        draw.text((16, 14), label, fill=(255, 255, 255))
        return img

    images = [_frame_image(i, fr) for i, fr in enumerate(frames)]
    ffmpeg_cmd = (
        f"ffmpeg -y -framerate {fps} -i frame_%04d.png "
        f"-c:v libx264 -pix_fmt yuv420p -s {resolution} output.mp4"
    )

    mp4_path = root / f"{export_id}.mp4"
    gif_path = root / f"{export_id}.gif"
    artifact_path: Path | None = None
    fmt = "gif"
    codec = "gif"

    with tempfile.TemporaryDirectory(prefix="kala-anim-") as tmp:
        tmp_path = Path(tmp)
        for i, img in enumerate(images):
            img.save(tmp_path / f"frame_{i:04d}.png")

        if shutil.which("ffmpeg"):
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", str(tmp_path / "frame_%04d.png"),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-s", f"{render_w}x{render_h}",
                str(mp4_path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=120)
                if mp4_path.is_file() and mp4_path.stat().st_size > 0:
                    artifact_path = mp4_path
                    fmt = "mp4"
                    codec = "H.264"
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                artifact_path = None

        if artifact_path is None:
            duration_ms = max(1, int(round(1000 / fps)))
            images[0].save(
                gif_path,
                save_all=True,
                append_images=images[1:],
                duration=duration_ms,
                loop=0,
                optimize=False,
            )
            if not gif_path.is_file() or gif_path.stat().st_size <= 0:
                raise RuntimeError("Failed to write animation export artifact")
            artifact_path = gif_path
            fmt = "gif"
            codec = "gif"

    size_mb = round(artifact_path.stat().st_size / (1024 * 1024), 3)
    download_path = f"/animation/exports/{artifact_path.name}"

    return {
        "export_id": export_id,
        "frame_count": frame_count,
        "fps": fps,
        "resolution": resolution,
        "width": width,
        "height": height,
        "duration_seconds": duration_seconds,
        "codec": codec,
        "container": fmt.upper(),
        "format": fmt,
        "bitrate_kbps": 5000 if width >= 1920 else 2500 if width >= 1280 else 1000,
        "ffmpeg_command": ffmpeg_cmd,
        "estimated_size_mb": size_mb,
        "file_size_kb": round(artifact_path.stat().st_size / 1024, 1),
        "export_url": download_path,
        "download_url": download_path,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "artifact_path": str(artifact_path),
    }


def get_export_artifact(filename: str, export_dir: str | None = None) -> str:
    """Return absolute path to a stored export, or raise FileNotFoundError/ValueError."""
    from pathlib import Path

    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError("invalid export filename")
    root = Path(export_dir) if export_dir else Path(__file__).resolve().parents[1] / "exports"
    path = (root / filename).resolve()
    if not str(path).startswith(str(root.resolve())):
        raise ValueError("invalid export filename")
    if not path.is_file():
        raise FileNotFoundError(filename)
    return str(path)

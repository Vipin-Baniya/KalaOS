"""
KalaVideo  (Phase 15 – AI Video Generator)
------------------------------------------
Scene-based video script generator.  Converts text prompts into structured
scene plans that drive the frontend preview player and downstream rendering
pipelines (FFmpeg, etc.).

Public API
----------
generate_video_script(prompt, style, scene_count)
    Returns a VideoScript dict with ``scenes`` list.

build_scene(index, text, image_concept, animation, duration, voice_text, bg_music)
    Constructs and validates a single scene dict.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Types & constants
# ---------------------------------------------------------------------------

VideoStyle = Literal[
    "cinematic",
    "motivational",
    "documentary",
    "cartoon",
    "lofi",
    "corporate",
    "abstract",
]

_VALID_STYLES: set[str] = {
    "cinematic",
    "motivational",
    "documentary",
    "cartoon",
    "lofi",
    "corporate",
    "abstract",
}

_VALID_ANIMATIONS: set[str] = {
    "fade",
    "slide-left",
    "slide-right",
    "zoom-in",
    "zoom-out",
    "dissolve",
    "none",
}

_DEFAULT_STYLE: VideoStyle = "cinematic"
_DEFAULT_SCENE_COUNT = 5
_MIN_SCENE_COUNT = 1
_MAX_SCENE_COUNT = 20
_DEFAULT_SCENE_DURATION = 4   # seconds
_MIN_DURATION = 1
_MAX_DURATION = 30

# ---------------------------------------------------------------------------
# Image concept palette (maps style → background theme keywords)
# ---------------------------------------------------------------------------

_STYLE_IMAGE_THEMES: dict[str, list[str]] = {
    "cinematic": [
        "dramatic landscape with golden hour lighting",
        "rain-soaked city street at night with neon reflections",
        "vast mountain range under stormy skies",
        "close-up portrait with cinematic bokeh background",
        "silhouette against a burning sunset horizon",
    ],
    "motivational": [
        "sunrise over a mountain peak symbolising new beginnings",
        "lone runner on an open road heading towards light",
        "outstretched hand reaching for a glowing star",
        "diverse team celebrating a hard-won victory",
        "open notebook surrounded by candles and positive quotes",
    ],
    "documentary": [
        "candid street scene with people in daily life",
        "aerial view of a bustling marketplace",
        "close-up of worn hands crafting traditional art",
        "vintage photograph style landscape",
        "interview-style neutral background with soft studio light",
    ],
    "cartoon": [
        "vibrant hand-drawn cartoon landscape",
        "colourful animated city with friendly characters",
        "playful flat-design nature scene",
        "retro comic-style panel with bold outlines",
        "cheerful pastel background with cartoon sun",
    ],
    "lofi": [
        "cosy bedroom desk at dusk with warm lamp glow",
        "rainy window with condensation and soft bokeh",
        "vintage cassette tape surrounded by autumn leaves",
        "lo-fi pixel art cityscape at twilight",
        "hand-drawn coffee-cup sketch on notebook paper",
    ],
    "corporate": [
        "clean modern office with city view",
        "diverse professional team in a bright meeting room",
        "data dashboard on a sleek monitor",
        "minimalist brand logo on white background",
        "confident presenter on an auditorium stage",
    ],
    "abstract": [
        "fluid colour wash with contrasting paint swirls",
        "geometric shapes dissolving into light particles",
        "fractal spiral in deep space",
        "neon wireframe grid receding into the horizon",
        "watercolour bleed on textured paper",
    ],
}

_STYLE_BG_MUSIC: dict[str, str] = {
    "cinematic": "epic orchestral score with rising strings",
    "motivational": "uplifting electronic beat with motivational piano",
    "documentary": "ambient acoustic guitar with subtle percussion",
    "cartoon": "playful xylophone melody with light brass stings",
    "lofi": "lo-fi hip-hop beat with warm vinyl crackle",
    "corporate": "clean upbeat corporate pop with light piano",
    "abstract": "experimental electronic ambience with generative textures",
}

_STYLE_ANIMATIONS: dict[str, list[str]] = {
    "cinematic": ["fade", "dissolve", "zoom-in"],
    "motivational": ["zoom-in", "slide-left", "fade"],
    "documentary": ["fade", "dissolve", "none"],
    "cartoon": ["slide-left", "slide-right", "zoom-in"],
    "lofi": ["fade", "dissolve", "none"],
    "corporate": ["slide-left", "fade", "zoom-out"],
    "abstract": ["dissolve", "zoom-in", "fade"],
}

# ---------------------------------------------------------------------------
# Sentence splitter
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_into_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def build_scene(
    index: int,
    text: str,
    image_concept: str = "",
    animation: str = "fade",
    duration: int = _DEFAULT_SCENE_DURATION,
    voice_text: str = "",
    bg_music: str = "",
) -> dict[str, Any]:
    """
    Construct and validate a single scene dict.

    Parameters
    ----------
    index : int
        1-based scene index.
    text : str
        On-screen display text / caption.
    image_concept : str
        Background image description / concept for AI generation.
    animation : str
        Transition animation type.  One of ``fade``, ``slide-left``,
        ``slide-right``, ``zoom-in``, ``zoom-out``, ``dissolve``, ``none``.
    duration : int
        Scene duration in seconds (1–30).
    voice_text : str
        Narration text for TTS.  Defaults to *text* when empty.
    bg_music : str
        Background music description / mood hint.

    Returns
    -------
    dict with keys matching the frontend scene schema.
    """
    if not isinstance(index, int) or index < 1:
        raise ValueError("index must be a positive integer")
    if not text or not str(text).strip():
        raise ValueError("text must not be empty")
    animation = animation if animation in _VALID_ANIMATIONS else "fade"
    duration = max(_MIN_DURATION, min(_MAX_DURATION, int(duration)))
    voice_text = voice_text.strip() if voice_text else text.strip()

    return {
        "index": index,
        "text": text.strip(),
        "image_concept": image_concept.strip() if image_concept else "",
        "animation": animation,
        "duration": duration,
        "voice_text": voice_text,
        "bg_music": bg_music.strip() if bg_music else "",
    }


def generate_video_script(
    prompt: str,
    style: str = _DEFAULT_STYLE,
    scene_count: int = _DEFAULT_SCENE_COUNT,
) -> dict[str, Any]:
    """
    Convert a text *prompt* into a structured video script.

    Parameters
    ----------
    prompt : str
        User input — a poem, idea, script fragment, or free-form description.
    style : str
        Visual / tonal style.  One of ``cinematic``, ``motivational``,
        ``documentary``, ``cartoon``, ``lofi``, ``corporate``, ``abstract``.
    scene_count : int
        Desired number of scenes (1–20).  Actual count may vary depending on
        the length of the prompt.

    Returns
    -------
    dict with keys:
        ``prompt``, ``style``, ``scenes``, ``total_duration``,
        ``bg_music_hint``, ``creative_score``.
    """
    # ── validation ────────────────────────────────────────────────────────
    if not prompt or not prompt.strip():
        raise ValueError("prompt must not be empty")
    if style not in _VALID_STYLES:
        raise ValueError(
            f"Invalid style '{style}'. Valid styles: {sorted(_VALID_STYLES)}"
        )
    scene_count = max(_MIN_SCENE_COUNT, min(_MAX_SCENE_COUNT, int(scene_count)))

    # ── split prompt into sentence fragments ──────────────────────────────
    sentences = _split_into_sentences(prompt.strip())
    if not sentences:
        sentences = [prompt.strip()]

    # Distribute sentences into the requested number of scenes
    # If fewer sentences than scenes, repeat or pad with a single sentence per scene
    chunks: list[str] = []
    if len(sentences) <= scene_count:
        # One sentence per scene; pad last scenes with evolved versions
        chunks = list(sentences)
        while len(chunks) < scene_count:
            chunks.append(sentences[(len(chunks)) % len(sentences)])
    else:
        # Merge excess sentences into scene_count groups
        per = len(sentences) // scene_count
        for i in range(scene_count):
            start = i * per
            end = start + per if i < scene_count - 1 else len(sentences)
            chunks.append(" ".join(sentences[start:end]))

    # ── build scenes ──────────────────────────────────────────────────────
    images = _STYLE_IMAGE_THEMES.get(style, _STYLE_IMAGE_THEMES["cinematic"])
    anims = _STYLE_ANIMATIONS.get(style, ["fade"])
    bg_music = _STYLE_BG_MUSIC.get(style, "ambient background music")

    scenes: list[dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        image_concept = images[i % len(images)]
        animation = anims[i % len(anims)]
        scene = build_scene(
            index=i + 1,
            text=chunk,
            image_concept=image_concept,
            animation=animation,
            duration=_DEFAULT_SCENE_DURATION,
            voice_text=chunk,
            bg_music=bg_music,
        )
        scenes.append(scene)

    total_duration = sum(s["duration"] for s in scenes)

    # ── creative score ────────────────────────────────────────────────────
    word_count = len(prompt.split())
    creative_score = round(
        min(1.0, (word_count / 150) * 0.5 + (len(scenes) / 10) * 0.3 + 0.2),
        2,
    )

    return {
        "prompt": prompt.strip(),
        "style": style,
        "scenes": scenes,
        "total_duration": total_duration,
        "bg_music_hint": bg_music,
        "creative_score": creative_score,
    }


# ---------------------------------------------------------------------------
# Video Effects
# ---------------------------------------------------------------------------

_VALID_EFFECTS: set[str] = {"blur", "sharpen", "cinematic", "vintage", "vhs", "bw", "glitch"}

_EFFECT_CSS: dict[str, str] = {
    "sharpen":   "contrast(1.4) saturate(1.2)",
    "cinematic": "contrast(1.2) saturate(0.9) sepia(0.1)",
    "vintage":   "sepia(0.4) saturate(0.8) brightness(0.9)",
    "vhs":       "contrast(1.1) saturate(0.7) hue-rotate(5deg)",
    "bw":        "grayscale(1)",
    "glitch":    "hue-rotate(90deg) invert(0.1)",
}


def apply_video_effect(
    scenes: list,
    effect: str,
    intensity: float = 1.0,
) -> dict[str, Any]:
    """Apply a visual effect to a list of scenes."""
    if effect not in _VALID_EFFECTS:
        raise ValueError(f"Invalid effect '{effect}'. Valid effects: {sorted(_VALID_EFFECTS)}")
    if not (0.0 <= intensity <= 2.0):
        raise ValueError("intensity must be between 0.0 and 2.0")

    if effect == "blur":
        filter_css = f"blur({int(intensity * 3)}px)"
    else:
        filter_css = _EFFECT_CSS[effect]

    return {
        "effect": effect,
        "intensity": intensity,
        "scenes_processed": len(scenes),
        "filter_css": filter_css,
        "preview_url": f"https://kalaos.com/preview/effect/{effect}",
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# AI Video Tools
# ---------------------------------------------------------------------------

_VALID_AI_TOOLS: set[str] = {"auto_caption", "stabilize", "color_grade", "slow_mo"}


def apply_ai_video_tool(
    scenes: list,
    tool: str,
    options: dict | None = None,
) -> dict[str, Any]:
    """Apply an AI video tool to a list of scenes."""
    if tool not in _VALID_AI_TOOLS:
        raise ValueError(f"Invalid tool '{tool}'. Valid tools: {sorted(_VALID_AI_TOOLS)}")

    if tool == "auto_caption":
        return {
            "tool": "auto_caption",
            "captions": [
                {
                    "scene": i + 1,
                    "text": f"Scene {i + 1}: {scene.get('text', scene.get('narration', 'Content'))[:50]}",
                    "timestamp": f"00:{i * 3:02d}:00",
                }
                for i, scene in enumerate(scenes)
            ],
            "scenes_processed": len(scenes),
        }

    if tool == "stabilize":
        return {
            "tool": "stabilize",
            "stabilization_strength": options.get("strength", 0.8) if options else 0.8,
            "scenes_processed": len(scenes),
            "smoothing_factor": 0.95,
            "status": "stabilized",
        }

    if tool == "color_grade":
        return {
            "tool": "color_grade",
            "grade_preset": options.get("preset", "cinematic") if options else "cinematic",
            "lut_applied": True,
            "scenes_processed": len(scenes),
            "adjustments": {"shadows": -10, "midtones": 5, "highlights": -5, "saturation": 1.1},
        }

    # slow_mo
    speed = options.get("speed", 0.5) if options else 0.5
    return {
        "tool": "slow_mo",
        "speed_factor": speed,
        "fps_output": 60,
        "scenes_processed": len(scenes),
        "duration_multiplier": 1 / speed,
    }

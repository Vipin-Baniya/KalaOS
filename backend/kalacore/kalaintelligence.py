"""
KalaIntelligence  (Phase 16 – Creative Intelligence Engine)
------------------------------------------------------------
Cross-medium AI transforms connecting all KalaOS studios.

Supported transforms
--------------------
  text   → video   – poem/story → scene-based video script
  text   → song    – prose/lyrics → song structure + beat recipe
  design → video   – design brief → animated video plan
  music  → video   – music mood/bpm → visualizer video config

Public API
----------
transform(input_type, output_type, data, options)
    Returns a dict whose shape depends on the output_type.

ai_assist(context, prompt, studio)
    Universal AI assistant: returns suggestions/actions for any studio.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

# ---------------------------------------------------------------------------
# Supported transform pairs
# ---------------------------------------------------------------------------

VALID_INPUT_TYPES:  set[str] = {"text", "design", "music", "video"}
VALID_OUTPUT_TYPES: set[str] = {"video", "song", "animation"}

_SUPPORTED_PAIRS: set[tuple[str, str]] = {
    ("text",   "video"),
    ("text",   "song"),
    ("design", "animation"),
    ("music",  "video"),
}

# ---------------------------------------------------------------------------
# Vocabulary tables
# ---------------------------------------------------------------------------

_MOOD_PALETTE: dict[str, dict[str, Any]] = {
    "joyful": {
        "colors":  ["#FFD700", "#FF6B6B", "#4ECDC4"],
        "tempo":   "upbeat",
        "chords":  ["I", "IV", "V", "vi"],
        "animation": "zoom-in",
    },
    "melancholic": {
        "colors":  ["#4A90D9", "#5C5C8A", "#2D2D4E"],
        "tempo":   "slow",
        "chords":  ["i", "VI", "III", "VII"],
        "animation": "fade",
    },
    "energetic": {
        "colors":  ["#FF4500", "#FF6B35", "#FFCC02"],
        "tempo":   "fast",
        "chords":  ["I", "V", "vi", "IV"],
        "animation": "slide-left",
    },
    "calm": {
        "colors":  ["#A8DADC", "#457B9D", "#1D3557"],
        "tempo":   "medium",
        "chords":  ["I", "ii", "IV", "V"],
        "animation": "dissolve",
    },
    "mysterious": {
        "colors":  ["#2C0735", "#4B0082", "#6A0DAD"],
        "tempo":   "medium",
        "chords":  ["i", "♭VII", "♭VI", "v"],
        "animation": "zoom-out",
    },
    "dramatic": {
        "colors":  ["#1A1A2E", "#16213E", "#E94560"],
        "tempo":   "variable",
        "chords":  ["i", "♭II", "V", "i"],
        "animation": "slide-right",
    },
}

_MUSIC_VISUALIZER_STYLES: dict[str, dict[str, Any]] = {
    "lofi": {
        "visual_style":   "warm analog",
        "palette":        ["#D4A574", "#8B6F47", "#3D2B1F"],
        "particle_effect": "dust motes",
        "waveform":       "smooth sine",
        "camera_motion":  "slow pan",
        "overlay":        "grain texture",
    },
    "electronic": {
        "visual_style":   "neon geometric",
        "palette":        ["#00FFFF", "#FF00FF", "#0000FF"],
        "particle_effect": "laser grid",
        "waveform":       "sharp peaks",
        "camera_motion":  "fast cut",
        "overlay":        "scanlines",
    },
    "classical": {
        "visual_style":   "elegant minimal",
        "palette":        ["#F5F5DC", "#C8A87E", "#8B7355"],
        "particle_effect": "floating notes",
        "waveform":       "smooth ribbon",
        "camera_motion":  "gentle drift",
        "overlay":        "light bokeh",
    },
    "hiphop": {
        "visual_style":   "urban graffiti",
        "palette":        ["#FF4500", "#FFD700", "#000000"],
        "particle_effect": "spray paint",
        "waveform":       "bass thump",
        "camera_motion":  "bounce cut",
        "overlay":        "street texture",
    },
    "ambient": {
        "visual_style":   "cosmic dreamscape",
        "palette":        ["#0D0221", "#341677", "#7209B7"],
        "particle_effect": "nebula drift",
        "waveform":       "fluid morph",
        "camera_motion":  "slow float",
        "overlay":        "star field",
    },
    "rock": {
        "visual_style":   "gritty cinematic",
        "palette":        ["#1C1C1C", "#8B0000", "#C0C0C0"],
        "particle_effect": "spark bursts",
        "waveform":       "distorted wave",
        "camera_motion":  "shake cut",
        "overlay":        "film scratch",
    },
}

_DEFAULT_VISUALIZER_STYLE = "ambient"

_SONG_STRUCTURE_TEMPLATES: dict[str, list[str]] = {
    "verse-chorus":   ["intro", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro"],
    "aab":            ["verse_a", "verse_a", "verse_b"],
    "through-composed": ["section_1", "section_2", "section_3", "section_4"],
    "loop-based":     ["intro", "loop", "build", "drop", "loop", "outro"],
}

_GENRE_HINTS: list[tuple[list[str], str]] = [
    (["trap", "drill", "rap", "hip", "hop", "beat"],      "hiphop"),
    (["lofi", "lo-fi", "chill", "study"],                  "lofi"),
    (["edm", "electronic", "dance", "techno", "house"],    "electronic"),
    (["ambient", "nature", "atmospheric", "space"],        "ambient"),
    (["rock", "guitar", "metal", "punk", "grunge"],        "rock"),
    (["classical", "orchestra", "piano", "symphony"],      "classical"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _words(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def _detect_mood(text: str) -> str:
    word_set = set(_words(text))
    scores: dict[str, int] = {m: 0 for m in _MOOD_PALETTE}
    _mood_keywords: dict[str, list[str]] = {
        "joyful":     ["happy", "joy", "bright", "fun", "laugh", "smile", "warm", "celebrate"],
        "melancholic": ["sad", "lonely", "rain", "tears", "miss", "gone", "lost", "grey", "cold"],
        "energetic":  ["run", "power", "fire", "fast", "rush", "fight", "win", "strong", "explode"],
        "calm":       ["peace", "quiet", "still", "gentle", "soft", "breath", "rest", "serene"],
        "mysterious": ["dark", "shadow", "secret", "unknown", "hidden", "mystery", "veil", "night"],
        "dramatic":   ["storm", "war", "battle", "sacrifice", "blood", "hero", "fall", "rise"],
    }
    for mood, keywords in _mood_keywords.items():
        for kw in keywords:
            if kw in word_set:
                scores[mood] += 1
    best = max(scores, key=lambda m: scores[m])
    if scores[best] == 0:
        return "calm"
    return best


def _detect_genre(text: str) -> str:
    ws = _words(text)
    for keywords, genre in _GENRE_HINTS:
        if any(w in ws for w in keywords):
            return genre
    return _DEFAULT_VISUALIZER_STYLE


def _stable_int(text: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


# ---------------------------------------------------------------------------
# Transform: text → video
# ---------------------------------------------------------------------------

def _text_to_video(data: str, options: dict) -> dict:
    """Convert text (poem/story/prompt) into a scene-based video script."""
    from kalacore.kalavideo import generate_video_script  # avoid circular import
    style   = options.get("style", "cinematic")
    n_scene = int(options.get("scene_count", 5))
    if style not in {"cinematic", "motivational", "documentary", "cartoon",
                     "lofi", "corporate", "abstract"}:
        style = "cinematic"
    n_scene = max(1, min(20, n_scene))
    mood    = _detect_mood(data)
    palette = _MOOD_PALETTE.get(mood, _MOOD_PALETTE["calm"])
    script  = generate_video_script(prompt=data, style=style, scene_count=n_scene)
    script["mood"]           = mood
    script["color_palette"]  = palette["colors"]
    script["suggested_animation"] = palette["animation"]
    return script


# ---------------------------------------------------------------------------
# Transform: text → song
# ---------------------------------------------------------------------------

def _text_to_song(data: str, options: dict) -> dict:
    """Convert text (lyrics/prompt) into a song structure + beat recipe."""
    from kalacore.kalaproducer import generate_ai_beat  # avoid circular import
    genre_hint = options.get("genre", "")
    mood       = _detect_mood(data)
    palette    = _MOOD_PALETTE.get(mood, _MOOD_PALETTE["calm"])

    # Derive a beat
    beat_prompt = f"{mood} {genre_hint} {data[:80]}"
    beat        = generate_ai_beat(beat_prompt)

    # Pick structure
    structure_key = "verse-chorus"
    ws = _words(data)
    if any(w in ws for w in ["loop", "repeat", "mantra", "chant"]):
        structure_key = "loop-based"
    elif len(ws) < 30:
        structure_key = "aab"
    structure = _SONG_STRUCTURE_TEMPLATES[structure_key]

    # Lyric segmentation: split data into sections
    lines = [ln.strip() for ln in data.splitlines() if ln.strip()]
    sections = []
    for i, section_name in enumerate(structure):
        lyric = lines[i % len(lines)] if lines else f"[{section_name}]"
        sections.append({
            "section": section_name,
            "lyric":   lyric,
            "bars":    4,
        })

    return {
        "input_type":  "text",
        "output_type": "song",
        "mood":        mood,
        "genre":       beat["genre"],
        "bpm":         beat["bpm"],
        "key":         options.get("key", "C"),
        "chords":      palette["chords"],
        "structure":   structure,
        "sections":    sections,
        "drums":       beat["drums"],
        "melody":      beat["melody"],
        "tempo":       palette["tempo"],
    }


# ---------------------------------------------------------------------------
# Transform: design → animation
# ---------------------------------------------------------------------------

def _design_to_animation(data: str, options: dict) -> dict:
    """Convert a design brief / canvas JSON description into an animation plan."""
    from kalacore.kalaanimation import generate_animation_plan  # avoid circular import
    plan = generate_animation_plan(data)
    mood    = _detect_mood(data)
    palette = _MOOD_PALETTE.get(mood, _MOOD_PALETTE["calm"])
    return {
        "input_type":  "design",
        "output_type": "animation",
        "mood":        mood,
        "color_palette": palette["colors"],
        "animation":   plan,
        "suggested_transitions": [palette["animation"]],
        "duration_seconds": int(options.get("duration", 10)),
    }


# ---------------------------------------------------------------------------
# Transform: music → video (visualizer)
# ---------------------------------------------------------------------------

def _music_to_video(data: str, options: dict) -> dict:
    """Convert music description / beat data into a visualizer video config."""
    genre = _detect_genre(data)
    style = _MUSIC_VISUALIZER_STYLES.get(genre, _MUSIC_VISUALIZER_STYLES[_DEFAULT_VISUALIZER_STYLE])
    mood  = _detect_mood(data)

    bpm_hint = 120
    bpm_match = re.search(r"\b(\d{2,3})\s*bpm\b", data, re.IGNORECASE)
    if bpm_match:
        bpm_hint = int(bpm_match.group(1))
    else:
        bpm_hint = _stable_int(data[:32], 70, 160)

    beat_sync_interval = round(60.0 / bpm_hint, 3)

    n_scenes  = int(options.get("scene_count", 4))
    n_scenes  = max(1, min(20, n_scenes))
    scenes = []
    transitions = ["fade", "dissolve", "zoom-in", "slide-left", "zoom-out"]
    for i in range(n_scenes):
        scenes.append({
            "index":       i + 1,
            "visual_style": style["visual_style"],
            "palette":     style["palette"],
            "waveform":    style["waveform"],
            "particle_effect": style["particle_effect"],
            "camera_motion":   style["camera_motion"],
            "overlay":         style["overlay"],
            "transition":  transitions[i % len(transitions)],
            "duration":    int(options.get("scene_duration", 8)),
        })

    return {
        "input_type":        "music",
        "output_type":       "video",
        "genre":             genre,
        "mood":              mood,
        "bpm":               bpm_hint,
        "beat_sync_interval": beat_sync_interval,
        "visual_style":      style["visual_style"],
        "color_palette":     style["palette"],
        "scenes":            scenes,
        "camera_motion":     style["camera_motion"],
    }


# ---------------------------------------------------------------------------
# Public: transform
# ---------------------------------------------------------------------------

def transform(
    input_type:  str,
    output_type: str,
    data:        str,
    options:     dict | None = None,
) -> dict:
    """
    Route a creative transform request.

    Parameters
    ----------
    input_type  : one of VALID_INPUT_TYPES
    output_type : one of VALID_OUTPUT_TYPES
    data        : source content (text, description, etc.)
    options     : optional hints (style, genre, scene_count, …)

    Returns
    -------
    A dict whose shape depends on the (input_type, output_type) pair.

    Raises
    ------
    ValueError  for invalid/unsupported type combinations or empty data.
    """
    if not input_type or input_type not in VALID_INPUT_TYPES:
        raise ValueError(
            f"Invalid input_type '{input_type}'. Valid: {sorted(VALID_INPUT_TYPES)}"
        )
    if not output_type or output_type not in VALID_OUTPUT_TYPES:
        raise ValueError(
            f"Invalid output_type '{output_type}'. Valid: {sorted(VALID_OUTPUT_TYPES)}"
        )
    pair = (input_type, output_type)
    if pair not in _SUPPORTED_PAIRS:
        raise ValueError(
            f"Transform '{input_type}→{output_type}' is not supported. "
            f"Supported pairs: {sorted(_SUPPORTED_PAIRS)}"
        )
    if not data or not data.strip():
        raise ValueError("data must not be empty.")
    opts = options or {}
    if pair == ("text", "video"):
        return _text_to_video(data.strip(), opts)
    if pair == ("text", "song"):
        return _text_to_song(data.strip(), opts)
    if pair == ("design", "animation"):
        return _design_to_animation(data.strip(), opts)
    if pair == ("music", "video"):
        return _music_to_video(data.strip(), opts)
    raise ValueError(f"Unsupported pair: {pair}")  # safety net


# ---------------------------------------------------------------------------
# Universal AI Assistant
# ---------------------------------------------------------------------------

_STUDIO_SUGGESTIONS: dict[str, list[str]] = {
    "text": [
        "Add metaphors to make this more vivid",
        "Restructure into verse-chorus format",
        "Convert this to a script format",
        "Make the tone more emotional",
        "Shorten to key phrases for a reel",
        "Expand this into a full story arc",
    ],
    "visual": [
        "Add a cinematic color grade",
        "Apply golden ratio composition",
        "Generate a complementary color palette",
        "Animate these elements",
        "Add depth with layered effects",
        "Export as animated GIF",
    ],
    "music": [
        "Convert to lofi track",
        "Add cinematic feel with strings",
        "Make this more emotional",
        "Turn into a reel-ready 30s cut",
        "Add drum variation in the bridge",
        "Master for streaming platforms",
    ],
    "animation": [
        "Add smooth transitions between scenes",
        "Sync animations to a beat",
        "Convert storyboard to timeline",
        "Apply cinematic camera movements",
        "Export as video loop",
        "Add particle effects",
    ],
    "video": [
        "Turn this into a reel",
        "Add cinematic color grading",
        "Generate voiceover script",
        "Add background music suggestion",
        "Export scene list as JSON",
        "Create a short teaser version",
    ],
    "general": [
        "Transform to another medium",
        "Add cinematic feel",
        "Make this more emotional",
        "Create a social media version",
        "Add AI-generated visuals",
        "Collaborate with a team member",
    ],
}

_ACTION_KEYWORDS: dict[str, str] = {
    "reel":       "Convert current content into a 30-second reel format",
    "emotional":  "Enhance emotional depth with dynamic pacing and tone",
    "cinematic":  "Apply cinematic color grading and camera movement style",
    "lofi":       "Transform to lofi aesthetic with warm tones and slow tempo",
    "animate":    "Generate animation plan from current content",
    "video":      "Convert to video with scenes, visuals, and audio",
    "song":       "Transform text into a structured song with chords and beat",
    "share":      "Publish to the KalaOS feed for community engagement",
    "export":     "Export project in the best format for distribution",
    "collab":     "Open this project for collaboration",
    "remix":      "Create a new version that remixes this project",
    "visualize":  "Create a music visualizer for this track",
}


def ai_assist(context: str, prompt: str, studio: str = "general") -> dict:
    """
    Universal AI assistant: context-aware suggestions for any studio.

    Parameters
    ----------
    context : current studio content / selection
    prompt  : user's natural-language request
    studio  : active studio ("text", "visual", "music", "animation", "video", "general")

    Returns
    -------
    dict with:
        "action"       – matched action name (or "suggest")
        "response"     – text response / instruction
        "suggestions"  – list of contextual next-step suggestions
        "transform"    – optional transform hint dict if cross-medium action detected
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt must not be empty.")

    studio = studio.lower().strip()
    if studio not in _STUDIO_SUGGESTIONS:
        studio = "general"

    prompt_lower = prompt.lower()
    matched_action = "suggest"
    matched_response = ""
    for keyword, action_desc in _ACTION_KEYWORDS.items():
        if keyword in prompt_lower:
            matched_action  = keyword
            matched_response = action_desc
            break

    if not matched_response:
        mood = _detect_mood(prompt + " " + context[:100])
        matched_response = (
            f"Based on the {studio} context and your request, here are tailored suggestions "
            f"to enhance your work with a {mood} mood."
        )

    suggestions = _STUDIO_SUGGESTIONS.get(studio, _STUDIO_SUGGESTIONS["general"])[:4]

    # Cross-medium transform hint
    transform_hint: dict | None = None
    if any(w in prompt_lower for w in ["video", "reel", "film"]):
        transform_hint = {"input_type": studio, "output_type": "video"}
    elif any(w in prompt_lower for w in ["song", "music", "beat", "lofi"]):
        transform_hint = {"input_type": studio, "output_type": "song"}
    elif any(w in prompt_lower for w in ["animate", "animation", "motion"]):
        transform_hint = {"input_type": studio, "output_type": "animation"}

    result: dict = {
        "action":      matched_action,
        "response":    matched_response,
        "suggestions": suggestions,
    }
    if transform_hint:
        result["transform"] = transform_hint
    return result

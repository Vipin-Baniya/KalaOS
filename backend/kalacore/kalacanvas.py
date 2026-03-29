"""
KalaCanvas  (Phase 14 – Visual Studio: Canvas + AI Image Generator)
--------------------------------------------------------------------
Analyses a text prompt to synthesise a structured image descriptor
and an SVG-encoded preview.  No external API is called; the engine
uses compositional heuristics to translate human language into colour
palettes, mood metadata and a vector placeholder ready for the
Fabric.js canvas.

Philosophy
----------
  • Generated images are described, not scraped — artist intent is preserved
  • Colour is derived from semantic mood, not random assignment
  • Previews are deterministic — same prompt yields the same result
  • No user data is retained after the response

Public API
----------
generate_canvas_image(prompt, style, width, height) → dict
"""

from __future__ import annotations

import base64
import hashlib
import re
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STYLES: frozenset[str] = frozenset({
    "cinematic",
    "abstract",
    "illustration",
    "photorealistic",
    "painting",
    "sketch",
    "anime",
    "watercolor",
})

_DEFAULT_STYLE = "cinematic"
_MIN_DIM = 100
_MAX_DIM = 4096
_DEFAULT_WIDTH = 800
_DEFAULT_HEIGHT = 500

# Mood → colour palette mapping (primary → accent)
_MOOD_PALETTES: dict[str, list[str]] = {
    "sunset":       ["#FF6B35", "#F7C59F", "#B8336A", "#726DA8"],
    "night":        ["#0A0B2E", "#1A1B4B", "#7C5AF1", "#C5CAE9"],
    "ocean":        ["#006994", "#0099CC", "#4FC3F7", "#B2EBF2"],
    "forest":       ["#1B4332", "#2D6A4F", "#52B788", "#D8F3DC"],
    "fire":         ["#E63946", "#F4A261", "#E76F51", "#FFF1E6"],
    "snow":         ["#E8F4FD", "#BDD7EE", "#9EC5E8", "#FFFFFF"],
    "desert":       ["#C9A96E", "#E2B97B", "#F0D5A0", "#8B6914"],
    "cyberpunk":    ["#FF00FF", "#00FFFF", "#1A0033", "#FFB300"],
    "futuristic":   ["#00BCD4", "#7C5AF1", "#1A1B4B", "#80CBC4"],
    "space":        ["#0A0B2E", "#1A237E", "#7C5AF1", "#E8EAF6"],
    "city":         ["#2C3E50", "#8E44AD", "#3498DB", "#ECF0F1"],
    "vintage":      ["#D4A96A", "#A67C52", "#8B5E3C", "#F5DEB3"],
    "nature":       ["#388E3C", "#66BB6A", "#A5D6A7", "#E8F5E9"],
    "pastel":       ["#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9"],
    "dark":         ["#121212", "#1E1E1E", "#424242", "#757575"],
    "bright":       ["#FFEB3B", "#FF5722", "#E91E63", "#9C27B0"],
    "neon":         ["#39FF14", "#FF073A", "#0A0A0A", "#00F3FF"],
    "gold":         ["#FFD700", "#FFC107", "#FF8F00", "#3E2723"],
    "rainbow":      ["#FF0000", "#FF7700", "#00CC00", "#0000FF"],
    "monochrome":   ["#000000", "#444444", "#888888", "#CCCCCC"],
    "warmth":       ["#FF7043", "#FFAB40", "#FDD835", "#FFCCBC"],
    "cool":         ["#1565C0", "#42A5F5", "#80DEEA", "#E3F2FD"],
}

_DEFAULT_PALETTE = ["#7C5AF1", "#5EEAD4", "#F59E0B", "#EF4444"]

# Subject keywords → descriptive subject labels
_SUBJECT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(city|urban|street|building|skyline|metropol)\b", re.I), "urban landscape"),
    (re.compile(r"\b(forest|jungle|tree|woods|nature|garden)\b", re.I), "natural scene"),
    (re.compile(r"\b(ocean|sea|beach|wave|coast|shore|island)\b", re.I), "seascape"),
    (re.compile(r"\b(mountain|hill|cliff|peak|valley)\b", re.I), "mountain vista"),
    (re.compile(r"\b(space|galaxy|nebula|planet|star|cosmos|universe)\b", re.I), "cosmic scene"),
    (re.compile(r"\b(portrait|face|person|figure|character|human)\b", re.I), "character portrait"),
    (re.compile(r"\b(animal|creature|dragon|wolf|cat|dog|bird)\b", re.I), "creature illustration"),
    (re.compile(r"\b(abstract|geometric|pattern|fractal|minimal)\b", re.I), "abstract composition"),
    (re.compile(r"\b(castle|palace|ruin|temple|arch|tower)\b", re.I), "architectural scene"),
    (re.compile(r"\b(flower|bloom|petal|botanical|garden|plant)\b", re.I), "botanical study"),
    (re.compile(r"\b(robot|android|cyborg|machine|mech)\b", re.I), "mechanical figure"),
    (re.compile(r"\b(fantasy|magic|wizard|elf|fairy|myth)\b", re.I), "fantasy scene"),
]

# Composition keywords
_COMPOSITION_HINTS: dict[str, str] = {
    "close":    "tight close-up framing",
    "wide":     "expansive wide-angle composition",
    "aerial":   "bird's-eye perspective",
    "low":      "dramatic low-angle shot",
    "symmetr":  "symmetrical balanced composition",
    "asymmetr": "dynamic asymmetric arrangement",
    "rule":     "rule-of-thirds layout",
    "center":   "centred subject composition",
    "negative": "negative space emphasis",
    "layered":  "multi-plane layered depth",
    "panoram":  "panoramic wide-format layout",
    "portrait": "vertical portrait orientation",
}

# Style-specific lighting descriptors
_STYLE_LIGHTING: dict[str, str] = {
    "cinematic":      "dramatic three-point cinematic lighting",
    "abstract":       "self-illuminated form-based light",
    "illustration":   "flat even illustration lighting",
    "photorealistic": "natural ambient light with shadows",
    "painting":       "painterly chiaroscuro lighting",
    "sketch":         "light implied by cross-hatching",
    "anime":          "cel-shaded rim lighting",
    "watercolor":     "soft diffused watercolor wash lighting",
}

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _hash_seed(text: str) -> int:
    """Deterministic integer seed derived from *text*."""
    return int(hashlib.sha256(text.encode()).hexdigest(), 16)


def _extract_subject(prompt: str) -> str:
    """Return a short subject label inferred from *prompt*."""
    for pattern, label in _SUBJECT_PATTERNS:
        if pattern.search(prompt):
            return label
    # Fallback: first three significant words
    words = [w for w in re.split(r"\W+", prompt) if len(w) > 3][:3]
    return " ".join(words) if words else "imaginative scene"


def _detect_mood(prompt: str) -> str:
    """Return the dominant mood keyword found in *prompt*."""
    lower = prompt.lower()
    for mood in _MOOD_PALETTES:
        if re.search(r"\b" + re.escape(mood) + r"\b", lower):
            return mood
    # Secondary associations
    _SECONDARY: dict[str, str] = {
        "night": "dark",
        "neon": "cyberpunk",
        "warm": "warmth",
        "cold": "cool",
        "winter": "snow",
        "summer": "bright",
        "golden": "gold",
        "black": "dark",
        "white": "monochrome",
    }
    for keyword, mood in _SECONDARY.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", lower):
            return mood
    return "space"  # appealing default


def _detect_palette(prompt: str, style: str) -> list[str]:
    """Return a 4-colour palette matching the mood of *prompt*."""
    mood = _detect_mood(prompt)
    base = list(_MOOD_PALETTES.get(mood, _DEFAULT_PALETTE))

    # Watercolor / pastel styles shift toward lighter tones
    if style in ("watercolor", "anime"):
        base = list(_MOOD_PALETTES.get("pastel", base))

    # Sketch uses near-grayscale
    if style == "sketch":
        base = ["#FAFAFA", "#D0D0D0", "#888888", "#333333"]

    return base


def _detect_composition(prompt: str) -> str:
    """Return a composition descriptor from *prompt* keywords."""
    lower = prompt.lower()
    for keyword, hint in _COMPOSITION_HINTS.items():
        if keyword in lower:
            return hint
    return "balanced compositional arrangement"


def _build_style_tags(prompt: str, style: str) -> list[str]:
    """Build a list of style / technique tags for *prompt*."""
    tags: list[str] = [style]
    lower = prompt.lower()

    # Technique tags
    if any(w in lower for w in ("detailed", "intricate", "fine")):
        tags.append("high detail")
    if any(w in lower for w in ("cinematic", "film", "movie")):
        tags.append("cinematic composition")
    if any(w in lower for w in ("dark", "shadow", "noir", "moody")):
        tags.append("dark mood")
    if any(w in lower for w in ("vibrant", "bright", "colourful", "colorful", "vivid")):
        tags.append("vibrant colour")
    if any(w in lower for w in ("minimal", "clean", "simple", "sparse")):
        tags.append("minimalist")
    if any(w in lower for w in ("glowing", "neon", "luminous", "glow")):
        tags.append("luminous lighting")
    if any(w in lower for w in ("bokeh", "blur", "depth")):
        tags.append("depth of field")
    if any(w in lower for w in ("textured", "rough", "grainy")):
        tags.append("rich texture")
    if any(w in lower for w in ("futuristic", "sci-fi", "scifi", "cyber")):
        tags.append("futuristic")
    if any(w in lower for w in ("vintage", "retro", "old", "antique")):
        tags.append("vintage aesthetic")

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def _escape_svg(text: str) -> str:
    """Escape characters that are unsafe inside SVG text nodes."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def _build_svg_preview(
    subject: str,
    palette: list[str],
    style: str,
    width: int,
    height: int,
    seed: int,
) -> str:
    """
    Return a deterministic SVG string representing the generated image.

    The SVG uses a linear gradient background, optional decorative geometry
    (derived from *seed* + *style*), and an overlay label.
    """
    c1, c2, c3, c4 = (palette + palette)[:4]
    w, h = width, height
    half_w, half_h = w // 2, h // 2
    label = _escape_svg(subject[:50])

    # Derive geometric decorations deterministically from seed
    r1 = (seed % 200) + 80
    r2 = ((seed >> 4) % 150) + 60
    cx1 = (seed % w) if w else half_w
    cy1 = ((seed >> 3) % h) if h else half_h
    cx2 = ((seed >> 6) % w) if w else half_w // 2
    cy2 = ((seed >> 9) % h) if h else half_h // 2
    opacity1 = 0.15 + (seed % 20) / 100
    opacity2 = 0.10 + ((seed >> 2) % 15) / 100
    font_size = max(14, min(28, w // 28))
    sub_size = max(10, min(16, w // 50))

    # Extra geometric element per style
    deco = ""
    if style == "abstract":
        # Rotated rectangle
        angle = seed % 60
        deco = (
            f'<rect x="{half_w - 60}" y="{half_h - 60}" width="120" height="120" '
            f'fill="none" stroke="{c3}" stroke-width="3" opacity="0.35" '
            f'transform="rotate({angle},{half_w},{half_h})"/>'
        )
    elif style in ("cinematic", "photorealistic"):
        # Rule-of-thirds lines
        tw = w // 3
        th = h // 3
        deco = (
            f'<line x1="{tw}" y1="0" x2="{tw}" y2="{h}" stroke="{c4}" '
            f'stroke-width="1" opacity="0.2"/>'
            f'<line x1="{2*tw}" y1="0" x2="{2*tw}" y2="{h}" stroke="{c4}" '
            f'stroke-width="1" opacity="0.2"/>'
            f'<line x1="0" y1="{th}" x2="{w}" y2="{th}" stroke="{c4}" '
            f'stroke-width="1" opacity="0.2"/>'
            f'<line x1="0" y1="{2*th}" x2="{w}" y2="{2*th}" stroke="{c4}" '
            f'stroke-width="1" opacity="0.2"/>'
        )
    elif style == "sketch":
        # Cross-hatch lines
        step = max(12, w // 30)
        lines = ""
        for i in range(0, w + h, step):
            lines += (
                f'<line x1="{i}" y1="0" x2="0" y2="{i}" '
                f'stroke="{c3}" stroke-width="0.5" opacity="0.25"/>'
            )
        deco = lines

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <linearGradient id="overlay" x1="0%" y1="60%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="rgba(0,0,0,0)"/>
      <stop offset="100%" stop-color="rgba(0,0,0,0.55)"/>
    </linearGradient>
  </defs>
  <rect width="{w}" height="{h}" fill="url(#bg)"/>
  <circle cx="{cx1}" cy="{cy1}" r="{r1}" fill="{c3}" opacity="{opacity1:.2f}"/>
  <circle cx="{cx2}" cy="{cy2}" r="{r2}" fill="{c4}" opacity="{opacity2:.2f}"/>
  {deco}
  <rect width="{w}" height="{h}" fill="url(#overlay)"/>
  <text x="{half_w}" y="{h - sub_size * 3}" text-anchor="middle"
        font-family="Inter, sans-serif" font-size="{font_size}"
        fill="rgba(255,255,255,0.92)" font-weight="600">{label}</text>
  <text x="{half_w}" y="{h - sub_size}" text-anchor="middle"
        font-family="Inter, sans-serif" font-size="{sub_size}"
        fill="rgba(255,255,255,0.55)">✦ KalaOS AI · {_escape_svg(style)}</text>
</svg>"""
    return svg


def _svg_to_data_url(svg: str) -> str:
    """Base64-encode *svg* and return a data URI."""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_canvas_image(
    prompt: str,
    style: str = _DEFAULT_STYLE,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
) -> dict[str, Any]:
    """
    Generate a structured image descriptor and SVG preview from *prompt*.

    Parameters
    ----------
    prompt : str
        Natural-language description of the desired image.
    style : str
        Visual style — one of ``VALID_STYLES``.  Defaults to ``"cinematic"``.
    width : int
        Desired canvas width in pixels (100–4096).
    height : int
        Desired canvas height in pixels (100–4096).

    Returns
    -------
    dict with keys:
        ``prompt``          – cleaned prompt string
        ``refined_prompt``  – enhanced prompt with style and mood notes
        ``style``           – requested style
        ``subject``         – inferred subject label
        ``mood``            – dominant mood keyword
        ``color_palette``   – list of 4 hex colours
        ``composition``     – composition descriptor
        ``style_tags``      – list of style / technique tags
        ``lighting``        – lighting descriptor
        ``width``           – actual width used
        ``height``          – actual height used
        ``preview_url``     – base64 SVG data URI ready for canvas
        ``suggested_filename`` – a safe filename based on the prompt

    Raises
    ------
    ValueError
        If *prompt* is empty or blank, *style* is not in ``VALID_STYLES``,
        or *width*/*height* are outside the allowed range.
    """
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("prompt must not be empty")

    style = style.strip().lower()
    if style not in VALID_STYLES:
        raise ValueError(
            f"style must be one of {sorted(VALID_STYLES)}"
        )

    if not (_MIN_DIM <= width <= _MAX_DIM):
        raise ValueError(
            f"width must be between {_MIN_DIM} and {_MAX_DIM}"
        )
    if not (_MIN_DIM <= height <= _MAX_DIM):
        raise ValueError(
            f"height must be between {_MIN_DIM} and {_MAX_DIM}"
        )

    # Derive attributes
    subject = _extract_subject(prompt)
    mood = _detect_mood(prompt)
    palette = _detect_palette(prompt, style)
    composition = _detect_composition(prompt)
    tags = _build_style_tags(prompt, style)
    lighting = _STYLE_LIGHTING.get(style, "natural lighting")

    # Enhanced prompt with style hints
    refined_prompt = (
        f"{prompt}. Style: {style}. "
        f"Mood: {mood}. Composition: {composition}. "
        f"Lighting: {lighting}."
    )

    # Suggested filename (alphanumeric only)
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower())[:40].strip("-")
    suggested_filename = f"kala-{slug}.png"

    # Deterministic seed for visual variety per prompt
    seed = _hash_seed(prompt + style)

    # Build SVG preview
    svg = _build_svg_preview(subject, palette, style, width, height, seed)
    preview_url = _svg_to_data_url(svg)

    return {
        "prompt": prompt,
        "refined_prompt": refined_prompt,
        "style": style,
        "subject": subject,
        "mood": mood,
        "color_palette": palette,
        "composition": composition,
        "style_tags": tags,
        "lighting": lighting,
        "width": width,
        "height": height,
        "preview_url": preview_url,
        "suggested_filename": suggested_filename,
    }

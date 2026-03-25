"""
KalaVisual  (Phase 11 – Visual Art Intelligence)
-------------------------------------------------
Analyses visual art through a description-based pipeline.

Provides compositional, colour-theory, stylistic and narrative insights
for paintings, sketches, photographs, video works and logos — without
requiring any image data to be uploaded or retained.  The pipeline
operates on artist-provided descriptions, preserving artist privacy.

Philosophy
----------
  • Visual art communicates what words cannot — we describe, never diminish
  • Colour and composition are culturally situated — context qualifies analysis
  • No style is superior; all visual traditions receive equal dignity
  • Analysis is private by default and never used for ranking

Public API
----------
analyze_visual(description, medium, color_palette, dimensions, style_tags) → dict
"""

import colorsys
import math
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_MEDIA = {"painting", "sketch", "photo", "video", "logo"}

# Style / movement keywords mapped to movement name
_STYLE_KEYWORDS: Dict[str, List[str]] = {
    "realism": [
        "realistic", "lifelike", "photorealistic", "detailed", "accurate",
        "representational", "figurative", "naturalistic",
    ],
    "abstract": [
        "abstract", "non-representational", "geometric", "non-objective",
        "colour field", "color field", "shapes", "forms",
    ],
    "expressionism": [
        "emotional", "expressive", "gestural", "distorted", "raw",
        "intense", "visceral", "painterly", "energetic brushwork",
    ],
    "impressionism": [
        "loose", "atmospheric", "light", "impressionistic", "dappled",
        "fleeting", "broken brushwork", "plein air",
    ],
    "minimalism": [
        "minimal", "minimal", "simple", "clean", "negative space",
        "sparse", "uncluttered", "stripped back",
    ],
    "surrealism": [
        "dream", "surreal", "bizarre", "dreamlike", "fantastical",
        "subconscious", "juxtaposition", "uncanny",
    ],
    "pop art": [
        "bold", "graphic", "commercial", "flat colour", "flat color",
        "pop", "vibrant", "high contrast",
    ],
    "street art": [
        "graffiti", "mural", "street", "spray", "urban", "stencil",
        "paste-up", "wheat paste",
    ],
    "illustration": [
        "illustrated", "illustration", "cartoon", "comic", "manga",
        "anime", "character", "stylised", "stylized",
    ],
    "photography": [
        "photograph", "camera", "lens", "exposure", "depth of field",
        "bokeh", "portrait", "landscape", "macro", "long exposure",
    ],
    "digital art": [
        "digital", "cgi", "3d render", "pixel", "pixel art",
        "digital painting", "digital illustration", "vector",
    ],
}

# Compositional element keywords
_COMPOSITION_KEYWORDS = {
    "rule_of_thirds": ["off-center", "third", "asymmetric", "corner", "side", "edge"],
    "centred": ["centered", "centred", "symmetrical", "symmetry", "balanced", "centred subject"],
    "radial": ["radial", "circular", "converging", "spiral", "radiating"],
    "diagonal": ["diagonal", "dynamic", "slanted", "angled", "tilted"],
    "leading_lines": ["leading lines", "path", "road", "river", "corridor", "vanishing point"],
    "layered_depth": ["foreground", "background", "midground", "layers", "depth", "perspective"],
    "negative_space": ["negative space", "empty", "breathing room", "open space", "void"],
    "texture": ["texture", "rough", "smooth", "granular", "layered", "impasto", "brushwork"],
    "pattern": ["pattern", "repetition", "rhythm", "motif", "grid", "tessellation"],
}

# Emotional register keywords
_EMOTIONAL_KEYWORDS = {
    "joyful": ["joyful", "happy", "celebratory", "playful", "vibrant", "bright", "uplifting"],
    "melancholic": ["melancholic", "sad", "lonely", "somber", "muted", "fog", "grey", "gray"],
    "tense": ["tense", "anxious", "unsettling", "disturbing", "dark", "ominous", "threatening"],
    "peaceful": ["peaceful", "calm", "serene", "tranquil", "quiet", "still", "meditative"],
    "dramatic": ["dramatic", "intense", "powerful", "striking", "bold", "cinematic"],
    "nostalgic": ["nostalgic", "vintage", "retro", "aged", "faded", "historical", "memory"],
    "mysterious": ["mysterious", "enigmatic", "hidden", "obscured", "fog", "shadow", "dark"],
}

# Intent keywords
_INTENT_KEYWORDS = {
    "expressive": [
        "personal", "self-portrait", "inner", "emotional", "feeling",
        "cathartic", "autobiographical",
    ],
    "documentary": [
        "documentary", "record", "capture", "moment", "event", "protest",
        "social", "political", "news",
    ],
    "decorative": [
        "decorative", "ornamental", "aesthetic", "design", "pattern",
        "wallpaper", "interior", "commercial",
    ],
    "conceptual": [
        "concept", "idea", "message", "statement", "commentary",
        "metaphor", "symbol", "allegory",
    ],
    "spiritual": [
        "spiritual", "devotional", "sacred", "religious", "meditative",
        "transcendent", "divine", "ritual",
    ],
    "environmental": [
        "nature", "landscape", "environment", "ecological", "outdoor",
        "wildlife", "botanical", "natural",
    ],
}


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _parse_hex(hex_str: str) -> Optional[Tuple[float, float, float]]:
    """Parse a hex colour string to (r, g, b) each in [0, 1].  Returns None on failure."""
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return None
    try:
        r = int(s[0:2], 16) / 255
        g = int(s[2:4], 16) / 255
        b = int(s[4:6], 16) / 255
        return r, g, b
    except ValueError:
        return None


def _rgb_to_hsv(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """Convert (r,g,b) each 0-1 to (h°, s%, v%)."""
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s * 100, v * 100


def _colour_temperature(h: float) -> str:
    """Classify a hue angle as warm / cool / neutral."""
    # Warm: red (0-30), orange (30-60), yellow (60-75)
    # Cool: green (75-180), cyan (180-210), blue (210-270), purple (270-330)
    # Neutral: magenta bordering warm/cool (330-360)
    if 0 <= h < 30 or 330 <= h <= 360:
        return "warm"
    if 30 <= h < 75:
        return "warm"  # orange-yellow
    if 75 <= h < 210:
        return "cool"
    if 210 <= h < 270:
        return "cool"  # blue
    return "neutral"


def _harmony_type(hues: List[float]) -> str:
    """Classify colour harmony from a list of hue angles (degrees)."""
    if len(hues) < 2:
        return "monochromatic"
    # Sort and find max angular gap
    sorted_h = sorted(hues)
    gaps = [
        abs(sorted_h[i + 1] - sorted_h[i]) for i in range(len(sorted_h) - 1)
    ]
    gaps.append(360 - sorted_h[-1] + sorted_h[0])
    max_gap = max(gaps)
    hue_spread = 360 - max_gap  # angular span of used hues

    if hue_spread < 30:
        return "monochromatic"
    if len(hues) == 2:
        diff = min(abs(sorted_h[1] - sorted_h[0]), 360 - abs(sorted_h[1] - sorted_h[0]))
        if 150 <= diff <= 210:
            return "complementary"
        if diff < 60:
            return "analogous"
        return "split-complementary"
    # 3+ colours
    avg_gap = hue_spread / max(len(hues) - 1, 1)
    if all(abs(g - 120) < 30 for g in gaps[:3]):
        return "triadic"
    if hue_spread < 60:
        return "analogous"
    return "polychromatic"


def analyze_color_palette(color_palette: List[str]) -> Dict[str, Any]:
    """
    Analyse a list of hex colour strings and return colour theory insights.
    Returns an empty dict if the palette is empty or all colours are invalid.
    """
    parsed = [c for c in (_parse_hex(h) for h in (color_palette or [])) if c]
    if not parsed:
        return {"note": "No valid hex colours provided; colour analysis skipped."}

    hsvs = [_rgb_to_hsv(*rgb) for rgb in parsed]
    hues = [h for h, s, v in hsvs if s > 10]  # ignore near-grey colours
    saturations = [s for _, s, _ in hsvs]
    values = [v for _, _, v in hsvs]

    temps = [_colour_temperature(h) for h in hues]
    temp_counts: Dict[str, int] = {}
    for t in temps:
        temp_counts[t] = temp_counts.get(t, 0) + 1
    dominant_temp = max(temp_counts, key=temp_counts.get) if temp_counts else "neutral"

    avg_sat = sum(saturations) / len(saturations)
    avg_val = sum(values) / len(values)

    harmony = _harmony_type(hues) if hues else "achromatic"

    sat_label = "highly saturated" if avg_sat > 65 else ("muted" if avg_sat < 30 else "moderately saturated")
    val_label = "high-key (predominantly light)" if avg_val > 65 else (
        "low-key (predominantly dark)" if avg_val < 35 else "mid-tone"
    )

    return {
        "palette_size": len(parsed),
        "colour_harmony": harmony,
        "dominant_temperature": dominant_temp,
        "temperature_breakdown": temp_counts,
        "saturation": sat_label,
        "average_saturation_pct": round(avg_sat, 1),
        "value_range": val_label,
        "average_value_pct": round(avg_val, 1),
        "hue_count": len(hues),
        "insight": _colour_insight(harmony, dominant_temp, sat_label, val_label),
    }


def _colour_insight(harmony: str, temperature: str, saturation: str, value: str) -> str:
    """Generate a plain-language colour insight."""
    insights = []
    harmony_descriptions = {
        "monochromatic": "creates unity and calm through tonal variation of a single hue",
        "analogous": "builds cohesion through neighbouring hues, evoking natural harmony",
        "complementary": "generates visual tension and energy through opposing hues",
        "split-complementary": "balances contrast with stability using a split pair",
        "triadic": "achieves dynamic balance through three equally-spaced hues",
        "polychromatic": "draws on a rich, varied palette that rewards close looking",
        "achromatic": "strips colour entirely, directing attention to form, value and texture",
    }
    insights.append(harmony_descriptions.get(harmony, "uses a distinctive colour arrangement"))
    if temperature == "warm":
        insights.append("warm tones invite intimacy and energy")
    elif temperature == "cool":
        insights.append("cool tones convey distance, contemplation or serenity")
    if "highly saturated" in saturation:
        insights.append("intense saturation commands attention and vitality")
    elif "muted" in saturation:
        insights.append("reduced saturation lends subtlety and sophistication")
    if "high-key" in value:
        insights.append("bright values create an open, airy mood")
    elif "low-key" in value:
        insights.append("dark values evoke mystery, depth and gravitas")
    return "; ".join(insights).capitalize() + "."


# ---------------------------------------------------------------------------
# Composition analysis
# ---------------------------------------------------------------------------

def analyze_composition(description: str) -> Dict[str, Any]:
    """Detect compositional elements from a text description."""
    desc_lower = description.lower()
    detected: Dict[str, bool] = {}

    for element, keywords in _COMPOSITION_KEYWORDS.items():
        detected[element] = any(kw in desc_lower for kw in keywords)

    active = [k for k, v in detected.items() if v]

    # Balance classification
    if detected.get("centred"):
        balance = "symmetrical — centred composition creates stillness and formal balance"
    elif detected.get("rule_of_thirds"):
        balance = "asymmetric — off-centre placement creates visual tension and interest"
    elif detected.get("diagonal"):
        balance = "dynamic — diagonal lines introduce energy and movement"
    elif detected.get("radial"):
        balance = "radial — converging lines draw the eye to a central focal point"
    elif detected.get("negative_space"):
        balance = "negative-space dominant — emptiness is used as an active visual element"
    else:
        balance = "undetermined from description"

    depth = "multi-layered" if detected.get("layered_depth") else (
        "flat" if not any(
            detected.get(k) for k in ("leading_lines", "layered_depth", "diagonal")
        ) else "shallow"
    )

    return {
        "detected_elements": active,
        "balance": balance,
        "depth": depth,
        "has_leading_lines": detected.get("leading_lines", False),
        "uses_negative_space": detected.get("negative_space", False),
        "has_pattern_rhythm": detected.get("pattern", False),
        "texture_noted": detected.get("texture", False),
        "element_count": len(active),
    }


# ---------------------------------------------------------------------------
# Style classification
# ---------------------------------------------------------------------------

def classify_style(description: str, style_tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Detect artistic style/movement from description and explicit tags."""
    desc_lower = description.lower()
    tag_lower = [t.lower() for t in (style_tags or [])]
    combined = desc_lower + " " + " ".join(tag_lower)

    scores: Dict[str, int] = {}
    for style, keywords in _STYLE_KEYWORDS.items():
        hit = sum(1 for kw in keywords if kw in combined)
        if hit:
            scores[style] = hit

    if not scores:
        primary = "undetermined"
        influences = []
        confidence = "low"
    else:
        sorted_styles = sorted(scores, key=scores.get, reverse=True)  # type: ignore[arg-type]
        primary = sorted_styles[0]
        influences = sorted_styles[1:4]
        top_score = scores[primary]
        confidence = "high" if top_score >= 3 else ("medium" if top_score == 2 else "low")

    return {
        "primary_style": primary,
        "style_influences": influences,
        "detection_confidence": confidence,
        "style_scores": scores,
        "note": (
            "Style classification is based on described characteristics — "
            "the artist's own categorisation always takes precedence."
        ),
    }


# ---------------------------------------------------------------------------
# Emotional register
# ---------------------------------------------------------------------------

def analyze_emotional_register(description: str) -> Dict[str, Any]:
    """Detect emotional register from description keywords."""
    desc_lower = description.lower()
    scores: Dict[str, int] = {}
    for emotion, keywords in _EMOTIONAL_KEYWORDS.items():
        hit = sum(1 for kw in keywords if kw in desc_lower)
        if hit:
            scores[emotion] = hit

    if not scores:
        primary = "neutral / undetermined"
        secondary = []
    else:
        sorted_emo = sorted(scores, key=scores.get, reverse=True)  # type: ignore[arg-type]
        primary = sorted_emo[0]
        secondary = sorted_emo[1:3]

    return {
        "primary_register": primary,
        "secondary_registers": secondary,
        "emotional_complexity": len(scores),
        "note": (
            "Emotional register is inferred from descriptive language; "
            "the artist's intent is the definitive authority."
        ),
    }


# ---------------------------------------------------------------------------
# Artistic intent
# ---------------------------------------------------------------------------

def infer_artistic_intent(description: str, medium: str) -> Dict[str, Any]:
    """Infer artistic intent and purpose from description."""
    desc_lower = description.lower()
    scores: Dict[str, int] = {}
    for intent, keywords in _INTENT_KEYWORDS.items():
        hit = sum(1 for kw in keywords if kw in desc_lower)
        if hit:
            scores[intent] = hit

    # Medium-specific defaults
    medium_defaults = {
        "logo": "decorative",
        "photo": "documentary",
        "video": "documentary",
        "painting": "expressive",
        "sketch": "expressive",
    }
    if not scores:
        primary_intent = medium_defaults.get(medium, "expressive")
    else:
        primary_intent = max(scores, key=scores.get)  # type: ignore[arg-type]

    return {
        "primary_intent": primary_intent,
        "detected_intents": list(scores.keys()),
        "note": (
            "Intent is inferred from language cues. "
            "No intent is more valid than another — all serve artistic purpose."
        ),
    }


# ---------------------------------------------------------------------------
# Medium-specific technical analysis
# ---------------------------------------------------------------------------

def analyze_technical_elements(description: str, medium: str) -> Dict[str, Any]:
    """Provide medium-specific technical observations."""
    desc_lower = description.lower()

    if medium == "painting":
        surface_keywords = {
            "canvas": "canvas",
            "paper": "paper",
            "board": "board or panel",
            "wall": "wall / mural",
            "wood": "wood panel",
        }
        surface = next((v for k, v in surface_keywords.items() if k in desc_lower), "unspecified surface")
        technique_keywords = {
            "oil": "oil paint",
            "acrylic": "acrylic",
            "watercolour": "watercolour",
            "watercolor": "watercolour",
            "gouache": "gouache",
            "tempera": "egg tempera",
            "encaustic": "encaustic (wax)",
            "fresco": "fresco",
        }
        technique = next((v for k, v in technique_keywords.items() if k in desc_lower), "undetermined medium")
        impasto = "heavy impasto" in desc_lower or "thick paint" in desc_lower
        return {
            "surface": surface,
            "paint_medium": technique,
            "impasto_texture": impasto,
            "observations": _painting_observations(technique, impasto),
        }

    if medium == "sketch":
        media_keywords = {
            "pencil": "graphite pencil",
            "charcoal": "charcoal",
            "ink": "pen & ink",
            "pen": "ballpoint / fineliner pen",
            "pastel": "pastel",
            "conte": "conté crayon",
            "marker": "marker",
        }
        sketch_medium = next((v for k, v in media_keywords.items() if k in desc_lower), "undetermined drawing medium")
        cross_hatching = any(kw in desc_lower for kw in ("cross-hatch", "crosshatch", "hatching"))
        shading = "shading" in desc_lower or "tonal" in desc_lower
        return {
            "drawing_medium": sketch_medium,
            "cross_hatching": cross_hatching,
            "tonal_shading": shading,
            "observations": _sketch_observations(sketch_medium, cross_hatching),
        }

    if medium == "photo":
        keywords = {
            "black and white": "monochrome",
            "black & white": "monochrome",
            "long exposure": "long exposure",
            "macro": "macro / close-up",
            "bokeh": "shallow depth of field (bokeh)",
            "hdr": "HDR processing",
            "portrait": "portrait",
            "landscape": "landscape",
            "street": "street photography",
        }
        style = next((v for k, v in keywords.items() if k in desc_lower), "general photography")
        film = "film" in desc_lower or "analog" in desc_lower or "analogue" in desc_lower
        return {
            "photo_genre": style,
            "film_photography": film,
            "observations": _photo_observations(style, film),
        }

    if medium == "video":
        technique_keywords = {
            "stop motion": "stop motion",
            "time-lapse": "time-lapse",
            "timelapse": "time-lapse",
            "slow motion": "slow motion",
            "animation": "animation",
            "documentary": "documentary style",
            "narrative": "narrative / fiction",
            "experimental": "experimental / avant-garde",
        }
        technique = next((v for k, v in technique_keywords.items() if k in desc_lower), "live action")
        return {
            "video_technique": technique,
            "observations": _video_observations(technique),
        }

    if medium == "logo":
        vector = any(kw in desc_lower for kw in ("vector", "svg", "scalable", "clean lines"))
        wordmark = "wordmark" in desc_lower or "text-based" in desc_lower or "lettering" in desc_lower
        icon = "icon" in desc_lower or "symbol" in desc_lower or "mark" in desc_lower
        return {
            "logo_type": "wordmark" if wordmark else ("icon / symbol" if icon else "combination mark"),
            "likely_vector": vector,
            "observations": _logo_observations(wordmark, icon, vector),
        }

    return {"observations": "No medium-specific analysis available for this category."}


def _painting_observations(technique: str, impasto: bool) -> str:
    base = f"A {technique} work"
    if impasto:
        base += " with heavy impasto — the surface itself becomes a textural element."
    else:
        base += " — layering and glazing control depth and luminosity."
    return base


def _sketch_observations(medium: str, cross_hatch: bool) -> str:
    base = f"A {medium} drawing"
    if cross_hatch:
        base += " using cross-hatching — a classical technique for building tonal depth through line."
    else:
        base += " — expressive line quality is the primary carrier of meaning."
    return base


def _photo_observations(genre: str, film: bool) -> str:
    base = f"A {genre} photograph"
    if film:
        base += " on film — grain, tonal curves and the tactile quality of analog capture contribute to the aesthetic."
    return base + "."


def _video_observations(technique: str) -> str:
    return (
        f"A {technique} work — time itself becomes a creative material, "
        "shaping rhythm, pacing and viewer experience."
    )


def _logo_observations(wordmark: bool, icon: bool, vector: bool) -> str:
    parts = []
    if wordmark:
        parts.append("typography-led identity where letterforms carry brand character")
    if icon:
        parts.append("symbol-led identity enabling recognition without text")
    if vector:
        parts.append("vector construction ensures scalability from favicon to billboard")
    if not parts:
        parts.append("combination mark blending type and symbol")
    return "; ".join(parts).capitalize() + "."


# ---------------------------------------------------------------------------
# Preservation recommendations
# ---------------------------------------------------------------------------

def preservation_recommendations(medium: str) -> Dict[str, Any]:
    """Return archival and preservation guidance for the given medium."""
    recs: Dict[str, Any] = {"medium": medium, "digital": [], "physical": [], "distribution": []}

    if medium == "painting":
        recs["physical"] = [
            "Store away from direct sunlight and UV sources",
            "Maintain 45–55% relative humidity to prevent cracking",
            "Keep temperature stable (18–22 °C / 64–72 °F)",
            "Use archival-quality framing materials (acid-free backing and matting)",
            "Photograph under consistent diffuse lighting before varnishing",
        ]
        recs["digital"] = [
            "Scan or photograph at minimum 600 DPI for archival quality",
            "Save master in TIFF or PNG (lossless) before exporting JPEG",
            "Include colour-calibration reference in the master photograph",
        ]
        recs["distribution"] = [
            "sRGB JPEG (≥90% quality) for web",
            "High-res TIFF for print reproduction",
            "Consider ICC profile embedding for accurate colour reproduction",
        ]

    elif medium == "sketch":
        recs["physical"] = [
            "Use acid-free paper and fixative spray to prevent smudging",
            "Store flat in archival sleeves — never rolled",
            "Keep away from humidity; pencil and charcoal are moisture-sensitive",
        ]
        recs["digital"] = [
            "Scan at 600–1200 DPI in greyscale or colour",
            "TIFF for master; PNG for web sharing",
        ]
        recs["distribution"] = [
            "PNG (lossless) preserves fine line detail better than JPEG",
            "PDF vector export if working in a digital tool",
        ]

    elif medium == "photo":
        recs["physical"] = [
            "Store prints in acid-free sleeves or boxes in a cool, dark environment",
            "Avoid handling with bare hands — use cotton gloves",
            "Back up negatives / RAW files immediately to at least two locations",
        ]
        recs["digital"] = [
            "Retain original RAW files alongside edited exports",
            "Use TIFF for master exports; JPEG (≥95%) for distribution",
            "Embed IPTC / XMP metadata (creator, date, description, copyright)",
        ]
        recs["distribution"] = [
            "sRGB JPEG for web and social media",
            "Adobe RGB or ProPhoto RGB for print workflows",
        ]

    elif medium == "video":
        recs["physical"] = [
            "Keep film negatives in acid-free canisters in a climate-controlled space",
            "Digitise film prints within 10 years of creation to prevent deterioration",
        ]
        recs["digital"] = [
            "Archive master in a lossless or near-lossless codec (ProRes 4444, DNxHR HQ)",
            "Store at full resolution; never delete the original export",
            "Back up on at least two separate drives or cloud services",
        ]
        recs["distribution"] = [
            "H.264 / H.265 MP4 for web delivery",
            "ProRes for broadcast or festival submission",
            "Include closed captions for accessibility",
        ]

    elif medium == "logo":
        recs["physical"] = ["Produce a style guide specifying exact colour values (HEX, RGB, CMYK, Pantone)"]
        recs["digital"] = [
            "Always retain the master in SVG or AI (vector) format",
            "Export PNG at multiple resolutions: 16px, 32px, 256px, 512px, 1024px",
            "Export a monochrome (black) and reversed (white) variant",
        ]
        recs["distribution"] = [
            "SVG for web (scales infinitely)",
            "PNG with transparency for digital use",
            "EPS / PDF for print vendors",
        ]

    return recs


# ---------------------------------------------------------------------------
# Subject / narrative extraction
# ---------------------------------------------------------------------------

def extract_visual_narrative(description: str) -> Dict[str, Any]:
    """Extract high-level narrative elements from the description."""
    desc_lower = description.lower()
    word_count = len(description.split())
    sentences = [s.strip() for s in re.split(r"[.!?]", description) if s.strip()]

    # Subject matter hints
    subjects = []
    subject_keywords = {
        "portrait / figure": ["person", "figure", "portrait", "face", "human", "people", "body"],
        "landscape": ["landscape", "mountain", "sky", "field", "forest", "nature", "outdoor"],
        "still life": ["still life", "objects", "bottle", "fruit", "table", "flower"],
        "architecture": ["building", "architecture", "urban", "city", "structure", "room", "interior"],
        "abstract / non-figurative": ["abstract", "colour", "color", "shape", "form", "mark"],
        "animal / wildlife": ["animal", "bird", "creature", "wildlife", "pet", "cat", "dog"],
        "fantasy / mythology": ["dragon", "myth", "legend", "fantasy", "creature", "magic"],
    }
    for subj, kws in subject_keywords.items():
        if any(kw in desc_lower for kw in kws):
            subjects.append(subj)

    # Narrative complexity
    if word_count < 20:
        complexity = "brief sketch — a starting point for deeper reflection"
    elif word_count < 60:
        complexity = "moderate description — key elements are communicated"
    else:
        complexity = "detailed description — rich context for analysis"

    return {
        "detected_subjects": subjects or ["undetermined from description"],
        "description_complexity": complexity,
        "sentence_count": len(sentences),
        "word_count": word_count,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def analyze_visual(
    description: str,
    medium: str = "painting",
    color_palette: Optional[List[str]] = None,
    dimensions: Optional[str] = None,
    style_tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Full visual art analysis pipeline.

    Parameters
    ----------
    description   : Artist-provided text description of the work.
    medium        : One of 'painting', 'sketch', 'photo', 'video', 'logo'.
    color_palette : Optional list of hex colour strings (e.g. ['#ff5733', '#2ecc71']).
    dimensions    : Optional string describing dimensions / aspect ratio.
    style_tags    : Optional list of style tags provided by the artist.

    Returns
    -------
    Comprehensive dict with colour, composition, style, emotion, intent,
    technical, narrative, and preservation sections.
    """
    if not description or not description.strip():
        return {"error": "description must not be empty"}

    med = medium.lower() if medium else "painting"
    if med not in SUPPORTED_MEDIA:
        med = "painting"

    colour_analysis = analyze_color_palette(color_palette or [])
    composition = analyze_composition(description)
    style = classify_style(description, style_tags)
    emotion = analyze_emotional_register(description)
    intent = infer_artistic_intent(description, med)
    technical = analyze_technical_elements(description, med)
    narrative = extract_visual_narrative(description)
    preservation = preservation_recommendations(med)

    # Overall summary
    summary_parts = [
        f"A {med}",
        f"in a {style['primary_style']} style" if style["primary_style"] != "undetermined" else "",
        f"with {colour_analysis.get('colour_harmony', '')} colour harmony" if colour_analysis.get("colour_harmony") else "",
        f"evoking a {emotion['primary_register']} register" if emotion["primary_register"] != "neutral / undetermined" else "",
        f"primarily {intent['primary_intent']} in intent",
    ]
    summary = " ".join(p for p in summary_parts if p).strip().rstrip(",") + "."

    return {
        "medium": med,
        "dimensions": dimensions,
        "summary": summary,
        "colour": colour_analysis,
        "composition": composition,
        "style": style,
        "emotion": emotion,
        "intent": intent,
        "technical": technical,
        "narrative": narrative,
        "preservation": preservation,
    }

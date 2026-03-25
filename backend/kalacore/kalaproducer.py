"""
KalaProducer  (Music Production, Generation, Distribution & Streaming)
-----------------------------------------------------------------------
Artist-first tools for music production planning, generative musical ideas,
distribution channel guidance, and streaming-platform optimisation.

Philosophy
----------
  • Every suggestion is a starting point, not a prescription.
  • The artist's vision is sovereign — tools serve the art.
  • Distribution and streaming metadata serve findability, not ranking.
  • Production notes are craft tools, not algorithmic directives.

Functions
---------
generate_production_plan    – BPM, key, structure, sound-design, mixing hints
generate_beat_pattern       – rhythmic grid and drum-machine notation
suggest_instruments         – instrument palette from emotional arc + genre hints
generate_melody_contour     – melodic shape and scale degree suggestions
suggest_distribution_channels – platform-by-platform release strategy
generate_streaming_metadata – streaming-optimised tags, ISRC, loudness targets
generate_sample_palette     – sample/loop/texture suggestions

Public API
----------
produce(text, pattern_analysis, art_genome_dict) → full producer dict
"""

import math
import hashlib
from typing import Any, Dict, List, Optional

from kalacore.pattern_engine import _words, count_syllables, _normalise


# ---------------------------------------------------------------------------
# Vocabulary tables
# ---------------------------------------------------------------------------

_GENRE_BPM_RANGES: Dict[str, tuple] = {
    "hip-hop":       (75,  100),
    "trap":          (130, 160),
    "r&b":           (65,  95),
    "pop":           (90,  130),
    "rock":          (100, 160),
    "folk":          (60,  100),
    "jazz":          (80,  180),
    "ambient":       (50,  80),
    "dance/edm":     (120, 140),
    "afrobeats":     (95,  115),
    "reggaeton":     (90,  100),
    "classical":     (40,  180),
    "spoken word":   (60,  80),
    "experimental":  (40,  200),
}

_EMOTIONAL_INSTRUMENTS: Dict[str, List[str]] = {
    "ascending": [
        "piano (upper register)", "acoustic guitar", "strings (rising phrase)",
        "flute", "synth pad (bright, airy)", "brass swells",
    ],
    "descending": [
        "cello", "bass guitar", "low piano", "organ (sustained)",
        "synth bass", "muted trumpet", "choir (low register)",
    ],
    "oscillating": [
        "electric guitar (clean + distorted)", "Rhodes electric piano",
        "synth arpeggio", "vibraphone", "sitar", "tabla",
    ],
    "flat": [
        "drone synth", "ambient pad", "hang drum", "kalimba",
        "bowed guitar", "sine wave bass", "rain stick",
    ],
}

_SCALE_DEGREES: Dict[str, List[str]] = {
    "major":        ["1", "2", "3", "4", "5", "6", "7"],
    "minor":        ["1", "2", "♭3", "4", "5", "♭6", "♭7"],
    "pentatonic":   ["1", "2", "3", "5", "6"],
    "mixed modal":  ["1", "2", "♭3", "3", "5", "♭7"],
    "blues":        ["1", "♭3", "4", "♭5", "5", "♭7"],
}

_STREAMING_PLATFORMS: List[Dict[str, Any]] = [
    {
        "platform": "Spotify",
        "reach": "global",
        "best_for": ["pop", "hip-hop", "r&b", "rock", "folk", "ambient"],
        "loudness_target_lufs": -14,
        "notes": "Upload via DistroKid, TuneCore, or direct Spotify for Artists. Add Canvas loops for visual engagement.",
    },
    {
        "platform": "Apple Music",
        "reach": "global",
        "best_for": ["pop", "r&b", "classical", "jazz", "folk"],
        "loudness_target_lufs": -16,
        "notes": "Supports Spatial Audio / Dolby Atmos mixes. Submit via distributor for editorial consideration.",
    },
    {
        "platform": "SoundCloud",
        "reach": "indie / underground / global",
        "best_for": ["electronic", "hip-hop", "experimental", "ambient", "spoken word"],
        "loudness_target_lufs": -14,
        "notes": "Strong community for bedroom producers. Use Next Pro for monetisation and scheduling.",
    },
    {
        "platform": "Bandcamp",
        "reach": "direct-to-fan",
        "best_for": ["indie", "experimental", "folk", "jazz", "spoken word"],
        "loudness_target_lufs": -12,
        "notes": "Best for direct fan revenue (artist keeps 85–92%). Ideal for limited editions and merch bundles.",
    },
    {
        "platform": "YouTube Music",
        "reach": "global",
        "best_for": ["all genres"],
        "loudness_target_lufs": -14,
        "notes": "Auto-normalises loudness. Upload official video or lyric video for highest discovery.",
    },
    {
        "platform": "Tidal",
        "reach": "audiophile / global",
        "best_for": ["jazz", "classical", "r&b", "hip-hop", "rock"],
        "loudness_target_lufs": -14,
        "notes": "Supports HiFi lossless and Dolby Atmos. Submit via distributor for Tidal Rising consideration.",
    },
    {
        "platform": "Amazon Music",
        "reach": "global",
        "best_for": ["pop", "country", "r&b", "classical"],
        "loudness_target_lufs": -14,
        "notes": "Reaches Alexa / Echo device users. Good for ambient and background music.",
    },
]

_DISTRIBUTION_SERVICES: List[Dict[str, str]] = [
    {"name": "DistroKid",  "model": "annual subscription", "keep_royalties": "100%",
     "notes": "Fast delivery, unlimited uploads, splits"},
    {"name": "TuneCore",   "model": "per-release fee",     "keep_royalties": "100%",
     "notes": "Detailed analytics, publishing admin available"},
    {"name": "CD Baby",    "model": "one-time fee",        "keep_royalties": "91%",
     "notes": "Sync licensing, publishing, physical distribution"},
    {"name": "Amuse",      "model": "free + Pro tier",     "keep_royalties": "100%",
     "notes": "Mobile-first, artist development program"},
    {"name": "UnitedMasters","model": "free + Select",    "keep_royalties": "100%",
     "notes": "Brand deal opportunities, strong for hip-hop"},
]

_BEAT_PATTERNS: Dict[str, Dict[str, str]] = {
    "4/4": {
        "kick":    "X . . . X . . . X . . . X . . .",
        "snare":   ". . X . . . X . . . X . . . X .",
        "hihat":   "x x x x x x x x x x x x x x x x",
        "note":    "Standard 4/4 grid — kick on 1 and 3, snare on 2 and 4",
    },
    "trap": {
        "kick":    "X . . X . . . . X . . . X . X .",
        "snare":   ". . . . X . . . . . . . X . . .",
        "hihat":   "x . x x . x x . x . x x . x x .",
        "note":    "Trap grid — rolling hi-hats, syncopated kick, sparse snare",
    },
    "boom bap": {
        "kick":    "X . . . . . X . X . . . . . . .",
        "snare":   ". . X . . . . . . . X . . . . .",
        "hihat":   "x . x . x . x . x . x . x . x .",
        "note":    "Boom bap — swinging 8th-note hi-hats, punchy kick/snare",
    },
    "afrobeats": {
        "kick":    "X . . X . . X . X . . X . . X .",
        "snare":   ". . X . . X . . . . X . . X . .",
        "hihat":   "x x . x x . x x . x x . x x . x",
        "note":    "Afrobeats grid — syncopated kick, interlocking hi-hat and snare",
    },
    "6/8": {
        "kick":    "X . . X . . X . . X . .",
        "snare":   ". . X . . X . . X . . X",
        "hihat":   "x x x x x x x x x x x x",
        "note":    "6/8 compound meter — triplet feel, good for ballads and folk",
    },
}


# ---------------------------------------------------------------------------
# 1. Production Plan
# ---------------------------------------------------------------------------

def generate_production_plan(
    lines: List[str],
    pattern_analysis: Dict[str, Any],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Generate a music production plan from structural and emotional analysis.

    Returns
    -------
    dict with keys:
        suggested_bpm_range     – (min, max) BPM
        suggested_key           – neutral key centre suggestion
        time_signature          – suggested time signature
        genre_palette           – list of compatible genre labels
        production_style        – production approach description
        mixing_notes            – list of mixing / arrangement hints
        mastering_target_lufs   – suggested integrated loudness
        production_notes        – plain-language guidance list
    """
    emotional_arc = art_genome.get("emotional_arc", {})
    arc_dir = emotional_arc.get("arc_direction", "flat")
    complexity = float(art_genome.get("complexity_score", 0.0))
    form = art_genome.get("form", "unknown")

    # Syllable rate → tempo feel
    word_count = len(_words(" ".join(lines)))
    line_count = max(len(lines), 1)
    avg_words_per_line = word_count / line_count
    syllable_density = sum(count_syllables(w) for w in _words(" ".join(lines))) / max(word_count, 1)

    # BPM selection
    if syllable_density > 2.5 or avg_words_per_line > 8:
        bpm_min, bpm_max = 75, 95      # dense text → slower delivery BPM
    elif avg_words_per_line < 4:
        bpm_min, bpm_max = 110, 140    # sparse text → energetic
    else:
        bpm_min, bpm_max = 85, 115     # balanced

    # Time signature
    structure = pattern_analysis.get("structure", {})
    avg_syllables_per_line = (
        sum(count_syllables(w) for line in lines for w in _words(line)) / line_count
    )
    if avg_syllables_per_line % 3 < avg_syllables_per_line % 4:
        time_sig = "6/8"
        time_sig_note = "compound duple — triplet feel, suitable for ballads"
    elif complexity > 0.7:
        time_sig = "5/4 or 7/8"
        time_sig_note = "complex meter — reflects the piece's density and sophistication"
    else:
        time_sig = "4/4"
        time_sig_note = "standard — maximum accessibility and production flexibility"

    # Genre palette from arc + form
    genre_map = {
        "ascending":   ["pop", "r&b", "folk", "rock"],
        "descending":  ["ambient", "jazz", "folk", "spoken word"],
        "oscillating": ["hip-hop", "experimental", "r&b", "jazz"],
        "flat":        ["ambient", "drone", "spoken word", "classical"],
    }
    genre_palette = genre_map.get(arc_dir, ["pop", "folk"])

    # Refine by form
    form_genre_boost = {
        "haiku":        ["ambient", "spoken word"],
        "sonnet":       ["classical", "folk"],
        "quatrain":     ["folk", "country", "singer-songwriter"],
        "couplet":      ["hip-hop", "rap"],
        "rhymed verse": ["pop", "rock"],
        "free verse":   ["experimental", "jazz"],
    }
    bonus = form_genre_boost.get(form, [])
    genre_palette = list(dict.fromkeys(bonus + genre_palette))[:5]

    # Production style
    prod_style_map = {
        "ascending":   "Bright, forward-moving production. Clean transients, open reverb tails, rising automation.",
        "descending":  "Intimate, atmospheric. Warm low-end, long decay, subtle saturation, sparse arrangement.",
        "oscillating": "Dynamic contrast. Layer elements that appear and disappear to mirror emotional shifts.",
        "flat":        "Minimal and meditative. Prioritise space and silence. Let the text breathe.",
    }
    production_style = prod_style_map.get(arc_dir, prod_style_map["flat"])

    # Mixing notes
    mixing_notes = [
        "Leave headroom — aim for -6 dBFS peak on the mix bus before mastering.",
        "Use mid-side processing to widen the mix without phase issues in mono.",
    ]
    if arc_dir == "ascending":
        mixing_notes.append("Automate a subtle high-shelf boost (+1 dB) in the final chorus to reinforce the climax.")
    elif arc_dir == "descending":
        mixing_notes.append("Low-pass filter the master bus slightly to give the piece warmth and closeness.")
    if complexity > 0.6:
        mixing_notes.append(
            "With a dense arrangement, use high-pass filters on mid-range elements (> 200 Hz) to clear the low end."
        )
    mixing_notes.append("Reference on earbuds and laptop speakers — not just studio monitors.")

    # Mastering loudness target
    if "ambient" in genre_palette or "spoken word" in genre_palette:
        mastering_lufs = -16
    elif "hip-hop" in genre_palette or "dance/edm" in genre_palette:
        mastering_lufs = -9
    else:
        mastering_lufs = -14

    production_notes = [
        f"Suggested BPM: {bpm_min}–{bpm_max}. Adjust to match the natural speech rhythm of the delivery.",
        f"Time signature: {time_sig} — {time_sig_note}.",
        f"Primary genre palette: {', '.join(genre_palette)}.",
        "These are craft suggestions — override any of them to serve your artistic vision.",
    ]

    # Suggested key (neutral — no specific pitch assignment)
    key_map = {
        "ascending":   "C major or A major (open, resolved, forward-moving)",
        "descending":  "A minor or D minor (introspective, cinematic)",
        "oscillating": "D major / B minor or modal centre (Dorian on D)",
        "flat":        "Open tuning or drone root (no fixed key required)",
    }
    suggested_key = key_map.get(arc_dir, "C major")

    return {
        "suggested_bpm_range":   (bpm_min, bpm_max),
        "suggested_key":         suggested_key,
        "time_signature":        time_sig,
        "genre_palette":         genre_palette,
        "production_style":      production_style,
        "mixing_notes":          mixing_notes,
        "mastering_target_lufs": mastering_lufs,
        "production_notes":      production_notes,
    }


# ---------------------------------------------------------------------------
# 2. Beat Pattern Generator
# ---------------------------------------------------------------------------

def generate_beat_pattern(
    art_genome: Dict[str, Any],
    genre_palette: Optional[List[str]] = None,
) -> dict:
    """
    Generate a rhythmic grid and drum-machine notation.

    Returns
    -------
    dict with keys:
        pattern_name   – name of the suggested pattern
        kick           – 16-step kick pattern (X = hit, . = rest)
        snare          – 16-step snare pattern
        hihat          – 16-step hi-hat pattern
        pattern_note   – description of the groove
        velocity_hint  – velocity accent guidance
        humanise_tip   – tip for adding organic feel
    """
    genre_palette = genre_palette or []
    arc_dir = art_genome.get("emotional_arc", {}).get("arc_direction", "flat")

    # Select pattern
    if any(g in ("trap",) for g in genre_palette):
        key = "trap"
    elif any(g in ("hip-hop", "r&b") for g in genre_palette):
        key = "boom bap"
    elif any(g in ("afrobeats",) for g in genre_palette):
        key = "afrobeats"
    elif arc_dir in ("descending", "flat"):
        key = "6/8"
    else:
        key = "4/4"

    pattern = _BEAT_PATTERNS[key]

    velocity_hint = (
        "Accent the snare on beats 2 and 4 (velocities 100–127). "
        "Ghost notes on snare at velocity 40–60 add depth."
    )
    humanise_tip = (
        "Shift kick/snare hits by ±3–8 ms from the grid for an organic feel. "
        "Vary hi-hat velocity between 50 and 100 to avoid machine-like uniformity."
    )

    return {
        "pattern_name":  key,
        "kick":          pattern["kick"],
        "snare":         pattern["snare"],
        "hihat":         pattern["hihat"],
        "pattern_note":  pattern["note"],
        "velocity_hint": velocity_hint,
        "humanise_tip":  humanise_tip,
    }


# ---------------------------------------------------------------------------
# 3. Instrument Palette
# ---------------------------------------------------------------------------

def suggest_instruments(
    art_genome: Dict[str, Any],
    genre_palette: Optional[List[str]] = None,
) -> dict:
    """
    Suggest an instrument palette based on emotional arc and genre.

    Returns
    -------
    dict with keys:
        primary_instruments    – list of core instruments
        texture_instruments    – list of ambient / supporting instruments
        avoid_note             – instruments that may clash with this emotional register
        layering_hint          – guidance on how to layer the palette
    """
    genre_palette = genre_palette or []
    arc_dir = art_genome.get("emotional_arc", {}).get("arc_direction", "flat")
    complexity = float(art_genome.get("complexity_score", 0.0))

    primary = _EMOTIONAL_INSTRUMENTS.get(arc_dir, _EMOTIONAL_INSTRUMENTS["flat"])[:3]
    texture = _EMOTIONAL_INSTRUMENTS.get(arc_dir, _EMOTIONAL_INSTRUMENTS["flat"])[3:]

    # Genre-specific overrides
    if any(g in ("hip-hop", "trap", "r&b") for g in genre_palette):
        primary = ["808 bass", "sampled loop", "Rhodes electric piano"] + primary[:1]
        texture = ["vinyl crackle", "synth pad", "atmospheric sample"]
    elif any(g in ("folk", "singer-songwriter") for g in genre_palette):
        primary = ["acoustic guitar", "fingerpicked", "upright bass"] + primary[:1]
        texture = ["light percussion (cajon, brush snare)", "strings (sparse)"]
    elif any(g in ("ambient", "experimental") for g in genre_palette):
        primary = ["synthesiser (modular)", "field recordings", "treated piano"]
        texture = ["granular texture", "reversed reverb", "drone pad"]

    avoid_map = {
        "ascending":   "heavy distorted guitars in the intro — save for the climax",
        "descending":  "bright, staccato synths that fight the introspective mood",
        "oscillating": "static, unchanging timbres — this piece needs dynamic contrast",
        "flat":        "busy percussion — silence is an instrument here",
    }
    avoid_note = avoid_map.get(arc_dir, "")

    if complexity > 0.7:
        layering_hint = (
            "Build in layers — start with bass + kick + lead melody, then add "
            "texture and harmony progressively. Dense pieces benefit from contrast "
            "between sparse and full sections."
        )
    else:
        layering_hint = (
            "Keep the arrangement minimal — three well-chosen sounds are stronger "
            "than ten competing ones. Leave space for the voice and the lyric."
        )

    return {
        "primary_instruments": primary,
        "texture_instruments": texture,
        "avoid_note":          avoid_note,
        "layering_hint":       layering_hint,
    }


# ---------------------------------------------------------------------------
# 4. Melody Contour Generator
# ---------------------------------------------------------------------------

def generate_melody_contour(
    lines: List[str],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Generate melodic shape suggestions from the text's syllable and stress pattern.

    Returns
    -------
    dict with keys:
        scale_quality      – scale family
        scale_degrees      – list of scale degree labels
        contour_description – plain-language melodic arc
        phrase_suggestions  – per-line melodic direction suggestions
        ornamentation_tips  – list of ornament / technique suggestions
    """
    emotional_arc = art_genome.get("emotional_arc", {})
    arc_dir = emotional_arc.get("arc_direction", "flat")
    complexity = float(art_genome.get("complexity_score", 0.0))

    # Scale family
    scale_map = {
        "ascending":   "major",
        "descending":  "minor",
        "oscillating": "mixed modal",
        "flat":        "pentatonic",
    }
    scale_quality = scale_map.get(arc_dir, "major")
    if complexity > 0.75:
        scale_quality = "blues"  # complex + dense → blues chromaticism

    degrees = _SCALE_DEGREES.get(scale_quality, _SCALE_DEGREES["major"])

    # Overall contour
    contour_map = {
        "ascending":   "Start low on tonic (1), rise through the phrase, peak on the 5th or 6th scale degree at the emotional height.",
        "descending":  "Start high (on the 5th or 6th), fall gradually through the phrase, resolve or leave unresolved on the tonic or ♭7.",
        "oscillating": "Alternate between high and low register across phrases. Let tension and release mirror the emotional oscillation.",
        "flat":        "Stay close to the tonic and pentatonic shape. Minimal leaps — melodic calmness mirrors the text's stillness.",
    }
    contour_description = contour_map.get(arc_dir, contour_map["flat"])

    # Per-line suggestions
    phrase_suggestions = []
    for i, line in enumerate(lines[:8]):  # limit to first 8 lines for readability
        words = _words(line)
        syllables = sum(count_syllables(w) for w in words)
        stressed = [i for i, w in enumerate(words) if count_syllables(w) > 1]
        if syllables > 10:
            direction = "descending phrase — dense syllable count favours falling melody"
        elif syllables < 4:
            direction = "ascending leap — short line leaves space for a melodic jump"
        else:
            direction = "arched phrase — rise mid-line, resolve at the end"
        phrase_suggestions.append({
            "line_preview": (line[:40] + "…") if len(line) > 40 else line,
            "syllable_count": syllables,
            "melodic_direction": direction,
        })

    ornamentation_tips = [
        "Use melisma (multiple notes on one syllable) on emotionally significant words.",
        "A brief grace note (acciaccatura) on stressed syllables adds vocal character.",
        "Vibrato on held notes — but use it intentionally, not as a default.",
    ]
    if arc_dir == "flat":
        ornamentation_tips.append("Consider singing slightly below pitch on held notes for an intimate, human quality.")
    elif arc_dir == "ascending":
        ornamentation_tips.append("A head-voice break (passaggio) at the emotional peak can be deeply powerful.")

    return {
        "scale_quality":        scale_quality,
        "scale_degrees":        degrees,
        "contour_description":  contour_description,
        "phrase_suggestions":   phrase_suggestions,
        "ornamentation_tips":   ornamentation_tips,
    }


# ---------------------------------------------------------------------------
# 5. Distribution Channel Guidance
# ---------------------------------------------------------------------------

def suggest_distribution_channels(
    art_genome: Dict[str, Any],
    genre_palette: Optional[List[str]] = None,
) -> dict:
    """
    Recommend streaming and distribution platforms suited to this piece.

    Returns
    -------
    dict with keys:
        recommended_platforms  – list of platform dicts (ranked by fit)
        distribution_services  – list of recommended digital distributors
        release_strategy_tips  – list of release strategy notes
        rights_reminder        – ethical note on artist rights
    """
    genre_palette = genre_palette or []
    arc_dir = art_genome.get("emotional_arc", {}).get("arc_direction", "flat")

    # Score platforms
    scored: List[tuple] = []
    for plat in _STREAMING_PLATFORMS:
        score = 0
        for g in genre_palette:
            if any(g.lower() in bf.lower() for bf in plat["best_for"]):
                score += 2
        if "all genres" in plat["best_for"]:
            score += 1
        scored.append((score, plat))

    scored.sort(key=lambda x: x[0], reverse=True)
    recommended = [p for _, p in scored[:5]]

    release_strategy_tips = [
        "Release on a Friday (global music release day) for maximum playlist consideration.",
        "Submit for editorial playlist consideration at least 7 days before release.",
        "Create a 'pre-save' campaign to build day-one stream counts.",
        "Release a lyric video or visualiser alongside the audio for YouTube and social.",
    ]
    if "ambient" in genre_palette or arc_dir == "flat":
        release_strategy_tips.append(
            "Ambient and contemplative pieces perform well in study/focus playlists — pitch to those curators."
        )
    if "experimental" in genre_palette:
        release_strategy_tips.append(
            "Bandcamp and SoundCloud have stronger communities for experimental work — prioritise them."
        )

    rights_reminder = (
        "You own your master recordings. Register them with a PRO (ASCAP, BMI, SESAC, PRS) "
        "to collect performance and mechanical royalties. Consider registering with SoundExchange "
        "for digital performance royalties."
    )

    return {
        "recommended_platforms":  recommended,
        "distribution_services":  _DISTRIBUTION_SERVICES,
        "release_strategy_tips":  release_strategy_tips,
        "rights_reminder":        rights_reminder,
    }


# ---------------------------------------------------------------------------
# 6. Streaming Metadata
# ---------------------------------------------------------------------------

def generate_streaming_metadata(
    lines: List[str],
    art_genome: Dict[str, Any],
    genre_palette: Optional[List[str]] = None,
    artist_name: Optional[str] = None,
) -> dict:
    """
    Generate streaming-optimised metadata for release submission.

    Returns
    -------
    dict with keys:
        suggested_title_words   – prominent thematic words for a title
        genre_tags              – comma-separated genre string
        mood_tags               – mood keywords
        isrc_note               – ISRC registration guidance
        loudness_targets        – per-platform loudness targets
        audio_format_note       – recommended audio format and bit depth
        release_checklist       – pre-release action list
    """
    genre_palette = genre_palette or []

    # Thematic words from top-frequency content words
    stop = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "of", "i", "is", "it"}
    word_freq: Dict[str, int] = {}
    for line in lines:
        for w in _words(line):
            w_clean = _normalise(w)
            if w_clean and w_clean not in stop and len(w_clean) > 2:
                word_freq[w_clean] = word_freq.get(w_clean, 0) + 1
    title_words = sorted(word_freq, key=lambda w: word_freq[w], reverse=True)[:5]

    # Mood tags from emotional arc
    mood_map = {
        "ascending":   ["hopeful", "uplifting", "triumphant"],
        "descending":  ["melancholic", "introspective", "haunting"],
        "oscillating": ["complex", "dynamic", "searching"],
        "flat":        ["meditative", "calm", "contemplative"],
    }
    arc_dir = art_genome.get("emotional_arc", {}).get("arc_direction", "flat")
    mood_tags = mood_map.get(arc_dir, ["reflective"])

    # Loudness targets by platform
    loudness_targets = [
        {"platform": p["platform"], "target_lufs": p["loudness_target_lufs"]}
        for p in _STREAMING_PLATFORMS[:5]
    ]

    isrc_note = (
        "Register an ISRC (International Standard Recording Code) for this recording. "
        "Free via your national ISRC agency or through your digital distributor. "
        "Each unique recording requires its own ISRC."
    )

    audio_format_note = (
        "Master at 24-bit / 48 kHz WAV. Distribute as WAV or FLAC (lossless). "
        "The distributor will generate platform-specific encodes (AAC, MP3, OGG)."
    )

    release_checklist = [
        "☐ Register as songwriter/composer with a PRO (ASCAP / BMI / PRS etc.)",
        "☐ Obtain ISRC code for each track",
        "☐ Register song copyright (US: copyright.gov, UK: intellectual-property.service.gov.uk)",
        "☐ Export master WAV at 24-bit / 48 kHz",
        "☐ Prepare cover art (3000×3000 px, sRGB, < 10 MB)",
        "☐ Write release description (1–3 sentences, your voice)",
        "☐ Choose release date and submit to distributor ≥ 7 days in advance",
        "☐ Set up pre-save / pre-order campaign",
        "☐ Pitch to editorial playlists via Spotify for Artists and Apple Music",
    ]

    return {
        "suggested_title_words": title_words,
        "genre_tags":            ", ".join(genre_palette),
        "mood_tags":             mood_tags,
        "isrc_note":             isrc_note,
        "loudness_targets":      loudness_targets,
        "audio_format_note":     audio_format_note,
        "release_checklist":     release_checklist,
    }


# ---------------------------------------------------------------------------
# 7. Sample Palette
# ---------------------------------------------------------------------------

def generate_sample_palette(
    art_genome: Dict[str, Any],
    genre_palette: Optional[List[str]] = None,
) -> dict:
    """
    Suggest sample, loop, and texture categories for this piece.

    Returns
    -------
    dict with keys:
        sample_categories  – list of sample types to search for
        texture_suggestions – list of texture/atmosphere ideas
        crate_digging_tips  – tips for finding unique source material
        clearance_reminder  – ethical/legal note on sample clearance
    """
    genre_palette = genre_palette or []
    arc_dir = art_genome.get("emotional_arc", {}).get("arc_direction", "flat")

    base_samples = {
        "ascending":   ["orchestral risers", "vocal chops (pitched up)", "filtered strings", "piano loops"],
        "descending":  ["vinyl soul records", "dusty jazz breaks", "lo-fi piano", "ambient field recordings"],
        "oscillating": ["funk breaks", "bossa nova guitar loops", "sitar riffs", "live drum breaks"],
        "flat":        ["nature sounds", "ambient pads", "Tibetan bowls", "rain / water textures"],
    }
    sample_categories = base_samples.get(arc_dir, base_samples["flat"])

    texture_suggestions = [
        "Vinyl crackle layered under the main instrument adds warmth and nostalgia.",
        "A distant crowd recording or room ambience creates spatial depth.",
        "Reversed reverb tails at section transitions smooth the arrangement flow.",
    ]
    if arc_dir == "ascending":
        texture_suggestions.append("A subtle wind or breath sound under the intro creates anticipation.")
    elif arc_dir == "descending":
        texture_suggestions.append("Rain or running water beneath the mix reinforces introspection.")

    crate_digging_tips = [
        "Freesound.org — free Creative Commons samples and field recordings.",
        "Splice.com — royalty-free loops and one-shots by genre and BPM.",
        "Looperman.com — community-uploaded loops (check licence per upload).",
        "Sample from original recordings only after confirming clearance rights.",
        "Recording your own instruments — even one unique sound — makes the track yours.",
    ]

    clearance_reminder = (
        "If you use a copyrighted sample, obtain clearance from both the master "
        "rights holder (label) and the publishing rights holder (songwriter). "
        "Uncleared samples can result in takedowns and legal liability. "
        "Original recordings are always the safest and most artistically sovereign choice."
    )

    return {
        "sample_categories":    sample_categories,
        "texture_suggestions":  texture_suggestions,
        "crate_digging_tips":   crate_digging_tips,
        "clearance_reminder":   clearance_reminder,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def produce(
    text: str,
    pattern_analysis: Dict[str, Any],
    art_genome_dict: Dict[str, Any],
    artist_name: Optional[str] = None,
) -> dict:
    """
    Full music production pipeline.

    Parameters
    ----------
    text             – the raw art text
    pattern_analysis – output of kalacore.pattern_engine.analyze()
    art_genome_dict  – output of kalacore.art_genome.build_art_genome().to_dict()
    artist_name      – optional artist name for metadata

    Returns
    -------
    dict with keys:
        production_plan        – generate_production_plan()
        beat_pattern           – generate_beat_pattern()
        instruments            – suggest_instruments()
        melody_contour         – generate_melody_contour()
        distribution           – suggest_distribution_channels()
        streaming_metadata     – generate_streaming_metadata()
        sample_palette         – generate_sample_palette()
    """
    raw_lines = text.splitlines()
    lines = [l for l in raw_lines if l.strip()]

    production_plan = generate_production_plan(lines, pattern_analysis, art_genome_dict)
    genre_palette = production_plan["genre_palette"]

    beat_pattern = generate_beat_pattern(art_genome_dict, genre_palette)
    instruments = suggest_instruments(art_genome_dict, genre_palette)
    melody_contour = generate_melody_contour(lines, art_genome_dict)
    distribution = suggest_distribution_channels(art_genome_dict, genre_palette)
    streaming_meta = generate_streaming_metadata(lines, art_genome_dict, genre_palette, artist_name)
    sample_palette = generate_sample_palette(art_genome_dict, genre_palette)

    return {
        "production_plan":    production_plan,
        "beat_pattern":       beat_pattern,
        "instruments":        instruments,
        "melody_contour":     melody_contour,
        "distribution":       distribution,
        "streaming_metadata": streaming_meta,
        "sample_palette":     sample_palette,
    }

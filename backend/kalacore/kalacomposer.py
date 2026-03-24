"""
KalaComposer  (Phase 3 – Musical Composition Tools)
-----------------------------------------------------
Translates the structural and emotional intelligence from KalaCore into
musical composition suggestions — without generating audio or overriding
the artist's sonic vision.

Philosophy
----------
  • These are starting-point suggestions, not prescriptions.
  • Every musical idea is optional and belongs to the artist.
  • The suggestions serve the art — they don't define it.

Functions
---------
map_text_to_musical_structure  – derive verse / chorus / bridge sections
                                  from the text's structural analysis
suggest_chord_progression       – emotional arc → harmonic palette
suggest_tempo                   – syllable flow + meter → BPM range + feel
generate_arrangement_notes      – emotional register → instrumentation ideas
map_lyric_rhythm_to_beat        – stress pattern → beat position alignment

Public API
----------
compose(text, pattern_analysis, art_genome_dict) → full composition dict
"""

import math
from typing import Any, Dict, List, Tuple

from kalacore.pattern_engine import _words, count_syllables, _normalise


# ---------------------------------------------------------------------------
# Chord vocabulary
# ---------------------------------------------------------------------------

# Quality families keyed by emotional register
_MAJOR_PROGRESSIONS = [
    ("I – IV – V – I",    "classic resolution, grounded and complete"),
    ("I – V – vi – IV",   "anthemic, open, widely beloved"),
    ("I – IV – vi – V",   "hopeful ascent with a twist"),
    ("I – iii – IV – V",  "bright and forward-moving"),
]

_MINOR_PROGRESSIONS = [
    ("i – VII – VI – VII",  "cinematic tension, unresolved longing"),
    ("i – iv – VII – III",  "descending gravity, introspective"),
    ("i – VI – III – VII",  "melancholic elegance"),
    ("i – v – iv – i",      "deep minor, rooted in darkness"),
]

_MIXED_PROGRESSIONS = [
    ("I – vi – IV – V",    "familiar warmth with emotional shadows"),
    ("vi – IV – I – V",    "starts in the minor, resolves to light"),
    ("i – III – VII – VI", "modal, drifting between moods"),
]

_SIMPLE_PROGRESSIONS = [
    ("I – V – I",       "minimal, meditative, spacious"),
    ("I – IV – I",      "drone-adjacent, hypnotic repetition"),
    ("i – VII – i",     "stark, minimal, powerful"),
]

# Modes keyed by arc
_SCALE_MAP = {
    "ascending":   ("major",        "Ionian / Lydian"),
    "descending":  ("minor",        "Aeolian / Dorian"),
    "oscillating": ("mixed modal",  "Mixolydian or modal interchange"),
    "flat":        ("pentatonic",   "pentatonic minor / major — open and unforced"),
}


# ---------------------------------------------------------------------------
# 1. Musical Structure Mapping
# ---------------------------------------------------------------------------

def map_text_to_musical_structure(
    lines: List[str],
    pattern_analysis: Dict[str, Any],
) -> dict:
    """
    Derive probable song sections (verse / chorus / bridge / outro) from
    the structural analysis of the text.

    Rules
    -----
    - Refrain lines → chorus candidates
    - Repeated (but not refrain) lines → hook candidates
    - Unique lines in a repetitive piece → bridge candidates
    - The final distinct block → outro candidate

    Returns
    -------
    dict with keys:
        sections        – list of {lines, role, note} dicts
        section_map     – {line_index: role} quick lookup
        has_chorus      – bool
        has_bridge      – bool
        structural_notes – list of plain-language observations
    """
    structure = pattern_analysis.get("structure", {})
    refrains: set = set(structure.get("refrains", []))
    repeated: dict = structure.get("repeated_lines", {})

    sections: List[dict] = []
    section_map: Dict[int, str] = {}
    structural_notes: List[str] = []
    has_chorus = False
    has_bridge = False

    for i, line in enumerate(lines):
        norm = _normalise(line)
        if norm in refrains:
            role = "chorus"
            has_chorus = True
        elif norm in repeated:
            role = "hook"
        else:
            role = "verse"
        section_map[i] = role

    # Identify bridge candidates: unique lines surrounded by repeated lines
    for i, line in enumerate(lines):
        if section_map.get(i) == "verse":
            prev_is_hook = i > 0 and section_map.get(i - 1) in ("chorus", "hook")
            next_is_hook = i < len(lines) - 1 and section_map.get(i + 1) in ("chorus", "hook")
            if prev_is_hook and next_is_hook:
                section_map[i] = "bridge"
                has_bridge = True

    # Mark last 1-2 unique lines as outro if piece ends on verse
    if lines and section_map.get(len(lines) - 1) == "verse":
        section_map[len(lines) - 1] = "outro"

    # Build sections list (group consecutive same-role lines)
    current_role = section_map.get(0, "verse")
    current_block: List[str] = []
    for i, line in enumerate(lines):
        role = section_map.get(i, "verse")
        if role == current_role:
            current_block.append(line)
        else:
            sections.append({"lines": current_block, "role": current_role})
            current_role = role
            current_block = [line]
    if current_block:
        sections.append({"lines": current_block, "role": current_role})

    # Structural observations
    verse_count = sum(1 for s in sections if s["role"] == "verse")
    chorus_count = sum(1 for s in sections if s["role"] == "chorus")
    if has_chorus:
        structural_notes.append(
            f"The piece contains {chorus_count} chorus-like section(s) — natural anchor points."
        )
    else:
        structural_notes.append(
            "No obvious chorus detected — the piece flows as continuous verse, "
            "or the refrain may emerge through repetition in performance."
        )
    if has_bridge:
        structural_notes.append(
            "A bridge section is present — this creates space for emotional contrast."
        )
    if verse_count >= 2:
        structural_notes.append(
            f"{verse_count} distinct verse section(s) suggest a narrative arc across the piece."
        )

    return {
        "sections": sections,
        "section_map": section_map,
        "has_chorus": has_chorus,
        "has_bridge": has_bridge,
        "structural_notes": structural_notes,
    }


# ---------------------------------------------------------------------------
# 2. Chord Progression Suggestions
# ---------------------------------------------------------------------------

def suggest_chord_progression(art_genome: Dict[str, Any]) -> dict:
    """
    Suggest harmonic palettes grounded in the emotional arc and complexity.

    Returns
    -------
    dict with keys:
        scale_quality      – "major", "minor", "mixed modal", "pentatonic"
        scale_name         – specific scale/mode suggestion
        primary_progressions – list of {progression, feel} dicts (top 2)
        secondary_progression – one contrasting suggestion
        key_note_suggestions – neutral key suggestions (no prescriptive key)
        harmonic_notes       – plain-language guidance
    """
    emotional_arc = art_genome.get("emotional_arc", {})
    arc_dir = emotional_arc.get("arc_direction", "flat")
    complexity = float(art_genome.get("complexity_score", 0.0))
    mean_valence = float(emotional_arc.get("mean_valence", 0.0))

    scale_quality, scale_name = _SCALE_MAP.get(arc_dir, ("pentatonic", "pentatonic"))

    # Pick progressions based on emotional quality + complexity
    if scale_quality == "major":
        pool = _MAJOR_PROGRESSIONS
        contrast_pool = _MIXED_PROGRESSIONS
    elif scale_quality == "minor":
        pool = _MINOR_PROGRESSIONS
        contrast_pool = _MIXED_PROGRESSIONS
    elif scale_quality == "mixed modal":
        pool = _MIXED_PROGRESSIONS
        contrast_pool = _MAJOR_PROGRESSIONS
    else:
        pool = _SIMPLE_PROGRESSIONS
        contrast_pool = _MAJOR_PROGRESSIONS

    # High complexity → prefer richer, less resolved progressions
    # Use complexity to select which progressions to prioritise
    idx_a = min(int(complexity * len(pool)), len(pool) - 1)
    idx_b = (idx_a + 1) % len(pool)
    primary = [
        {"progression": pool[idx_a][0], "feel": pool[idx_a][1]},
        {"progression": pool[idx_b][0], "feel": pool[idx_b][1]},
    ]

    contrast_idx = int(complexity * len(contrast_pool)) % len(contrast_pool)
    secondary = {
        "progression": contrast_pool[contrast_idx][0],
        "feel": contrast_pool[contrast_idx][1],
        "note": "For a contrasting section or bridge — explore or ignore as you wish.",
    }

    # Neutral key suggestions (starting points, not prescriptions)
    key_suggestions = {
        "major": ["C major", "G major", "D major", "A major"],
        "minor": ["A minor", "E minor", "D minor", "B minor"],
        "mixed modal": ["D Mixolydian", "A Dorian", "G Lydian"],
        "pentatonic": ["C pentatonic", "G pentatonic", "A minor pentatonic"],
    }

    harmonic_notes = [
        f"The {arc_dir} emotional arc suggests a {scale_quality} harmonic foundation.",
        f"Scale suggestion: {scale_name}.",
        "These are starting points — modulate wherever the music wants to go.",
    ]
    if mean_valence < -0.1:
        harmonic_notes.append(
            "The overall valence is negative — a lower root note or darker voicing may feel right."
        )
    elif mean_valence > 0.1:
        harmonic_notes.append(
            "The overall valence is positive — brighter voicings and higher register may complement."
        )

    return {
        "scale_quality": scale_quality,
        "scale_name": scale_name,
        "primary_progressions": primary,
        "secondary_progression": secondary,
        "key_note_suggestions": key_suggestions.get(scale_quality, []),
        "harmonic_notes": harmonic_notes,
    }


# ---------------------------------------------------------------------------
# 3. Tempo and Time Signature Suggestions
# ---------------------------------------------------------------------------

def suggest_tempo(lines: List[str], art_genome: Dict[str, Any]) -> dict:
    """
    Derive a BPM range and feel from syllabic density and meter flow.

    Returns
    -------
    dict with keys:
        bpm_range          – (min_bpm, max_bpm) tuple
        feel               – "urgent", "flowing", "meditative", "conversational"
        time_signature_suggestions – list of options
        tempo_notes        – plain-language guidance
    """
    # Average syllables per line
    syl_totals = [
        sum(count_syllables(w) for w in _words(l)) for l in lines
    ]
    avg_syl = sum(syl_totals) / max(len(syl_totals), 1)

    # Flow regularity from art_genome is not directly available here —
    # we approximate from syllable variance
    if len(syl_totals) > 1:
        mean = sum(syl_totals) / len(syl_totals)
        variance = sum((x - mean) ** 2 for x in syl_totals) / len(syl_totals)
        std = math.sqrt(variance)
        flow_score = max(0.0, 1.0 - (std / max(mean, 1)))
    else:
        flow_score = 1.0

    emotional_arc = art_genome.get("emotional_arc", {})
    mean_valence = float(emotional_arc.get("mean_valence", 0.0))
    arc_dir = emotional_arc.get("arc_direction", "flat")

    # Base BPM from syllable density:
    # dense lines (many syllables) → can sustain higher BPM
    # sparse lines → breathe at lower BPM
    base_bpm = int(60 + (avg_syl - 4) * 8)
    base_bpm = max(50, min(base_bpm, 160))

    # Adjust for emotional charge
    if mean_valence > 0.1 or arc_dir == "ascending":
        base_bpm = min(base_bpm + 10, 180)
    elif mean_valence < -0.1 or arc_dir == "descending":
        base_bpm = max(base_bpm - 10, 40)

    bpm_range = (max(40, base_bpm - 12), min(200, base_bpm + 12))

    # Feel
    if base_bpm >= 120:
        feel = "urgent"
    elif base_bpm >= 90:
        feel = "flowing"
    elif base_bpm >= 65:
        feel = "conversational"
    else:
        feel = "meditative"

    # Time signature suggestions
    if flow_score >= 0.8:
        time_sigs = ["4/4 (regular, grounded)", "3/4 (waltz, if the meter feels like threes)"]
    elif flow_score >= 0.5:
        time_sigs = ["4/4", "6/8 (compound, adds a rolling feel)"]
    else:
        time_sigs = [
            "free time (the meter is irregular — let the phrase length breathe)",
            "5/4 or 7/8 (if you want to capture the rhythmic variation)",
        ]

    tempo_notes = [
        f"Suggested BPM range: {bpm_range[0]}–{bpm_range[1]}.",
        f"Feel: {feel}.",
        "These are starting points — trust your ear over any algorithm.",
    ]
    if flow_score < 0.5:
        tempo_notes.append(
            "The syllable flow is irregular — rubato or free time may serve this piece better than a click track."
        )

    return {
        "bpm_range": bpm_range,
        "feel": feel,
        "time_signature_suggestions": time_sigs,
        "tempo_notes": tempo_notes,
    }


# ---------------------------------------------------------------------------
# 4. Arrangement Notes
# ---------------------------------------------------------------------------

# Instrument colour palette mapped to emotional/structural characteristics
_INSTRUMENT_PALETTES = {
    "ascending_bright": [
        "acoustic guitar (fingerpicked)",
        "piano (upper register)",
        "strings (rising figure)",
        "light percussion (brushed snare)",
    ],
    "descending_dark": [
        "electric guitar (clean, reverb-heavy)",
        "piano (lower register, sparse)",
        "cello or bass cello",
        "minimal percussion or none",
    ],
    "oscillating_complex": [
        "layered synths (pads)",
        "piano and guitar in conversation",
        "strings with dissonance resolved",
        "polyrhythmic percussion",
    ],
    "flat_meditative": [
        "solo voice or voice + single instrument",
        "ambient pads (drone)",
        "light percussion (shakers or frame drum)",
        "silence as part of the arrangement",
    ],
}


def generate_arrangement_notes(
    lines: List[str],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Suggest instrumentation and arrangement ideas grounded in emotional
    register and structural signals.

    Returns
    -------
    dict with keys:
        palette             – instrument suggestions list
        arrangement_style   – one-line style description
        density_guidance    – sparse / moderate / full arrangement suggestion
        production_notes    – plain-language ideas
    """
    emotional_arc = art_genome.get("emotional_arc", {})
    arc_dir = emotional_arc.get("arc_direction", "flat")
    mean_valence = float(emotional_arc.get("mean_valence", 0.0))
    complexity = float(art_genome.get("complexity_score", 0.0))
    cognitive_load = float(art_genome.get("cognitive_load", 0.0))

    # Pick palette
    if arc_dir == "ascending" and mean_valence >= 0:
        palette_key = "ascending_bright"
        style = "bright, building, emotionally open"
    elif arc_dir in ("descending", "flat") and mean_valence < 0:
        palette_key = "descending_dark"
        style = "intimate, sparse, emotionally weighted"
    elif arc_dir == "oscillating":
        palette_key = "oscillating_complex"
        style = "layered, dynamic, emotionally complex"
    else:
        palette_key = "flat_meditative"
        style = "spacious, uncluttered, meditative"

    palette = _INSTRUMENT_PALETTES[palette_key]

    # Density based on cognitive load + complexity
    density_score = (complexity + cognitive_load) / 2.0
    if density_score > 0.6:
        density = "full arrangement — the lyrical and harmonic complexity can carry more instruments"
    elif density_score > 0.35:
        density = "moderate arrangement — 2–3 instruments, space preserved for the lyric to breathe"
    else:
        density = "sparse arrangement — voice + 1 instrument may be all this piece needs"

    production_notes = [
        f"Arrangement style: {style}.",
        density,
        "Consider the silence as an instrument — gaps in the arrangement can carry as much meaning as the notes.",
    ]
    if art_genome.get("creative_risk_index", 0.0) > 0.4:
        production_notes.append(
            "The piece takes significant creative risks — the arrangement can honour that by avoiding conventions."
        )

    return {
        "palette": palette,
        "arrangement_style": style,
        "density_guidance": density,
        "production_notes": production_notes,
    }


# ---------------------------------------------------------------------------
# 5. Lyric–Beat Alignment
# ---------------------------------------------------------------------------

def map_lyric_rhythm_to_beat(lines: List[str]) -> List[dict]:
    """
    Align the stress pattern of each line to beat positions.

    Stressed syllables (S) land on strong beats (1, 3 in 4/4).
    Unstressed syllables (U) fall on weak beats (2, 4, offbeats).

    Returns per-line list with:
        line            – original line
        beat_positions  – list of {word, syllables, beat_hint} per word
        rhythmic_shape  – "front-heavy", "even", "end-heavy"
    """
    _FUNCTION_WORDS = frozenset({
        "a", "an", "the", "in", "on", "at", "of", "to", "for", "and", "but",
        "or", "is", "was", "be", "by", "do", "did", "has", "had", "it", "its",
        "my", "no", "not", "so", "us", "we", "as", "if", "can",
        "with", "you", "your", "they", "them", "that", "this",
    })

    results = []
    for line in lines:
        ws = _words(line)
        if not ws:
            results.append({"line": line, "beat_positions": [], "rhythmic_shape": "empty"})
            continue

        positions = []
        beat_counter = 1  # 1-indexed beat position within a 4/4 bar
        total_beats = 4
        stressed_early = 0
        stressed_late = 0
        total_stressed = 0
        mid = len(ws) // 2

        for i, word in enumerate(ws):
            stressed = word not in _FUNCTION_WORDS
            syl_count = count_syllables(word)
            beat_hint = f"beat {beat_counter}" if stressed else f"off-beat near {beat_counter}"
            positions.append({
                "word": word,
                "syllables": syl_count,
                "stressed": stressed,
                "beat_hint": beat_hint,
            })
            if stressed:
                total_stressed += 1
                if i < mid:
                    stressed_early += 1
                else:
                    stressed_late += 1
            beat_counter = (beat_counter % total_beats) + 1

        if total_stressed == 0:
            shape = "even"
        elif stressed_early > stressed_late * 1.5:
            shape = "front-heavy"
        elif stressed_late > stressed_early * 1.5:
            shape = "end-heavy"
        else:
            shape = "even"

        results.append({
            "line": line,
            "beat_positions": positions,
            "rhythmic_shape": shape,
        })
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose(
    text: str,
    pattern_analysis: Dict[str, Any],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Full KalaComposer analysis.

    Parameters
    ----------
    text             : original multi-line text
    pattern_analysis : output of kalacore.pattern_engine.analyze()
    art_genome       : output of kalacore.art_genome.ArtGenome.to_dict()

    Returns
    -------
    dict with keys:
        musical_structure, chord_suggestions, tempo, arrangement,
        lyric_beat_alignment
    """
    raw_lines = text.splitlines()
    lines = [l for l in raw_lines if l.strip()]

    if not lines:
        return {
            "musical_structure": {},
            "chord_suggestions": {},
            "tempo": {},
            "arrangement": {},
            "lyric_beat_alignment": [],
        }

    return {
        "musical_structure": map_text_to_musical_structure(lines, pattern_analysis),
        "chord_suggestions": suggest_chord_progression(art_genome),
        "tempo": suggest_tempo(lines, art_genome),
        "arrangement": generate_arrangement_notes(lines, art_genome),
        "lyric_beat_alignment": map_lyric_rhythm_to_beat(lines),
    }

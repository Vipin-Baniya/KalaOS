"""
KalaFlow  (Phase 5 – Distribution & Release Intelligence)
----------------------------------------------------------
Artist-first tools for understanding how a piece of art might move
through the world — without subjecting it to algorithmic gatekeeping.

Philosophy
----------
  • A piece can be ready without being "optimised".
  • Distribution is logistics, not judgement.
  • The artist decides what releases — not the platform.
  • Metadata serves findability, not ranking.

Functions
---------
assess_distribution_readiness  – is the piece structurally complete?
generate_release_metadata       – mood tags, genre hints, structural summary
calculate_listener_journey      – emotional arc as listener experience narrative
detect_format_suitability       – single / EP / album structural assessment
build_artist_statement_prompts  – questions to help artist articulate intent

Public API
----------
flow(text, pattern_analysis, art_genome_dict) → full flow dict
"""

from typing import Any, Dict, List

from kalacore.pattern_engine import _words, _normalise, count_syllables


# ---------------------------------------------------------------------------
# Vocabulary for tagging
# ---------------------------------------------------------------------------

# Mood tags mapped to emotional arc direction and valence
_MOOD_TAGS = {
    "ascending":   ["hopeful", "uplifting", "resilient", "triumphant", "awakening"],
    "descending":  ["melancholic", "introspective", "grieving", "haunting", "heavy"],
    "oscillating": ["complex", "emotionally layered", "dynamic", "conflicted", "searching"],
    "flat":        ["meditative", "steady", "understated", "minimal", "contemplative"],
}

# Genre hints by structural characteristics
_FORM_TO_GENRE = {
    "haiku":          ["spoken word", "ambient poetry", "neo-classical"],
    "sonnet":         ["literary song", "chamber folk", "art song"],
    "quatrain":       ["folk", "country", "singer-songwriter", "indie folk"],
    "ballad stanza":  ["ballad", "folk", "Americana", "country"],
    "couplet":        ["rap", "spoken word", "hip-hop", "pop hook"],
    "rhymed verse":   ["pop", "rock", "R&B", "hip-hop"],
    "free verse":     ["spoken word", "experimental", "alternative", "avant-garde"],
    "tercet":         ["experimental poetry", "art song", "drone folk"],
    "distich":        ["minimalist", "aphoristic", "spoken word"],
    "unknown":        ["open / genre-undefined"],
}


# ---------------------------------------------------------------------------
# 1. Distribution Readiness Assessment
# ---------------------------------------------------------------------------

def assess_distribution_readiness(
    lines: List[str],
    pattern_analysis: Dict[str, Any],
) -> dict:
    """
    Assess whether the piece has the structural attributes of a complete work
    ready for release.

    Checks
    ------
    1. Completeness   – non-trivial length (≥ 4 lines)
    2. Coherence      – not entirely blank / placeholder text
    3. Opening hook   – first line is distinct (not a refrain / repeated line)
    4. Emotional arc  – some movement or intentional stasis
    5. Closure        – last line is distinct (creates a sense of ending)

    Returns
    -------
    dict with keys:
        is_ready        – bool
        readiness_score – [0,1]
        checks          – list of {check, passed, note} dicts
        notes           – plain-language summary
    """
    structure = pattern_analysis.get("structure", {})
    refrains: set = set(structure.get("refrains", []))
    emotional_arc = pattern_analysis.get("emotional_arc", {})
    arc_dir = emotional_arc.get("arc_direction", "flat")

    checks = []

    # Check 1: Length
    length_ok = len(lines) >= 4
    checks.append({
        "check": "sufficient_length",
        "passed": length_ok,
        "note": (
            "At least 4 lines present — a complete artistic statement."
            if length_ok else
            "Very short piece — could be intentionally minimal or a fragment."
        ),
    })

    # Check 2: Not all identical lines
    unique_norms = len(set(_normalise(l) for l in lines))
    coherent = unique_norms >= max(len(lines) // 2, 1)
    checks.append({
        "check": "lyric_coherence",
        "passed": coherent,
        "note": (
            "Varied language present — the piece has content."
            if coherent else
            "Very high repetition — intentional or work-in-progress?"
        ),
    })

    # Check 3: Opening hook
    first_norm = _normalise(lines[0]) if lines else ""
    first_is_hook = first_norm not in refrains
    checks.append({
        "check": "opening_hook",
        "passed": first_is_hook,
        "note": (
            "Opening line is distinct — draws the listener in immediately."
            if first_is_hook else
            "Opening with a refrain — creates immediate recognition but delays narrative entry."
        ),
    })

    # Check 4: Emotional arc
    arc_present = arc_dir != "flat"
    checks.append({
        "check": "emotional_arc",
        "passed": arc_present,
        "note": (
            f"Emotional arc detected ({arc_dir}) — the piece has emotional movement."
            if arc_present else
            "Flat emotional arc — this may be intentional (meditative, drone) or a development opportunity."
        ),
    })

    # Check 5: Closure
    last_norm = _normalise(lines[-1]) if lines else ""
    closes_distinctly = last_norm not in refrains or len(lines) < 3
    checks.append({
        "check": "strong_closure",
        "passed": closes_distinctly,
        "note": (
            "Final line creates a distinct close."
            if closes_distinctly else
            "Ends on a refrain — circular structure, may feel unresolved or intentionally open."
        ),
    })

    passed = sum(1 for c in checks if c["passed"])
    readiness_score = round(passed / len(checks), 4)
    is_ready = readiness_score >= 0.6

    notes_list = []
    if is_ready:
        notes_list.append("This piece has the structural attributes of a complete work.")
    else:
        notes_list.append("This piece may still be in development — or intentionally minimal.")
    notes_list.append(
        "Readiness is structural, not qualitative. Only the artist decides when it's ready."
    )

    return {
        "is_ready": is_ready,
        "readiness_score": readiness_score,
        "checks": checks,
        "notes": notes_list,
    }


# ---------------------------------------------------------------------------
# 2. Release Metadata Generation
# ---------------------------------------------------------------------------

def generate_release_metadata(
    lines: List[str],
    pattern_analysis: Dict[str, Any],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Generate artist-editable release metadata from the structural analysis.

    Returns
    -------
    dict with keys:
        mood_tags         – list of suggested mood tags
        genre_hints       – list of genre suggestions (starting points)
        structural_summary – plain-language description of the piece's structure
        length_category   – "short", "standard", "long", "extended"
        suggested_title_words – prominent thematic words that might appear in a title
        metadata_note     – ethical reminder about metadata usage
    """
    emotional_arc = pattern_analysis.get("emotional_arc", {})
    arc_dir = emotional_arc.get("arc_direction", "flat")
    form_type = art_genome.get("form_type", "unknown")
    structure = pattern_analysis.get("structure", {})

    # Mood tags
    mood_tags = list(_MOOD_TAGS.get(arc_dir, ["expressive"]))

    # Add refinements based on valence
    mean_valence = float(emotional_arc.get("mean_valence", 0.0))
    if mean_valence > 0.2:
        mood_tags = [t for t in mood_tags if "dark" not in t.lower()] + ["warm"]
    elif mean_valence < -0.2:
        mood_tags = [t for t in mood_tags if "uplift" not in t.lower()] + ["raw"]

    # Genre hints from form
    genre_hints = list(_FORM_TO_GENRE.get(form_type, _FORM_TO_GENRE["unknown"]))

    # Structural summary
    n = len(lines)
    refrains = structure.get("refrains", [])
    refrain_note = f" with {len(refrains)} refrain(s)" if refrains else ""
    structural_summary = (
        f"{n}-line {form_type}{refrain_note}, "
        f"{arc_dir} emotional arc, "
        f"rhyme density {art_genome.get('rhyme_density', 0.0):.2f}."
    )

    # Length category
    if n <= 4:
        length_category = "short"
    elif n <= 12:
        length_category = "standard"
    elif n <= 24:
        length_category = "long"
    else:
        length_category = "extended"

    # Prominent thematic words (non-stop, non-function, high frequency)
    from collections import Counter
    _STOP: frozenset = frozenset({
        "a", "an", "the", "in", "on", "at", "of", "to", "for", "and", "but",
        "or", "is", "was", "be", "by", "do", "did", "has", "had", "it", "its",
        "my", "no", "not", "so", "us", "we", "as", "if", "all", "with",
        "you", "your", "they", "them", "that", "this", "from", "are", "were",
        "will", "been", "have", "just", "into", "up", "out", "can", "me",
        "him", "her", "his", "she", "he", "i",
    })
    all_words = [w for l in lines for w in _words(l) if w not in _STOP and len(w) > 3]
    top_words = [w for w, _ in Counter(all_words).most_common(6)]

    return {
        "mood_tags": mood_tags,
        "genre_hints": genre_hints,
        "structural_summary": structural_summary,
        "length_category": length_category,
        "suggested_title_words": top_words,
        "metadata_note": (
            "These tags are starting points for the artist to edit, not algorithmic labels. "
            "Metadata serves findability — not platform ranking."
        ),
    }


# ---------------------------------------------------------------------------
# 3. Listener Journey Map
# ---------------------------------------------------------------------------

def calculate_listener_journey(
    lines: List[str],
    pattern_analysis: Dict[str, Any],
) -> dict:
    """
    Convert the emotional arc into a listener experience narrative —
    describing what a listener might feel as the piece unfolds.

    Returns
    -------
    dict with keys:
        journey_stages   – list of {lines_range, emotional_state, narrative} dicts
        overall_journey  – one-sentence summary of the full listener experience
        intimacy_level   – "private", "shared", "universal"
    """
    emotional_arc = pattern_analysis.get("emotional_arc", {})
    line_scores: List[float] = emotional_arc.get("line_scores", [])
    arc_dir = emotional_arc.get("arc_direction", "flat")

    if not line_scores or not lines:
        return {
            "journey_stages": [],
            "overall_journey": "No emotional data to map.",
            "intimacy_level": "unknown",
        }

    # Split into thirds for journey stages
    n = len(lines)
    third = max(n // 3, 1)
    stages = []

    def _stage_narrative(avg_score: float, position: str) -> str:
        if avg_score > 0.2:
            register = "emotionally open, warm"
        elif avg_score < -0.2:
            register = "emotionally heavy, searching"
        else:
            register = "emotionally neutral, observational"
        return f"The listener is in {register} territory at the {position} of the piece."

    for stage_idx, (start, label) in enumerate(
        [(0, "opening"), (third, "middle"), (third * 2, "closing")]
    ):
        end = min(start + third, n)
        if start >= n:
            break
        stage_lines = lines[start:end]
        stage_scores = line_scores[start:end]
        avg = sum(stage_scores) / max(len(stage_scores), 1)
        stages.append({
            "lines_range": f"lines {start + 1}–{end}",
            "line_count": len(stage_lines),
            "average_valence": round(avg, 4),
            "emotional_state": (
                "positive" if avg > 0.1 else "negative" if avg < -0.1 else "neutral"
            ),
            "narrative": _stage_narrative(avg, label),
        })

    # Overall journey
    journey_map = {
        "ascending": "The listener is taken from weight toward light — a journey of emergence.",
        "descending": "The listener travels from brightness into depth — an inward journey.",
        "oscillating": "The listener moves between emotional states — held in complexity.",
        "flat": "The listener inhabits a sustained emotional space — immersive and consistent.",
    }
    overall_journey = journey_map.get(arc_dir, "A unique emotional journey.")

    # Intimacy: how personal/universal is the language?
    first_person_lines = sum(
        1 for l in lines if _words(l) and _words(l)[0] == "i"
    )
    first_person_ratio = first_person_lines / max(n, 1)
    if first_person_ratio > 0.5:
        intimacy = "private"  # deeply personal "I" statements
    elif first_person_ratio > 0.2:
        intimacy = "shared"   # some personal + some universal
    else:
        intimacy = "universal"  # observational, outward-facing

    return {
        "journey_stages": stages,
        "overall_journey": overall_journey,
        "intimacy_level": intimacy,
    }


# ---------------------------------------------------------------------------
# 4. Format Suitability
# ---------------------------------------------------------------------------

def detect_format_suitability(
    lines: List[str],
    pattern_analysis: Dict[str, Any],
) -> dict:
    """
    Assess which release format this piece most naturally suits.

    Returns
    -------
    dict with keys:
        primary_format    – "single", "EP track", "album track", "interlude"
        format_score      – {format: score} dict
        format_notes      – plain-language guidance
    """
    n = len(lines)
    structure = pattern_analysis.get("structure", {})
    rep_count = structure.get("repetition_count", 0)
    refrains = structure.get("refrains", [])
    arc_dir = pattern_analysis.get("emotional_arc", {}).get("arc_direction", "flat")

    scores: Dict[str, float] = {
        "single": 0.0,
        "EP track": 0.0,
        "album track": 0.0,
        "interlude": 0.0,
    }

    # Singles: 8–16 lines, has a refrain, strong emotional arc
    if 8 <= n <= 16 and refrains:
        scores["single"] += 0.4
    if arc_dir in ("ascending", "descending"):
        scores["single"] += 0.2
    if rep_count >= 1:
        scores["single"] += 0.1

    # EP tracks: moderate length, some complexity
    if 6 <= n <= 20:
        scores["EP track"] += 0.3
    if arc_dir == "oscillating":
        scores["EP track"] += 0.2

    # Album tracks: any length, more narrative/complex
    if n > 12:
        scores["album track"] += 0.3
    if arc_dir in ("oscillating", "descending"):
        scores["album track"] += 0.2
    scores["album track"] += 0.1  # any piece can be an album track

    # Interlude: very short, flat or minimal
    if n <= 4:
        scores["interlude"] += 0.4
    if arc_dir == "flat":
        scores["interlude"] += 0.2

    # Normalise
    total = sum(scores.values()) or 1.0
    scores = {k: round(v / total, 4) for k, v in scores.items()}
    primary = max(scores, key=lambda k: scores[k])

    format_notes = [
        f"This piece most naturally suits a {primary} context.",
        "Format is never a constraint — these are structural observations only.",
        "The artist decides where and how this piece lives.",
    ]

    return {
        "primary_format": primary,
        "format_scores": scores,
        "format_notes": format_notes,
    }


# ---------------------------------------------------------------------------
# 5. Artist Statement Prompts
# ---------------------------------------------------------------------------

def build_artist_statement_prompts(
    art_genome: Dict[str, Any],
    existential_data: Dict[str, Any],
) -> dict:
    """
    Generate reflective questions to help the artist articulate their intent
    for press releases, liner notes, or platform bios.

    Returns
    -------
    dict with keys:
        core_prompts    – universal questions for any artist
        tailored_prompts – questions derived from this specific piece's analysis
        note            – framing note
    """
    core_prompts = [
        "What was happening in your life when you made this?",
        "What did you most want a listener to feel?",
        "What surprised you about this piece as it emerged?",
        "Who did you make this for — including yourself?",
        "What would you want someone to carry away from it ten years from now?",
    ]

    tailored_prompts = []
    emotional_arc = art_genome.get("emotional_arc", {})
    arc_dir = emotional_arc.get("arc_direction", "flat")
    creation_reason = existential_data.get("creation_reason", {})
    primary_reason = creation_reason.get("primary_reason", "expression")
    form_type = art_genome.get("form_type", "unknown")
    creative_risk = float(art_genome.get("creative_risk_index", 0.0))

    if arc_dir == "ascending":
        tailored_prompts.append(
            "The piece moves toward light — was that the destination, or did you find it in the writing?"
        )
    elif arc_dir == "descending":
        tailored_prompts.append(
            "The piece descends emotionally — was that honest, or was it difficult to write that way?"
        )

    if primary_reason == "catharsis":
        tailored_prompts.append(
            "This reads like a release — did writing it change something for you?"
        )
    elif primary_reason == "testimony":
        tailored_prompts.append(
            "This feels like bearing witness — whose story does it carry?"
        )
    elif primary_reason == "protest":
        tailored_prompts.append(
            "The piece has resistance in it — what are you refusing to accept?"
        )
    elif primary_reason == "connection":
        tailored_prompts.append(
            "The piece reaches toward others — who are you reaching for?"
        )

    if creative_risk > 0.4:
        tailored_prompts.append(
            "You broke some rules here — was that conscious, or did the art demand it?"
        )

    if form_type not in ("unknown", "free verse"):
        tailored_prompts.append(
            f"You chose (or landed in) a {form_type} form — "
            "was structure something you sought or something you noticed afterwards?"
        )

    return {
        "core_prompts": core_prompts,
        "tailored_prompts": tailored_prompts,
        "note": (
            "These prompts belong to the artist — for liner notes, interviews, "
            "or just private reflection. They carry no obligation."
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def flow(
    text: str,
    pattern_analysis: Dict[str, Any],
    art_genome: Dict[str, Any],
    existential_data: Dict[str, Any],
) -> dict:
    """
    Full KalaFlow distribution intelligence.

    Parameters
    ----------
    text              : original multi-line text
    pattern_analysis  : output of kalacore.pattern_engine.analyze()
    art_genome        : output of kalacore.art_genome.ArtGenome.to_dict()
    existential_data  : output of kalacore.existential.analyze_existential()

    Returns
    -------
    dict with keys:
        readiness, metadata, listener_journey, format_suitability,
        artist_statement_prompts
    """
    raw_lines = text.splitlines()
    lines = [l for l in raw_lines if l.strip()]

    if not lines:
        return {
            "readiness": {},
            "metadata": {},
            "listener_journey": {},
            "format_suitability": {},
            "artist_statement_prompts": {},
        }

    return {
        "readiness": assess_distribution_readiness(lines, pattern_analysis),
        "metadata": generate_release_metadata(lines, pattern_analysis, art_genome),
        "listener_journey": calculate_listener_journey(lines, pattern_analysis),
        "format_suitability": detect_format_suitability(lines, pattern_analysis),
        "artist_statement_prompts": build_artist_statement_prompts(
            art_genome, existential_data
        ),
    }

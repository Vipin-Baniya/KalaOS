"""
KalaOS Existential Layer  (Phase 1 – Existential + Phase 9 – Deep Features)
-----------------------------------------------------------------------------
Detects the *why* behind a piece of art — not just what it contains.

Functions
---------
detect_survival_markers   – words/patterns suggesting art made under
                            emotional or existential necessity
map_emotional_necessity   – intensity and specificity of emotional need
infer_creation_reason     – heuristic "why this was created" label
detect_negative_space     – gaps, silences, and short pauses as meaning
                            (Phase 9 – Negative Space Intelligence)
score_human_irreducibility – zones where algorithmic analysis cannot explain
                            the artistic choice (Phase 9 – Human
                            Irreducibility Index)

All functions are pure and stateless — no external dependencies required.
"""

import re
from typing import List, Dict, Any

from kalacore.pattern_engine import _normalise, _words  # reuse helpers


# ---------------------------------------------------------------------------
# Curated word sets
# ---------------------------------------------------------------------------

# Survival-level emotional markers — language used when the art is a life-raft
_SURVIVAL_WORDS: frozenset = frozenset({
    "survive", "surviving", "survival", "fight", "fighting", "breathe",
    "breathing", "bleed", "bleeding", "broken", "breaking", "shatter",
    "shattering", "drown", "drowning", "scream", "screaming", "silent",
    "silence", "alone", "abandoned", "betrayed", "betrayal", "lost",
    "losing", "lose", "hollow", "numb", "numbing", "fade", "fading",
    "disappear", "disappearing", "invisible", "unseen", "unheard",
    "nobody", "nothing", "worthless", "helpless", "hopeless", "trapped",
    "escape", "escaping", "release", "releasing", "free", "freedom",
    "rescue", "save", "saving", "hold", "holding", "carry", "carrying",
    "burden", "weight", "heavy", "shaking", "trembling", "crumbling",
    "falling", "fallen", "rise", "rising", "endure", "enduring",
})

# Emotional necessity indicators — specific, raw, personal language
_NECESSITY_WORDS: frozenset = frozenset({
    "must", "need", "needed", "needing", "have to", "cannot stop",
    "can not stop", "wont stop", "will not stop", "keep", "keeping",
    "again", "still", "always", "never", "forever", "every time",
    "every night", "every day", "everywhere", "cannot forget",
    "can not forget", "remember", "remembering", "haunts", "haunting",
    "won't leave", "stays", "stays with", "lived", "living through",
    "going through", "been through", "survived", "made it",
    "this is", "i am", "i was", "i will", "i need", "i must",
})

# Creation-reason archetypes mapped to keyword clusters
_CREATION_ARCHETYPES: Dict[str, frozenset] = {
    "catharsis": frozenset({
        "release", "let go", "cry", "tears", "sob", "pour", "flood",
        "overflow", "explode", "burst", "vent", "feel", "feeling",
    }),
    "testimony": frozenset({
        "witness", "seen", "happened", "true", "truth", "real", "story",
        "tell", "told", "say", "said", "speak", "spoke", "voice", "record",
        "remember", "history", "was there", "i saw",
    }),
    "survival": frozenset({
        "survive", "endure", "live", "breathe", "hold on", "keep going",
        "make it", "get through", "still here", "still standing",
    }),
    "connection": frozenset({
        "you", "yours", "us", "we", "together", "share", "find",
        "someone", "anyone", "everyone", "who knows", "who feels",
        "not alone", "same", "understand", "heard",
    }),
    "protest": frozenset({
        "fight", "resist", "refuse", "no", "enough", "change", "break",
        "system", "power", "silence them", "they", "won't be silenced",
        "stand up", "rise up",
    }),
    "wonder": frozenset({
        "beautiful", "miracle", "wow", "imagine", "dream", "light",
        "glowing", "golden", "magic", "mystery", "beyond", "vast",
        "endless", "stars", "cosmos", "universe",
    }),
}


# ---------------------------------------------------------------------------
# 1. Survival-Driven Art Detection
# ---------------------------------------------------------------------------

def detect_survival_markers(lines: List[str]) -> dict:
    """
    Detect language patterns that suggest this art was made under emotional
    or existential pressure — a life-raft rather than performance.

    Returns
    -------
    dict with keys:
        survival_word_count   – total occurrences of survival-register words
        survival_line_ratio   – proportion of lines containing ≥1 such word
        is_survival_driven    – True when ratio ≥ 0.3 or count ≥ 5
        survival_lines        – list of lines that contain survival markers
    """
    count = 0
    survival_lines: List[str] = []

    for line in lines:
        ws = _words(line)
        hits = sum(1 for w in ws if w in _SURVIVAL_WORDS)
        if hits:
            count += hits
            survival_lines.append(line)

    ratio = round(len(survival_lines) / max(len(lines), 1), 4)
    is_survival = ratio >= 0.3 or count >= 5

    return {
        "survival_word_count": count,
        "survival_line_ratio": ratio,
        "is_survival_driven": is_survival,
        "survival_lines": survival_lines,
    }


# ---------------------------------------------------------------------------
# 2. Emotional Necessity Mapping
# ---------------------------------------------------------------------------

def map_emotional_necessity(lines: List[str]) -> dict:
    """
    Measure the *intensity* and *specificity* of emotional necessity.

    Intensity  – proportion of lines with necessity-register language.
    Specificity – proportion of first-person singular statements
                  (highly personal = more necessary).

    Returns
    -------
    dict with keys:
        necessity_intensity   – [0,1]
        necessity_specificity – [0,1]
        necessity_score       – combined [0,1]
        necessity_lines       – lines with necessity markers
    """
    necessity_lines: List[str] = []
    first_person_count = 0

    for line in lines:
        ws = _words(line)
        line_text = " ".join(ws)
        # Check word-level necessity markers first (fast path)
        has_necessity = any(w in _NECESSITY_WORDS for w in ws)
        # Only check multi-word phrases when no single-word match was found
        if not has_necessity:
            has_necessity = any(phrase in line_text for phrase in _NECESSITY_WORDS if " " in phrase)
        if has_necessity:
            necessity_lines.append(line)
        # First-person: line starts with "i"
        if ws and ws[0] == "i":
            first_person_count += 1

    intensity = round(len(necessity_lines) / max(len(lines), 1), 4)
    specificity = round(first_person_count / max(len(lines), 1), 4)
    necessity_score = round((intensity * 0.6) + (specificity * 0.4), 4)

    return {
        "necessity_intensity": intensity,
        "necessity_specificity": specificity,
        "necessity_score": necessity_score,
        "necessity_lines": necessity_lines,
    }


# ---------------------------------------------------------------------------
# 3. "Why This Was Created" Inference
# ---------------------------------------------------------------------------

def infer_creation_reason(lines: List[str]) -> dict:
    """
    Infer the most likely reason this piece was created using archetype
    keyword matching.

    Returns the primary archetype, its confidence, and all archetype scores.

    Archetypes: catharsis, testimony, survival, connection, protest, wonder.
    """
    all_words_set: frozenset = frozenset(
        w for line in lines for w in _words(line)
    )
    # Also check full text for multi-word phrases
    full_text = " ".join(_normalise(l) for l in lines)

    scores: Dict[str, float] = {}
    for archetype, keywords in _CREATION_ARCHETYPES.items():
        single_word_hits = len(all_words_set & keywords)
        # Multi-word phrase hits
        phrase_hits = sum(1 for kw in keywords if " " in kw and kw in full_text)
        raw = single_word_hits + phrase_hits * 2  # phrases weighted more
        scores[archetype] = raw

    total = sum(scores.values()) or 1
    normalised = {k: round(v / total, 4) for k, v in scores.items()}

    primary = max(normalised, key=lambda k: normalised[k])
    confidence = normalised[primary]

    # If nothing stands out, label as "expression"
    if confidence < 0.25:
        primary = "expression"
        confidence = 0.0

    return {
        "primary_reason": primary,
        "confidence": confidence,
        "archetype_scores": normalised,
    }


# ---------------------------------------------------------------------------
# 4. Negative Space Intelligence  (Phase 9)
# ---------------------------------------------------------------------------

def detect_negative_space(lines: List[str], raw_lines: List[str]) -> dict:
    """
    Detect silence, gaps, and pauses as artistic meaning.

    Parameters
    ----------
    lines     : non-blank lines (from pattern_engine.analyze)
    raw_lines : all lines including blanks (text.splitlines())

    Returns
    -------
    dict with keys:
        blank_line_count   – total blank/empty lines
        gap_positions      – indices in raw_lines where blanks appear
        gap_ratio          – blanks / total raw lines
        has_negative_space – True when gap_ratio ≥ 0.1
        trailing_silence   – True when the piece ends with ≥1 blank line
        internal_gaps      – list of (before_line, after_line) tuples for
                             internal (non-trailing, non-leading) blanks
    """
    blank_positions = [i for i, l in enumerate(raw_lines) if not l.strip()]
    total = max(len(raw_lines), 1)

    # Internal gaps: not at start or end
    internal_gaps = []
    for pos in blank_positions:
        if 0 < pos < len(raw_lines) - 1:
            before = raw_lines[pos - 1].strip()
            after = raw_lines[pos + 1].strip()
            if before and after:
                internal_gaps.append({"before": before, "after": after, "position": pos})

    trailing_silence = bool(raw_lines) and not raw_lines[-1].strip()

    return {
        "blank_line_count": len(blank_positions),
        "gap_positions": blank_positions,
        "gap_ratio": round(len(blank_positions) / total, 4),
        "has_negative_space": len(blank_positions) / total >= 0.1,
        "trailing_silence": trailing_silence,
        "internal_gaps": internal_gaps,
    }


# ---------------------------------------------------------------------------
# 5. Human Irreducibility Index  (Phase 9)
# ---------------------------------------------------------------------------

def score_human_irreducibility(
    lines: List[str],
    analysis: Dict[str, Any],
) -> dict:
    """
    Score the zones where algorithmic analysis fails to fully account for
    the artistic choice — the Human Irreducibility Index.

    A line scores "irreducible" when it:
      - Has no detectable end-rhyme, internal rhyme, or palindrome pattern
      - Has no repetition (unique in the piece)
      - Is NOT in the known refrain list
      - Does NOT fit the dominant meter (syllable outlier > 1 std-dev)

    Returns
    -------
    dict with keys:
        irreducible_lines  – lines that defy pattern explanation
        irreducibility_index – [0,1]: proportion of lines that are irreducible
        explanation        – plain-language description
    """
    from collections import Counter
    import math

    syllables = analysis.get("syllables", [])
    rhyme_data = analysis.get("rhymes", {})
    palindrome_data = analysis.get("palindrome", {})
    structure = analysis.get("structure", {})

    # Lines that participate in end-rhyme groups
    rhyming_indices: set = set()
    for indices in rhyme_data.get("end_rhyme_groups", {}).values():
        rhyming_indices.update(indices)

    # Lines with internal rhyme
    internal_rhyme_lines = {
        r["line"] for r in rhyme_data.get("internal_rhymes", [])
        if r.get("has_internal_rhyme")
    }

    # Palindrome lines
    pal_lines = {
        l["line"] for l in palindrome_data.get("lines", [])
        if l.get("is_full_palindrome") or l.get("partial_palindromes")
    }

    # Refrains
    refrains = set(structure.get("refrains", []))
    repeated = set(structure.get("repeated_lines", {}).keys())

    # Syllable outliers
    syl_totals = [s.get("total_syllables", 0) for s in syllables]
    if len(syl_totals) > 1:
        mean = sum(syl_totals) / len(syl_totals)
        variance = sum((x - mean) ** 2 for x in syl_totals) / len(syl_totals)
        std = math.sqrt(variance)
    else:
        mean, std = 0.0, 0.0

    irreducible: List[str] = []
    for i, line in enumerate(lines):
        norm = _normalise(line)
        # Exclude if it has rhyme, palindrome, or repetition patterns
        if i in rhyming_indices:
            continue
        if line in internal_rhyme_lines:
            continue
        if line in pal_lines:
            continue
        if norm in refrains or norm in repeated:
            continue
        # Exclude if it fits the dominant meter (within 1 std-dev)
        if std > 0 and i < len(syl_totals):
            if abs(syl_totals[i] - mean) <= std:
                continue
        # This line defies algorithmic explanation
        irreducible.append(line)

    index = round(len(irreducible) / max(len(lines), 1), 4)
    if index >= 0.5:
        explanation = "More than half this piece exists beyond pattern — deeply human."
    elif index >= 0.25:
        explanation = "Significant portions resist algorithmic explanation — the art exceeds its structure."
    elif index > 0:
        explanation = "Some lines defy pattern — intentional creative departure."
    else:
        explanation = "Patterns account for most of this piece — structure is the art."

    return {
        "irreducible_lines": irreducible,
        "irreducibility_index": index,
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_existential(text: str, pattern_analysis: Dict[str, Any]) -> dict:
    """
    Full existential analysis of a piece of art.

    Parameters
    ----------
    text             : original text (may contain blank lines)
    pattern_analysis : output of kalacore.pattern_engine.analyze()

    Returns
    -------
    dict with keys:
        survival, emotional_necessity, creation_reason,
        negative_space, human_irreducibility
    """
    raw_lines = text.splitlines()
    lines = [l for l in raw_lines if l.strip()]

    if not lines:
        return {
            "survival": {},
            "emotional_necessity": {},
            "creation_reason": {},
            "negative_space": {},
            "human_irreducibility": {},
        }

    return {
        "survival": detect_survival_markers(lines),
        "emotional_necessity": map_emotional_necessity(lines),
        "creation_reason": infer_creation_reason(lines),
        "negative_space": detect_negative_space(lines, raw_lines),
        "human_irreducibility": score_human_irreducibility(lines, pattern_analysis),
    }

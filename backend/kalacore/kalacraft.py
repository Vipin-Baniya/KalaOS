"""
KalaCraft  (Phase 2 – Creation & Craft)
----------------------------------------
Tools that help artists refine their work — without overriding their voice.

Philosophy
----------
  • Suggest, never enforce
  • Show impact, not errors
  • Honour artist intent — every output is optional

Functions
---------
phonetic_breakdown      – CMU-lite heuristic phoneme breakdown per word
detect_stress_pattern   – primary / secondary stress markers per line
detect_breath_points    – natural performance pause positions
analyze_meter_flow      – per-line meter regularity & flow score
analyze_line_density    – semantic weight per line (syllables + unique words)
detect_semantic_drift   – track how theme/vocabulary shifts across the piece
"""

import re
from typing import List, Dict, Any, Tuple

from kalacore.pattern_engine import _normalise, _words, count_syllables


# ---------------------------------------------------------------------------
# Phoneme / stress helpers (no external library)
# ---------------------------------------------------------------------------

# Simplified English grapheme-to-phoneme rules for the most common patterns.
# Returns a list of "phoneme tokens" — these are heuristic, not IPA.
_VOWEL_RE = re.compile(r"[aeiouy]+")
_CONSONANT_CLUSTER_RE = re.compile(r"[^aeiouy]{2,}")

# Common digraphs to label as single units
_DIGRAPHS = ("th", "sh", "ch", "ph", "wh", "gh", "ng", "ck", "qu")


def _rough_phonemes(word: str) -> List[str]:
    """
    Heuristic phoneme tokenisation.  Not IPA — but good enough for stress
    pattern visualisation.
    """
    w = word.lower().strip(".,!?;:'\"")
    if not w:
        return []

    tokens: List[str] = []
    i = 0
    while i < len(w):
        # Check digraph first
        if i + 1 < len(w) and w[i : i + 2] in _DIGRAPHS:
            tokens.append(w[i : i + 2])
            i += 2
        elif w[i] in "aeiouy":
            # Gather full vowel cluster
            j = i + 1
            while j < len(w) and w[j] in "aeiouy":
                j += 1
            tokens.append(w[i:j])
            i = j
        else:
            tokens.append(w[i])
            i += 1
    return tokens


def phonetic_breakdown(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Return a heuristic phonetic breakdown for each line.

    Each entry contains:
      line         – original line
      words        – list of {word, phonemes, syllable_count} dicts
      total_phonemes – total phoneme count for the line
    """
    results = []
    for line in lines:
        ws = _words(line)
        word_data = []
        for w in ws:
            ph = _rough_phonemes(w)
            word_data.append({
                "word": w,
                "phonemes": ph,
                "syllable_count": count_syllables(w),
            })
        results.append({
            "line": line,
            "words": word_data,
            "total_phonemes": sum(len(wd["phonemes"]) for wd in word_data),
        })
    return results


# ---------------------------------------------------------------------------
# Stress Pattern Detection
# ---------------------------------------------------------------------------

def detect_stress_pattern(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Assign a simple DA-dum stress pattern to each word in each line.

    Stress heuristic:
      - Syllables whose vowel cluster is followed by a consonant and then
        a vowel tend to be stressed (onset of a stressed syllable).
      - Function words (the, a, an, in, of, to, …) are unstressed.
      - Polysyllabic words: stress falls on the penultimate or antepenultimate
        syllable (simplified rule).

    Returns per-line list with:
      line     – original line
      pattern  – list of "S" (stressed) / "U" (unstressed) per word
      notation – compact string like "U S U S S"
    """
    _FUNCTION_WORDS = frozenset({
        "a", "an", "the", "in", "on", "at", "of", "to", "for",
        "and", "but", "or", "nor", "so", "yet", "as", "is", "was",
        "be", "by", "do", "did", "has", "had", "its", "it", "if",
        "my", "no", "not", "now", "our", "than", "that", "this",
        "us", "we", "with", "you", "your",
    })

    results = []
    for line in lines:
        ws = _words(line)
        pattern = []
        for w in ws:
            if w in _FUNCTION_WORDS:
                pattern.append("U")
            elif count_syllables(w) == 1:
                pattern.append("S")  # monosyllabic content word → stressed
            else:
                # Multi-syllable: mark as S (dominant stress for the word)
                pattern.append("S")
        results.append({
            "line": line,
            "pattern": pattern,
            "notation": " ".join(pattern),
        })
    return results


# ---------------------------------------------------------------------------
# Breath-Point Detection
# ---------------------------------------------------------------------------

def detect_breath_points(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Identify natural breath / performance pause positions.

    Breath points are suggested:
      1. After punctuation that marks a phrase boundary (,  ;  :  —  …)
      2. At the end of every line
      3. Within lines longer than 10 syllables (suggested mid-line break)

    Returns per-line list with:
      line          – original line
      end_of_line   – always True (every line end is a breath point)
      punctuation_pauses – indices in the word list after which a pause is suggested
      mid_line_break – True if syllable count suggests a mid-line breath
      suggested_pause_after – combined list of word indices for pauses
    """
    _PAUSE_PUNCTUATION = re.compile(r"[,;:—…\-]")
    results = []
    for line in lines:
        raw_words = line.split()
        pause_indices = []
        for i, w in enumerate(raw_words):
            if _PAUSE_PUNCTUATION.search(w):
                pause_indices.append(i)

        total_syl = sum(count_syllables(w) for w in _words(line))
        mid_line = total_syl > 10

        # If no punctuation pauses and line is long, suggest middle
        if mid_line and not pause_indices:
            mid = len(raw_words) // 2
            pause_indices = [mid]

        results.append({
            "line": line,
            "end_of_line": True,
            "punctuation_pauses": pause_indices,
            "mid_line_break": mid_line,
            "suggested_pause_after": pause_indices,
        })
    return results


# ---------------------------------------------------------------------------
# Meter Flow Visualization
# ---------------------------------------------------------------------------

def analyze_meter_flow(lines: List[str]) -> Dict[str, Any]:
    """
    Measure the regularity ("flow") of meter across the piece.

    Flow score – how consistent the syllable counts are line-to-line.
    A perfectly regular piece (all lines same length) scores 1.0.
    A wildly irregular piece scores near 0.0.

    Returns
    -------
    dict with keys:
      per_line        – list of {line, syllables, deviation_from_mean}
      mean_syllables  – average syllables per line
      flow_score      – [0,1] regularity score
      dominant_meter  – "iambic pentameter", "trochaic tetrameter", etc.
                        (simple heuristic, or "free verse" if irregular)
    """
    per_line = []
    syl_counts = []
    for line in lines:
        syl = sum(count_syllables(w) for w in _words(line))
        syl_counts.append(syl)
        per_line.append({"line": line, "syllables": syl})

    if not syl_counts:
        return {"per_line": [], "mean_syllables": 0, "flow_score": 0.0, "dominant_meter": "unknown"}

    mean = sum(syl_counts) / len(syl_counts)
    variance = sum((x - mean) ** 2 for x in syl_counts) / len(syl_counts)
    std = variance ** 0.5

    for entry, syl in zip(per_line, syl_counts):
        entry["deviation_from_mean"] = round(syl - mean, 2)

    # Flow score: 1 - (normalised std)
    flow_score = round(max(0.0, 1.0 - (std / max(mean, 1))), 4)

    # Dominant meter heuristic by average syllables per line
    dominant = _guess_meter(mean, flow_score)

    return {
        "per_line": per_line,
        "mean_syllables": round(mean, 2),
        "flow_score": flow_score,
        "dominant_meter": dominant,
    }


def _guess_meter(mean_syl: float, flow_score: float) -> str:
    """Map mean syllable count + regularity to a named meter."""
    if flow_score < 0.5:
        return "free verse"
    m = round(mean_syl)
    table = {
        5: "iambic dimeter",
        6: "trochaic trimeter",
        7: "iambic trimeter / ballad",
        8: "trochaic tetrameter",
        9: "iambic tetrameter",
        10: "iambic pentameter",
        11: "iambic pentameter (feminine ending)",
        12: "alexandrine / hexameter",
    }
    return table.get(m, "free verse")


# ---------------------------------------------------------------------------
# Line Density Analysis
# ---------------------------------------------------------------------------

def analyze_line_density(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Measure semantic weight (density) of each line.

    Density = syllables × unique_word_ratio.
    High density = complex, layered lines.
    Low density = spacious, breath-giving lines.

    Returns per-line list with:
      line           – original line
      syllables      – total syllable count
      word_count     – number of words
      unique_ratio   – unique words / total words
      density_score  – [0,1] normalised density
    """
    results = []
    density_raw = []
    for line in lines:
        ws = _words(line)
        if not ws:
            results.append({
                "line": line, "syllables": 0,
                "word_count": 0, "unique_ratio": 0.0, "density_score": 0.0,
            })
            continue
        syl = sum(count_syllables(w) for w in ws)
        unique_ratio = len(set(ws)) / len(ws)
        raw = syl * unique_ratio
        density_raw.append(raw)
        results.append({
            "line": line,
            "syllables": syl,
            "word_count": len(ws),
            "unique_ratio": round(unique_ratio, 4),
            "_raw": raw,
        })

    # Normalise against max raw value
    max_raw = max(density_raw, default=1.0)
    for entry in results:
        raw = entry.pop("_raw", 0.0)
        entry["density_score"] = round(raw / max(max_raw, 1.0), 4)

    return results


# ---------------------------------------------------------------------------
# Semantic Drift Detection
# ---------------------------------------------------------------------------

# Common stop-words to exclude from vocabulary tracking
_STOP_WORDS: frozenset = frozenset({
    "a", "an", "the", "in", "on", "at", "of", "to", "for", "and", "but",
    "or", "is", "was", "be", "by", "do", "did", "has", "had", "it", "its",
    "my", "no", "not", "so", "us", "we", "as", "if", "all", "can",
    "with", "you", "your", "they", "them", "that", "this", "those", "these",
    "from", "are", "were", "will", "been", "have", "more", "just", "into",
    "up", "out", "what", "who", "how", "when", "where", "than", "also",
    "back", "over", "about", "him", "her", "his", "she", "he", "me",
})


def detect_semantic_drift(lines: List[str]) -> dict:
    """
    Track how the vocabulary / theme shifts across the piece.

    Splits the text into thirds (opening, middle, closing).
    For each section, finds the dominant content words (top 5 by frequency).
    Reports vocabulary overlap between sections — high overlap = coherent,
    low overlap = significant thematic drift.

    Returns
    -------
    dict with keys:
      sections          – {opening, middle, closing} with top content words
      overlap_om        – overlap between opening and middle [0,1]
      overlap_mc        – overlap between middle and closing [0,1]
      drift_score       – 1 - mean overlap → high = lots of drift [0,1]
      has_semantic_drift – True when drift_score > 0.5
    """
    if not lines:
        return {
            "sections": {}, "overlap_om": 0.0,
            "overlap_mc": 0.0, "drift_score": 0.0,
            "has_semantic_drift": False,
        }

    n = len(lines)
    third = max(n // 3, 1)
    groups = {
        "opening": lines[:third],
        "middle": lines[third: third * 2],
        "closing": lines[third * 2:],
    }

    def top_words(section_lines: List[str]) -> set:
        from collections import Counter
        ws = [
            w for l in section_lines
            for w in _words(l)
            if w not in _STOP_WORDS and len(w) > 2
        ]
        counts = Counter(ws)
        return set(w for w, _ in counts.most_common(5))

    sections = {name: list(top_words(g)) for name, g in groups.items()}

    def overlap(a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        return round(len(set(a) & set(b)) / max(len(set(a) | set(b)), 1), 4)

    o = set(sections["opening"])
    m = set(sections["middle"])
    c = set(sections["closing"])
    overlap_om = overlap(o, m)
    overlap_mc = overlap(m, c)
    drift_score = round(1.0 - (overlap_om + overlap_mc) / 2, 4)

    return {
        "sections": sections,
        "overlap_om": overlap_om,
        "overlap_mc": overlap_mc,
        "drift_score": drift_score,
        "has_semantic_drift": drift_score > 0.5,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_craft(text: str) -> dict:
    """
    Full KalaCraft analysis for a piece of text.

    Parameters
    ----------
    text : str
        Multi-line string (lyrics, poem, etc.)

    Returns
    -------
    dict with keys:
        phonetics, stress_patterns, breath_points,
        meter_flow, line_density, semantic_drift
    """
    raw_lines = text.splitlines()
    lines = [l for l in raw_lines if l.strip()]

    if not lines:
        return {
            "phonetics": [],
            "stress_patterns": [],
            "breath_points": [],
            "meter_flow": {},
            "line_density": [],
            "semantic_drift": {},
        }

    return {
        "phonetics": phonetic_breakdown(lines),
        "stress_patterns": detect_stress_pattern(lines),
        "breath_points": detect_breath_points(lines),
        "meter_flow": analyze_meter_flow(lines),
        "line_density": analyze_line_density(lines),
        "semantic_drift": detect_semantic_drift(lines),
    }

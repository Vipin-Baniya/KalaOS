"""
KalaSignal  (Phase 4 – Possibility Engine)
-------------------------------------------
Analyses the *resonance potential* of a piece of art without prescribing
how it should be changed.

Philosophy
----------
  Viral ≠ Loved ≠ Remembered — these are separate dimensions.
  KalaSignal shows all three, never conflating them.
  All analysis is private by default and never used for ranking.

Functions
---------
score_memorability     – structural hooks that make a piece stick
score_longevity        – depth indicators suggesting enduring meaning
score_emotional_access – how accessible the emotional register is
score_share_potential  – structural features that invite sharing
                         (clarity, brevity, resonant close)
separate_resonance     – the critical separation: viral / loved / remembered
explain_resonance      – plain-language, confidence-aware explanation

Public API
----------
analyze_signal(text, art_genome_dict) → full resonance dict
"""

import math
from typing import Any, Dict, List

from kalacore.pattern_engine import _words, _normalise, count_syllables


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _line_count(lines: List[str]) -> int:
    return len(lines)


def _avg_syllables(lines: List[str]) -> float:
    totals = [sum(count_syllables(w) for w in _words(l)) for l in lines]
    return sum(totals) / max(len(totals), 1)


# ---------------------------------------------------------------------------
# 1. Memorability Score
# ---------------------------------------------------------------------------

def score_memorability(
    lines: List[str],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Estimate how likely this piece is to be remembered.

    Key signals:
      - Refrain / repetition (refrains = hooks)
      - Rhyme density (rhyme aids recall)
      - Symmetry (mirror structure = satisfying)
      - Short, punchy lines (easier to hold in mind)
      - Emotional arc ends on a high note ("ascending")

    Returns
    -------
    dict with keys:
        score            – [0,1]
        signals          – dict of contributing signals and their weights
        strongest_signal – which factor contributes most
    """
    structure = art_genome.get("structure_analysis", {})
    rhyme_density = float(art_genome.get("rhyme_density", 0.0))
    symmetry = float(art_genome.get("symmetry_score", 0.0))
    emotional_arc = art_genome.get("emotional_arc", {})

    refrain_count = len(structure.get("refrains", []))
    repetition_count = int(structure.get("repetition_count", 0))

    # Refrain presence (hooks)
    refrain_score = min(refrain_count / 3.0, 1.0)  # 3 refrains = max

    # Rhyme aids recall
    rhyme_score = rhyme_density

    # Symmetry is satisfying
    symmetry_score = symmetry

    # Short lines are easier to remember
    avg_syl = _avg_syllables(lines)
    brevity_score = max(0.0, 1.0 - (avg_syl - 6) / 10.0) if avg_syl > 6 else 1.0
    brevity_score = min(brevity_score, 1.0)

    # Emotional arc ends strong
    arc_dir = emotional_arc.get("arc_direction", "flat")
    arc_boost = 0.8 if arc_dir == "ascending" else 0.5 if arc_dir == "flat" else 0.3

    signals = {
        "refrain_hooks": round(refrain_score, 4),
        "rhyme_density": round(rhyme_score, 4),
        "symmetry": round(symmetry_score, 4),
        "brevity": round(brevity_score, 4),
        "emotional_close": round(arc_boost, 4),
    }
    weights = {"refrain_hooks": 0.30, "rhyme_density": 0.25, "symmetry": 0.15,
               "brevity": 0.15, "emotional_close": 0.15}

    score = round(sum(signals[k] * weights[k] for k in signals), 4)
    strongest = max(signals, key=lambda k: signals[k] * weights[k])

    return {"score": score, "signals": signals, "strongest_signal": strongest}


# ---------------------------------------------------------------------------
# 2. Longevity Score
# ---------------------------------------------------------------------------

def score_longevity(
    lines: List[str],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Estimate enduring meaning — will this piece matter in 10 years?

    Key signals:
      - Structural complexity (depth rewards re-reading)
      - Human-irreducible zones (the unexplainable = timeless)
      - Cognitive load (challenge = sustained engagement)
      - Emotional arc has genuine movement (not flat)
      - Creative risk / improvisation (originality endures)

    Returns
    -------
    dict with keys:
        score            – [0,1]
        signals          – dict of contributing signals
        strongest_signal – leading contributor
    """
    complexity = float(art_genome.get("complexity_score", 0.0))
    cognitive_load = float(art_genome.get("cognitive_load", 0.0))
    creative_risk = float(art_genome.get("creative_risk_index", 0.0))
    irreducible_count = len(art_genome.get("human_irreducible_zones", []))
    emotional_arc = art_genome.get("emotional_arc", {})

    arc_dir = emotional_arc.get("arc_direction", "flat")
    arc_score = 1.0 if arc_dir in ("ascending", "descending", "oscillating") else 0.3

    irreducible_score = min(irreducible_count / max(_line_count(lines), 1), 1.0)

    signals = {
        "complexity": round(complexity, 4),
        "cognitive_load": round(cognitive_load, 4),
        "creative_risk": round(creative_risk, 4),
        "irreducibility": round(irreducible_score, 4),
        "emotional_movement": round(arc_score, 4),
    }
    weights = {"complexity": 0.25, "cognitive_load": 0.20, "creative_risk": 0.20,
               "irreducibility": 0.20, "emotional_movement": 0.15}

    score = round(sum(signals[k] * weights[k] for k in signals), 4)
    strongest = max(signals, key=lambda k: signals[k] * weights[k])

    return {"score": score, "signals": signals, "strongest_signal": strongest}


# ---------------------------------------------------------------------------
# 3. Emotional Accessibility Score
# ---------------------------------------------------------------------------

def score_emotional_access(
    lines: List[str],
    art_genome: Dict[str, Any],
) -> dict:
    """
    How emotionally accessible is this piece?

    A piece is accessible when:
      - It has clear emotional valence (not stuck near zero)
      - Cognitive load is moderate (too high = alienating)
      - Lines are not too long (readability)
      - Rhyme or repetition provides familiarity

    Returns
    -------
    dict with keys:
        score            – [0,1]
        signals          – dict of contributing signals
        strongest_signal – leading contributor
    """
    emotional_arc = art_genome.get("emotional_arc", {})
    cognitive_load = float(art_genome.get("cognitive_load", 0.0))
    rhyme_density = float(art_genome.get("rhyme_density", 0.0))

    mean_valence = abs(float(emotional_arc.get("mean_valence", 0.0)))
    valence_score = min(mean_valence * 5, 1.0)  # amplify small signals

    # Accessibility peaks at moderate cognitive load (~0.4), drops at extremes
    cog_access = 1.0 - abs(cognitive_load - 0.4) / 0.6
    cog_access = max(0.0, min(cog_access, 1.0))

    # Shorter average lines → more accessible
    avg_syl = _avg_syllables(lines)
    readability = max(0.0, 1.0 - (avg_syl - 5) / 10.0) if avg_syl > 5 else 1.0
    readability = min(readability, 1.0)

    signals = {
        "emotional_clarity": round(valence_score, 4),
        "cognitive_accessibility": round(cog_access, 4),
        "readability": round(readability, 4),
        "familiarity_through_rhyme": round(rhyme_density, 4),
    }
    weights = {"emotional_clarity": 0.35, "cognitive_accessibility": 0.25,
               "readability": 0.20, "familiarity_through_rhyme": 0.20}

    score = round(sum(signals[k] * weights[k] for k in signals), 4)
    strongest = max(signals, key=lambda k: signals[k] * weights[k])

    return {"score": score, "signals": signals, "strongest_signal": strongest}


# ---------------------------------------------------------------------------
# 4. Share Potential
# ---------------------------------------------------------------------------

def score_share_potential(
    lines: List[str],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Estimate structural features that invite sharing (NOT virality prediction).

    Sharing is invited by:
      - A strong, clear close (emotional arc ends decisively)
      - Concise overall length (not exhausting)
      - High rhyme density (quotable)
      - A recognisable form (sonnet, quatrain → cultural familiarity)
      - Moderate complexity (interesting but not alienating)

    Returns
    -------
    dict with keys:
        score            – [0,1]
        signals          – dict of contributing signals
        note             – ethical disclaimer
    """
    emotional_arc = art_genome.get("emotional_arc", {})
    rhyme_density = float(art_genome.get("rhyme_density", 0.0))
    complexity = float(art_genome.get("complexity_score", 0.0))
    form_type = art_genome.get("form_type", "unknown")

    arc_dir = emotional_arc.get("arc_direction", "flat")
    strong_close = 1.0 if arc_dir in ("ascending", "descending") else 0.4

    # Length: 4-16 lines is sweet spot for sharing
    n = _line_count(lines)
    length_score = 1.0 if 4 <= n <= 16 else max(0.0, 1.0 - abs(n - 10) / 20.0)

    # Recognised forms are more shareable
    recognised_forms = {"sonnet", "haiku", "quatrain", "couplet", "ballad stanza"}
    form_score = 0.8 if form_type in recognised_forms else 0.4

    # Optimal complexity for sharing ≈ 0.4
    complexity_fit = 1.0 - abs(complexity - 0.4) / 0.6
    complexity_fit = max(0.0, min(complexity_fit, 1.0))

    signals = {
        "strong_close": round(strong_close, 4),
        "length_fit": round(length_score, 4),
        "recognised_form": round(form_score, 4),
        "rhyme_quotability": round(rhyme_density, 4),
        "complexity_fit": round(complexity_fit, 4),
    }
    weights = {"strong_close": 0.30, "length_fit": 0.20, "recognised_form": 0.20,
               "rhyme_quotability": 0.15, "complexity_fit": 0.15}

    score = round(sum(signals[k] * weights[k] for k in signals), 4)

    return {
        "score": score,
        "signals": signals,
        "note": (
            "Share potential reflects structural invitation to sharing — "
            "not a prediction of virality. Viral ≠ Loved ≠ Remembered."
        ),
    }


# ---------------------------------------------------------------------------
# 5. Resonance Separation  (CRITICAL — Phase 4 philosophy)
# ---------------------------------------------------------------------------

def separate_resonance(
    memorability: dict,
    longevity: dict,
    emotional_access: dict,
    share_potential: dict,
) -> dict:
    """
    The critical KalaSignal output: keep the three resonance dimensions
    clearly separate and never blend them into a single score.

    Viral   ≈ share_potential (spreads fast, fades fast)
    Loved   ≈ emotional_access (felt deeply, personally)
    Remembered ≈ longevity (endures, deepens over time)

    Each dimension is independent.  A piece can be:
      Viral + not Loved + not Remembered (trend)
      Loved + not Viral + not Remembered (intimate)
      Remembered + not Loved + not Viral (classic)
      All three (rare, extraordinary)
      None of the three — and still be worth making.

    Returns a plain-language description for each dimension.
    """
    def _label(score: float) -> str:
        if score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "moderate"
        else:
            return "low"

    v = share_potential.get("score", 0.0)
    lo = emotional_access.get("score", 0.0)
    r = longevity.get("score", 0.0)

    return {
        "viral_potential": {"score": round(v, 4), "level": _label(v)},
        "loved_potential": {"score": round(lo, 4), "level": _label(lo)},
        "remembered_potential": {"score": round(r, 4), "level": _label(r)},
        "axiom": "Viral ≠ Loved ≠ Remembered — these are separate truths.",
        "note": (
            "No score here means this piece has no value. "
            "Art can be worth making even when all scores are low."
        ),
    }


# ---------------------------------------------------------------------------
# 6. Explainable Resonance
# ---------------------------------------------------------------------------

def explain_resonance(separation: dict) -> str:
    """
    Generate a plain-language, confidence-aware resonance explanation.
    Never tells the artist what to change — only illuminates what is.
    """
    parts = []

    v_level = separation["viral_potential"]["level"]
    lo_level = separation["loved_potential"]["level"]
    r_level = separation["remembered_potential"]["level"]

    # Loved (emotional access)
    if lo_level == "high":
        parts.append("The emotional register is open and accessible — it reaches out to the listener.")
    elif lo_level == "moderate":
        parts.append("There is genuine feeling here, though it may resonate more deeply with some listeners than others.")
    else:
        parts.append("The emotional channel is subtle or guarded — a deliberate choice in many traditions.")

    # Remembered (longevity)
    if r_level == "high":
        parts.append("The depth and originality here suggest this could endure beyond the moment.")
    elif r_level == "moderate":
        parts.append("There is enough complexity and risk that this piece may grow in meaning over time.")
    else:
        parts.append("The piece lives in the present — immediate rather than cumulative.")

    # Viral
    if v_level == "high":
        parts.append("Structurally, this piece invites sharing — though whether it spreads is never the measure of its worth.")
    elif v_level == "low":
        parts.append("This piece doesn't chase reach — a quiet art that asks for attention rather than momentum.")

    parts.append("All resonance data is private and never used for ranking or recommendation.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_signal(text: str, art_genome: Dict[str, Any]) -> dict:
    """
    Full KalaSignal resonance analysis.

    Parameters
    ----------
    text       : original multi-line text
    art_genome : output of art_genome.ArtGenome.to_dict()

    Returns
    -------
    dict with keys:
        memorability, longevity, emotional_access, share_potential,
        separation, explanation
    """
    raw_lines = text.splitlines()
    lines = [l for l in raw_lines if l.strip()]

    if not lines:
        return {
            "memorability": {},
            "longevity": {},
            "emotional_access": {},
            "share_potential": {},
            "separation": {},
            "explanation": "No content to analyze.",
        }

    mem = score_memorability(lines, art_genome)
    lon = score_longevity(lines, art_genome)
    acc = score_emotional_access(lines, art_genome)
    shr = score_share_potential(lines, art_genome)
    sep = separate_resonance(mem, lon, acc, shr)
    exp = explain_resonance(sep)

    return {
        "memorability": mem,
        "longevity": lon,
        "emotional_access": acc,
        "share_potential": shr,
        "separation": sep,
        "explanation": exp,
    }

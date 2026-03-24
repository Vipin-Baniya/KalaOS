"""
KalaOS Temporal Intelligence  (Phase 9 – Remaining Deep Features)
------------------------------------------------------------------
Tools for understanding how art exists across time — not just in the
moment of creation.

Philosophy
----------
  • Meaning is not fixed at the moment of creation.
  • Ephemeral art is not lesser art.
  • Every piece of art has ancestors — creative ancestry honours them.
  • Cultural preservation is stewardship, not archiving.

Functions
---------
track_temporal_meaning       – how and why meaning might shift over time
classify_ephemeral_art       – is this art designed to be temporary?
map_creative_ancestry        – which creative ancestors does this draw from?
generate_cultural_preservation_record – long-term stewardship documentation

Public API
----------
analyze_temporal(text, pattern_analysis, art_genome_dict,
                 existential_data, lineage_data) → full temporal dict
"""

from typing import Any, Dict, List, Optional

from kalacore.pattern_engine import _words, _normalise, count_syllables


# ---------------------------------------------------------------------------
# Temporal meaning vocabulary
# ---------------------------------------------------------------------------

# Words/phrases that suggest time-sensitive meaning
_TEMPORAL_MARKERS: frozenset = frozenset({
    "today", "now", "tonight", "this year", "this moment", "right now",
    "lately", "recently", "these days", "last night", "this morning",
    "tomorrow", "soon", "before long", "at last", "finally", "at once",
    "still", "yet", "already", "no longer", "used to", "once was",
    "when i was", "i remember", "years ago", "long ago", "in those days",
    "it was", "there was", "there were",
})

# Words that suggest timeless / universal meaning
_TIMELESS_MARKERS: frozenset = frozenset({
    "always", "forever", "eternal", "endless", "never", "every time",
    "whenever", "wherever", "whoever", "whatever", "through the ages",
    "in all things", "beyond time", "outlast", "endure", "remain",
    "constant", "unchanging", "all people", "all who", "all hearts",
})

# Cultural context indicators
_CULTURAL_SPECIFICITY: frozenset = frozenset({
    "dollar", "phone", "screen", "internet", "social", "trending",
    "viral", "post", "tweet", "like", "follow", "subscribe", "stream",
    "playlist", "algorithm", "feed", "inbox", "message", "text",
    "app", "device", "selfie", "hashtag", "dm",
})

# Ephemeral art indicators
_LIVE_PERFORMANCE_WORDS: frozenset = frozenset({
    "tonight", "right here", "this room", "you and me", "this crowd",
    "together here", "in this space", "right now", "look at us",
    "this moment", "being here",
})


# ---------------------------------------------------------------------------
# 1. Temporal Meaning Tracking
# ---------------------------------------------------------------------------

def track_temporal_meaning(
    lines: List[str],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Analyse how meaning in this piece might shift across time.

    Returns
    -------
    dict with keys:
        temporal_anchoring    – "immediate", "recent-past", "timeless", "mixed"
        temporal_word_count   – words with time-sensitive meaning
        timeless_word_count   – words with timeless meaning
        cultural_specificity  – level: "high", "moderate", "low"
        cultural_specific_words – words that tie the piece to a specific era
        temporal_notes        – plain-language observations
    """
    all_words = {w for l in lines for w in _words(l)}
    full_text = " ".join(_normalise(l) for l in lines)

    temporal_count = 0
    for marker in _TEMPORAL_MARKERS:
        if " " in marker:
            if marker in full_text:
                temporal_count += 1
        elif marker in all_words:
            temporal_count += 1

    timeless_count = 0
    for marker in _TIMELESS_MARKERS:
        if " " in marker:
            if marker in full_text:
                timeless_count += 1
        elif marker in all_words:
            timeless_count += 1

    cultural_specific = list(all_words & _CULTURAL_SPECIFICITY)
    cul_count = len(cultural_specific)
    if cul_count >= 3:
        cultural_level = "high"
    elif cul_count >= 1:
        cultural_level = "moderate"
    else:
        cultural_level = "low"

    # Determine temporal anchoring
    if timeless_count > temporal_count * 2:
        anchoring = "timeless"
    elif temporal_count > timeless_count * 2:
        anchoring = "immediate"
    elif temporal_count > 0 and timeless_count > 0:
        anchoring = "mixed"
    else:
        # Check emotional arc as secondary indicator
        arc = art_genome.get("emotional_arc", {}).get("arc_direction", "flat")
        anchoring = "timeless" if arc == "flat" else "immediate"

    temporal_notes = [
        f"Temporal anchoring: {anchoring}.",
    ]
    if cultural_level == "high":
        temporal_notes.append(
            f"High cultural specificity — words like {', '.join(cultural_specific[:3])} "
            "may date this piece or give it documentary value."
        )
    elif cultural_level == "moderate":
        temporal_notes.append(
            "Moderate cultural specificity — the piece exists in its era but reaches beyond it."
        )
    else:
        temporal_notes.append(
            "Low cultural specificity — the language is not tied to a particular moment."
        )

    if anchoring == "timeless":
        temporal_notes.append(
            "Timeless language — this piece may carry meaning across generations."
        )
    elif anchoring == "immediate":
        temporal_notes.append(
            "Immediate language — this piece lives in the present; "
            "that urgency is part of what it is."
        )
    elif anchoring == "mixed":
        temporal_notes.append(
            "The piece holds both the immediate and the timeless in tension — "
            "a rich temporal complexity."
        )

    return {
        "temporal_anchoring": anchoring,
        "temporal_word_count": temporal_count,
        "timeless_word_count": timeless_count,
        "cultural_specificity": cultural_level,
        "cultural_specific_words": cultural_specific,
        "temporal_notes": temporal_notes,
    }


# ---------------------------------------------------------------------------
# 2. Ephemeral Art Classification
# ---------------------------------------------------------------------------

def classify_ephemeral_art(
    lines: List[str],
    pattern_analysis: Dict[str, Any],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Determine if this piece is designed to be temporary — ephemeral art
    that lives most fully in performance, in the moment, in passing.

    Ephemeral indicators:
      - Direct address to a live audience
      - Present-tense immediate language
      - Very short form (fragment, vignette)
      - Low repetition (not designed for repeated recall)
      - Low rhyme density (not built for memorisation)

    Returns
    -------
    dict with keys:
        is_ephemeral       – bool
        ephemeral_score    – [0,1]
        indicators         – list of observed indicators
        ephemeral_note     – philosophical framing
    """
    n = len(lines)
    structure = pattern_analysis.get("structure", {})
    rep_count = structure.get("repetition_count", 0)
    refrains = structure.get("refrains", [])
    rhyme_density = float(art_genome.get("rhyme_density", 0.0))

    all_words = {w for l in lines for w in _words(l)}
    full_text = " ".join(_normalise(l) for l in lines)

    indicators = []
    score_components: List[float] = []

    # Direct audience address
    live_hits = sum(
        1 for m in _LIVE_PERFORMANCE_WORDS
        if (m in full_text if " " in m else m in all_words)
    )
    if live_hits >= 1:
        indicators.append(f"direct audience address ({live_hits} phrase(s))")
        score_components.append(0.3)

    # Very short form (≤4 lines)
    if n <= 4:
        indicators.append(f"fragment length ({n} lines)")
        score_components.append(0.3)

    # Low repetition (unique, not designed for recall)
    if rep_count == 0 and not refrains:
        indicators.append("no repetition — not designed for memorisation")
        score_components.append(0.2)

    # Low rhyme density
    if rhyme_density < 0.2:
        indicators.append(f"low rhyme density ({rhyme_density:.2f}) — not built for recall")
        score_components.append(0.15)

    # Present-tense immediate temporal anchoring
    immediate_words = {"now", "tonight", "today", "right", "here", "this"}
    immediate_hits = len(all_words & immediate_words)
    if immediate_hits >= 2:
        indicators.append(f"present-tense immediacy ({immediate_hits} markers)")
        score_components.append(0.2)

    ephemeral_score = round(min(sum(score_components), 1.0), 4)
    is_ephemeral = ephemeral_score >= 0.4

    return {
        "is_ephemeral": is_ephemeral,
        "ephemeral_score": ephemeral_score,
        "indicators": indicators,
        "ephemeral_note": (
            "Ephemeral art is not lesser art — it is art that lives most fully "
            "in the moment of its making or performance. "
            "The fact that it may not persist does not diminish what it was."
        ),
    }


# ---------------------------------------------------------------------------
# 3. Creative Ancestry Mapping
# ---------------------------------------------------------------------------

# Creative ancestors — pioneers of forms and approaches
_CREATIVE_ANCESTORS: Dict[str, Dict[str, Any]] = {
    "confessional tradition": {
        "exemplars": ["Sylvia Plath", "Anne Sexton", "Robert Lowell"],
        "core_signal": "first-person intimate disclosure",
        "what_it_passed_on": "permission to use the self as subject matter",
    },
    "blues tradition": {
        "exemplars": ["Bessie Smith", "Robert Johnson", "Billie Holiday"],
        "core_signal": "survival narrative, call-and-response, AAB repetition",
        "what_it_passed_on": "art as documentation of suffering and endurance",
    },
    "imagist tradition": {
        "exemplars": ["Ezra Pound", "H.D.", "William Carlos Williams"],
        "core_signal": "economy of language, concrete image, no ornament",
        "what_it_passed_on": "the image as complete statement",
    },
    "oral tradition": {
        "exemplars": ["griots", "bards", "spoken word poets"],
        "core_signal": "repetition, rhythm, communal knowledge, memorability",
        "what_it_passed_on": "art as shared memory across generations",
    },
    "protest tradition": {
        "exemplars": ["Gil Scott-Heron", "Nina Simone", "Pablo Neruda"],
        "core_signal": "direct address, refusal, collective voice",
        "what_it_passed_on": "art as political act and act of survival",
    },
    "lyric tradition": {
        "exemplars": ["Sappho", "Rumi", "Pablo Neruda"],
        "core_signal": "the self in relationship, longing, beauty",
        "what_it_passed_on": "the personal as universal — individual feeling speaks for all",
    },
    "hip-hop tradition": {
        "exemplars": ["The Last Poets", "Rakim", "Nas", "Kendrick Lamar"],
        "core_signal": "rhythmic density, internal rhyme, cultural testimony",
        "what_it_passed_on": "compression as artistry, truth-telling as virtuosity",
    },
}


def map_creative_ancestry(
    lineage_data: Dict[str, Any],
    existential_data: Dict[str, Any],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Map this piece to its creative ancestors based on formal tradition and
    emotional / structural signals.

    Returns
    -------
    dict with keys:
        ancestors           – list of {tradition, exemplars, signal, inheritance}
        primary_ancestor    – the strongest connection
        ancestry_note       – framing note
    """
    detected_traditions = [
        t["tradition"] for t in lineage_data.get("detected_traditions", [])
    ]
    creation_reason = existential_data.get("creation_reason", {})
    primary_reason = creation_reason.get("primary_reason", "expression")
    survival_driven = existential_data.get("survival", {}).get("is_survival_driven", False)

    matched_ancestors = []

    # Map formal traditions to ancestors
    tradition_to_ancestor = {
        "confessional": "confessional tradition",
        "blues": "blues tradition",
        "imagist": "imagist tradition",
        "folk": "oral tradition",
        "hip-hop lyric": "hip-hop tradition",
        "free verse": "lyric tradition",
        "ballad": "oral tradition",
        "sonnet": "lyric tradition",
    }

    seen: set = set()
    for trad in detected_traditions:
        ancestor_key = tradition_to_ancestor.get(trad)
        if ancestor_key and ancestor_key not in seen:
            ancestor = _CREATIVE_ANCESTORS[ancestor_key]
            matched_ancestors.append({
                "tradition": ancestor_key,
                "exemplars": ancestor["exemplars"],
                "core_signal": ancestor["core_signal"],
                "inheritance": ancestor["what_it_passed_on"],
            })
            seen.add(ancestor_key)

    # Add protest tradition if primary reason is protest
    if primary_reason == "protest" and "protest tradition" not in seen:
        ancestor = _CREATIVE_ANCESTORS["protest tradition"]
        matched_ancestors.append({
            "tradition": "protest tradition",
            "exemplars": ancestor["exemplars"],
            "core_signal": ancestor["core_signal"],
            "inheritance": ancestor["what_it_passed_on"],
        })

    # Add blues tradition if survival-driven
    if survival_driven and "blues tradition" not in seen:
        ancestor = _CREATIVE_ANCESTORS["blues tradition"]
        matched_ancestors.append({
            "tradition": "blues tradition",
            "exemplars": ancestor["exemplars"],
            "core_signal": ancestor["core_signal"],
            "inheritance": ancestor["what_it_passed_on"],
        })

    # Fallback: every piece of art has the lyric tradition as ancestor
    if not matched_ancestors:
        ancestor = _CREATIVE_ANCESTORS["lyric tradition"]
        matched_ancestors.append({
            "tradition": "lyric tradition",
            "exemplars": ancestor["exemplars"],
            "core_signal": ancestor["core_signal"],
            "inheritance": ancestor["what_it_passed_on"],
        })

    primary_ancestor = matched_ancestors[0]["tradition"] if matched_ancestors else "lyric tradition"

    return {
        "ancestors": matched_ancestors,
        "primary_ancestor": primary_ancestor,
        "ancestry_note": (
            "Creative ancestry is not influence-claiming — it is acknowledgement. "
            "These traditions passed something on, and this piece carries it forward, "
            "whether consciously or not."
        ),
    }


# ---------------------------------------------------------------------------
# 4. Cultural Preservation Record
# ---------------------------------------------------------------------------

def generate_cultural_preservation_record(
    lines: List[str],
    art_genome: Dict[str, Any],
    existential_data: Dict[str, Any],
    temporal_data: Dict[str, Any],
    ancestry_data: Dict[str, Any],
    fingerprint: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Generate a long-term stewardship record — documentation that treats
    this piece of art as a cultural artifact worthy of preservation.

    Returns
    -------
    dict with keys:
        preservation_priority  – "high", "moderate", "standard"
        preservation_reasons   – why this piece merits preservation
        cultural_context       – what era/conditions it reflects
        transmission_medium    – how this art is most likely to survive
        stewardship_notes      – plain-language guidance
    """
    n = len(lines)
    arc_dir = art_genome.get("emotional_arc", {}).get("arc_direction", "flat")
    creative_risk = float(art_genome.get("creative_risk_index", 0.0))
    complexity = float(art_genome.get("complexity_score", 0.0))
    temporal_anchoring = temporal_data.get("temporal_anchoring", "mixed")
    cultural_specificity = temporal_data.get("cultural_specificity", "low")
    cultural_specific_words = temporal_data.get("cultural_specific_words", [])
    survival_driven = existential_data.get("survival", {}).get("is_survival_driven", False)
    necessity_score = existential_data.get("emotional_necessity", {}).get("necessity_score", 0.0)
    primary_ancestor = ancestry_data.get("primary_ancestor", "lyric tradition")
    irreducibility_index = existential_data.get(
        "human_irreducibility", {}
    ).get("irreducibility_index", 0.0)

    # Preservation priority signals
    priority_signals: List[str] = []
    if survival_driven:
        priority_signals.append("made under existential/emotional necessity")
    if creative_risk > 0.4:
        priority_signals.append("high creative risk — rule-breaking of historic significance")
    if irreducibility_index > 0.4:
        priority_signals.append("high human irreducibility — exceeds algorithmic analysis")
    if cultural_specificity == "high":
        priority_signals.append(
            "high cultural specificity — documentary value for future readers"
        )
    if necessity_score > 0.5:
        priority_signals.append("high emotional necessity — likely made from personal imperative")

    if len(priority_signals) >= 3:
        preservation_priority = "high"
    elif len(priority_signals) >= 1:
        preservation_priority = "moderate"
    else:
        preservation_priority = "standard"

    # Cultural context
    if cultural_specific_words:
        era_note = (
            f"This piece contains culturally specific language "
            f"({', '.join(cultural_specific_words[:3])}) that situates it in a particular era."
        )
    else:
        era_note = (
            "The language is not strongly era-specific — "
            "it may survive cultural shifts more intact."
        )

    # Transmission medium — how this art is most likely to persist
    if art_genome.get("rhyme_density", 0.0) > 0.4:
        medium = "oral / sung — rhyme structure aids memorisation across generations"
    elif "oral tradition" in primary_ancestor:
        medium = "oral — repetition and rhythm designed for the voice"
    elif n <= 4:
        medium = "inscribed — short enough to be quoted and carried"
    else:
        medium = "written / recorded — length and complexity reward preservation in full"

    stewardship_notes = [
        f"Preservation priority: {preservation_priority}.",
        era_note,
        f"Transmission medium: {medium}.",
        "Cultural preservation is not about deciding what is valuable — "
        "all art has value to someone. This record exists to help this piece survive.",
    ]

    return {
        "preservation_priority": preservation_priority,
        "preservation_reasons": priority_signals,
        "cultural_context": era_note,
        "transmission_medium": medium,
        "stewardship_notes": stewardship_notes,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_temporal(
    text: str,
    pattern_analysis: Dict[str, Any],
    art_genome: Dict[str, Any],
    existential_data: Dict[str, Any],
    lineage_data: Dict[str, Any],
    fingerprint: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Full Phase 9 temporal intelligence analysis.

    Parameters
    ----------
    text             : original multi-line text
    pattern_analysis : output of kalacore.pattern_engine.analyze()
    art_genome       : output of kalacore.art_genome.ArtGenome.to_dict()
    existential_data : output of kalacore.existential.analyze_existential()
    lineage_data     : output of kalacore.kalacustody.assess_artistic_lineage()
    fingerprint      : optional, from kalacore.kalacustody.generate_artistic_fingerprint()

    Returns
    -------
    dict with keys:
        temporal_meaning, ephemeral_classification, creative_ancestry,
        cultural_preservation
    """
    raw_lines = text.splitlines()
    lines = [l for l in raw_lines if l.strip()]

    if not lines:
        return {
            "temporal_meaning": {},
            "ephemeral_classification": {},
            "creative_ancestry": {},
            "cultural_preservation": {},
        }

    temporal_data = track_temporal_meaning(lines, art_genome)
    ephemeral_data = classify_ephemeral_art(lines, pattern_analysis, art_genome)
    ancestry_data = map_creative_ancestry(lineage_data, existential_data, art_genome)
    preservation_data = generate_cultural_preservation_record(
        lines, art_genome, existential_data, temporal_data, ancestry_data, fingerprint
    )

    return {
        "temporal_meaning": temporal_data,
        "ephemeral_classification": ephemeral_data,
        "creative_ancestry": ancestry_data,
        "cultural_preservation": preservation_data,
    }

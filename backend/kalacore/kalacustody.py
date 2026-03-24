"""
KalaCustody  (Phase 6 – Authorship, Trust & Legacy)
-----------------------------------------------------
Immutable authorship tools that serve the artist's right to be remembered
as the origin of their work — now and in the future.

Philosophy
----------
  • Authorship is not a permission system — it is a human truth.
  • The fingerprint belongs to the artist, not the platform.
  • Similarity detection is for the artist's awareness, not for enforcement.
  • Legacy annotation preserves intent, not performance.

Functions
---------
generate_artistic_fingerprint   – deterministic structural description of a piece
create_custody_record           – structured authorship record (no external DB)
assess_artistic_lineage         – which traditions does this piece draw from?
detect_structural_similarity    – structural-level similarity between two pieces
build_legacy_annotation         – future-facing documentation of artistic intent

Public API
----------
custody(text, pattern_analysis, art_genome_dict, existential_data) → dict
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from kalacore.pattern_engine import _words, _normalise, count_syllables


# ---------------------------------------------------------------------------
# Tradition vocabulary
# ---------------------------------------------------------------------------

# Formal traditions keyed by observable structural signals
_TRADITIONS = {
    "blues":              "AAB stanza, bent notes, call-and-response, survival narrative",
    "folk":               "narrative storytelling, repetition, communal themes, oral tradition",
    "ghazal":             "radif (refrain at end of each couplet), beloveds's name in final couplet",
    "sonnet":             "14-line form, turn (volta), iambic pentameter tradition",
    "haiku":              "17-syllable (5-7-5), nature/season reference, juxtaposition",
    "slam / spoken word": "direct address, anaphora, conversational rhythm, protest tradition",
    "hip-hop lyric":      "multisyllabic rhyme, internal rhyme density, rhythmic compression",
    "ballad":             "narrative verse, alternating 8-6 syllables, ABAB rhyme, story arc",
    "free verse":         "no fixed form, line breaks as meaning, breath as unit of measure",
    "confessional":       "first-person singular, raw emotional disclosure, private made public",
    "imagist":            "concrete imagery, economy of language, no ornamentation",
}

# Signals that suggest each tradition
_TRADITION_SIGNALS: Dict[str, Dict[str, Any]] = {
    "blues": {
        "min_lines": 3,
        "repetition_count_min": 1,
        "survival_keywords": frozenset({"hurt", "pain", "gone", "down", "blues"}),
    },
    "folk": {
        "narrative_indicators": frozenset({"once", "was", "came", "went", "told", "story"}),
        "min_lines": 6,
    },
    "hip-hop lyric": {
        "internal_rhyme_threshold": 0.4,
        "rhyme_density_threshold": 0.5,
    },
    "confessional": {
        "first_person_ratio_threshold": 0.4,
    },
    "imagist": {
        "avg_line_words_max": 6,
        "cognitive_load_max": 0.4,
    },
    "haiku": {
        "line_count": 3,
    },
    "sonnet": {
        "line_count": 14,
    },
}


# ---------------------------------------------------------------------------
# 1. Artistic Fingerprint
# ---------------------------------------------------------------------------

def generate_artistic_fingerprint(
    text: str,
    pattern_analysis: Dict[str, Any],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Generate a deterministic structural fingerprint of the piece.

    The fingerprint is NOT a cryptographic hash of the raw text — it captures
    the artistic structure in a way that is human-readable AND machine-stable.
    Two pieces with the same structure will have the same fingerprint even if
    their words differ, making it useful for understanding form, not just identity.

    For identity, a SHA-256 of the normalised text is also provided.

    Returns
    -------
    dict with keys:
        structural_fingerprint   – compact human-readable structural descriptor
        identity_hash            – SHA-256 of normalised text (for identity checks)
        fingerprint_components   – breakdown of contributing factors
    """
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return {
            "structural_fingerprint": "empty",
            "identity_hash": hashlib.sha256(b"").hexdigest(),
            "fingerprint_components": {},
        }

    # Structural fingerprint components
    form = art_genome.get("form_type", "unknown")
    n_lines = len(lines)
    rhyme_density = round(float(art_genome.get("rhyme_density", 0.0)), 2)
    arc_dir = art_genome.get("emotional_arc", {}).get("arc_direction", "flat")
    symmetry = "symmetric" if art_genome.get("symmetry_score", 0.0) >= 1.0 else "asymmetric"
    has_refrain = bool(pattern_analysis.get("structure", {}).get("refrains"))

    # Syllable shape: describe as a compact sequence
    syl_totals = []
    for l in lines:
        syl_totals.append(sum(count_syllables(w) for w in _words(l)))
    syl_profile = "-".join(str(s) for s in syl_totals[:8])  # first 8 lines
    if len(lines) > 8:
        syl_profile += f"…({n_lines} lines)"

    structural_fingerprint = (
        f"{form}|{n_lines}L|{arc_dir}|{symmetry}|"
        f"rhyme={rhyme_density:.2f}|"
        f"{'refrain' if has_refrain else 'no-refrain'}|"
        f"syl={syl_profile}"
    )

    # Identity hash: SHA-256 of normalised text
    normalised_text = " ".join(_normalise(l) for l in lines)
    identity_hash = hashlib.sha256(normalised_text.encode("utf-8")).hexdigest()

    return {
        "structural_fingerprint": structural_fingerprint,
        "identity_hash": identity_hash,
        "fingerprint_components": {
            "form": form,
            "line_count": n_lines,
            "arc_direction": arc_dir,
            "symmetry": symmetry,
            "rhyme_density": rhyme_density,
            "has_refrain": has_refrain,
            "syllable_profile": syl_profile,
        },
    }


# ---------------------------------------------------------------------------
# 2. Custody Record
# ---------------------------------------------------------------------------

def create_custody_record(
    text: str,
    fingerprint: dict,
    art_genome: Dict[str, Any],
    artist_name: Optional[str] = None,
    creation_context: Optional[str] = None,
) -> dict:
    """
    Create a structured authorship record that the artist controls.

    This is not a blockchain or external registry — it is a portable,
    human-readable record that the artist can store wherever they choose.

    Returns
    -------
    dict with keys:
        version             – record schema version
        identity_hash       – from fingerprint (for reference)
        structural_fingerprint – from fingerprint
        declared_artist     – artist name if provided, else "[undeclared]"
        creation_context    – artist-supplied context if provided
        art_genome_summary  – compact summary of the piece's artistic identity
        record_note         – usage note
    """
    genome_summary = {
        "form_type": art_genome.get("form_type", "unknown"),
        "rhyme_density": art_genome.get("rhyme_density", 0.0),
        "emotional_arc": art_genome.get("emotional_arc", {}).get("arc_direction", "unknown"),
        "complexity_score": art_genome.get("complexity_score", 0.0),
        "creative_risk_index": art_genome.get("creative_risk_index", 0.0),
    }

    return {
        "version": "1.0",
        "identity_hash": fingerprint.get("identity_hash", ""),
        "structural_fingerprint": fingerprint.get("structural_fingerprint", ""),
        "declared_artist": artist_name or "[undeclared]",
        "creation_context": creation_context or "[not provided]",
        "art_genome_summary": genome_summary,
        "record_note": (
            "This record is created by and for the artist. "
            "Store it wherever you choose — it belongs to you. "
            "KalaOS does not retain or transmit this record."
        ),
    }


# ---------------------------------------------------------------------------
# 3. Artistic Lineage Assessment
# ---------------------------------------------------------------------------

def assess_artistic_lineage(
    lines: List[str],
    pattern_analysis: Dict[str, Any],
    art_genome: Dict[str, Any],
) -> dict:
    """
    Identify which artistic traditions this piece draws from, based on
    observable structural and linguistic signals.

    Returns
    -------
    dict with keys:
        detected_traditions – list of {tradition, confidence, signals} dicts
        primary_tradition   – highest-confidence match
        lineage_note        – plain-language framing
    """
    n = len(lines)
    structure = pattern_analysis.get("structure", {})
    rhymes = pattern_analysis.get("rhymes", {})
    internal_rhymes = rhymes.get("internal_rhymes", [])
    emotional_arc = pattern_analysis.get("emotional_arc", {})

    rhyme_density = float(art_genome.get("rhyme_density", 0.0))
    cognitive_load = float(art_genome.get("cognitive_load", 0.0))

    # First-person ratio
    first_person = sum(1 for l in lines if _words(l) and _words(l)[0] == "i")
    fp_ratio = first_person / max(n, 1)

    # Internal rhyme density
    ir_with_rhyme = sum(1 for r in internal_rhymes if r.get("has_internal_rhyme"))
    ir_density = ir_with_rhyme / max(n, 1)

    # Average words per line
    avg_words = sum(len(_words(l)) for l in lines) / max(n, 1)

    all_words_flat = {w for l in lines for w in _words(l)}

    detected = []

    # Haiku
    if n == 3:
        detected.append({
            "tradition": "haiku",
            "confidence": 0.85,
            "signals": ["3-line structure"],
            "description": _TRADITIONS["haiku"],
        })

    # Sonnet
    elif n == 14:
        detected.append({
            "tradition": "sonnet",
            "confidence": 0.80,
            "signals": ["14-line structure"],
            "description": _TRADITIONS["sonnet"],
        })

    # Hip-hop lyric
    if ir_density >= 0.4 and rhyme_density >= 0.5:
        detected.append({
            "tradition": "hip-hop lyric",
            "confidence": round(min((ir_density + rhyme_density) / 2, 1.0), 4),
            "signals": [
                f"internal rhyme density {ir_density:.2f}",
                f"end rhyme density {rhyme_density:.2f}",
            ],
            "description": _TRADITIONS["hip-hop lyric"],
        })

    # Confessional
    if fp_ratio >= 0.4:
        detected.append({
            "tradition": "confessional",
            "confidence": round(min(fp_ratio, 1.0), 4),
            "signals": [f"first-person ratio {fp_ratio:.2f}"],
            "description": _TRADITIONS["confessional"],
        })

    # Imagist
    if avg_words <= 6 and cognitive_load <= 0.4:
        detected.append({
            "tradition": "imagist",
            "confidence": round(max(0.4, 1.0 - (avg_words / 10.0)), 4),
            "signals": [
                f"avg words per line {avg_words:.1f}",
                f"cognitive load {cognitive_load:.2f}",
            ],
            "description": _TRADITIONS["imagist"],
        })

    # Blues signals
    blues_words = {"hurt", "pain", "gone", "down", "blues"}
    blues_hits = len(all_words_flat & blues_words)
    rep_count = structure.get("repetition_count", 0)
    if blues_hits >= 1 and rep_count >= 1 and n >= 3:
        detected.append({
            "tradition": "blues",
            "confidence": round(min(blues_hits * 0.2 + rep_count * 0.1, 1.0), 4),
            "signals": [
                f"blues vocabulary ({blues_hits} matches)",
                f"repetition count {rep_count}",
            ],
            "description": _TRADITIONS["blues"],
        })

    # Folk / narrative
    folk_words = {"once", "was", "came", "went", "told", "story"}
    folk_hits = len(all_words_flat & folk_words)
    if folk_hits >= 1 and n >= 6:
        detected.append({
            "tradition": "folk",
            "confidence": round(min(folk_hits * 0.15, 0.7), 4),
            "signals": [
                f"narrative vocabulary ({folk_hits} matches)",
                f"{n} lines",
            ],
            "description": _TRADITIONS["folk"],
        })

    # Free verse (fallback if nothing detected or low confidence)
    if not detected or all(t["confidence"] < 0.5 for t in detected):
        detected.append({
            "tradition": "free verse",
            "confidence": 0.5,
            "signals": ["no dominant formal tradition detected"],
            "description": _TRADITIONS["free verse"],
        })

    detected.sort(key=lambda t: t["confidence"], reverse=True)
    primary = detected[0]["tradition"] if detected else "unknown"

    return {
        "detected_traditions": detected,
        "primary_tradition": primary,
        "lineage_note": (
            "Artistic traditions are not boxes — they are conversation partners. "
            "This piece may draw from several, or from none that have names yet."
        ),
    }


# ---------------------------------------------------------------------------
# 4. Structural Similarity Detection
# ---------------------------------------------------------------------------

def detect_structural_similarity(
    fingerprint_a: dict,
    fingerprint_b: dict,
) -> dict:
    """
    Compare two pieces at the structural level using their fingerprint components.
    Does NOT compare raw text — structural similarity is not plagiarism detection.

    Returns
    -------
    dict with keys:
        similarity_score  – [0,1] structural similarity
        matching_features – list of features that match
        diverging_features – list of features that differ
        similarity_note   – ethical framing
    """
    comp_a = fingerprint_a.get("fingerprint_components", {})
    comp_b = fingerprint_b.get("fingerprint_components", {})

    fields_to_compare = [
        "form", "arc_direction", "symmetry", "has_refrain",
    ]
    numeric_fields = [
        ("rhyme_density", 0.2),  # tolerance
        ("line_count", 3),
    ]

    matching = []
    diverging = []

    for field in fields_to_compare:
        val_a = comp_a.get(field)
        val_b = comp_b.get(field)
        if val_a is not None and val_b is not None:
            if val_a == val_b:
                matching.append(f"{field}: {val_a}")
            else:
                diverging.append(f"{field}: {val_a!r} vs {val_b!r}")

    for field, tolerance in numeric_fields:
        val_a = comp_a.get(field, 0)
        val_b = comp_b.get(field, 0)
        try:
            if abs(float(val_a) - float(val_b)) <= tolerance:
                matching.append(f"{field}: ~{val_a}")
            else:
                diverging.append(f"{field}: {val_a} vs {val_b}")
        except (TypeError, ValueError):
            pass

    total_checks = len(matching) + len(diverging)
    score = round(len(matching) / max(total_checks, 1), 4)

    return {
        "similarity_score": score,
        "matching_features": matching,
        "diverging_features": diverging,
        "similarity_note": (
            "Structural similarity is about form, not content. "
            "Two sonnets are structurally similar — that doesn't make one derivative of the other. "
            "Only the artist can assess true artistic relationship between pieces."
        ),
    }


# ---------------------------------------------------------------------------
# 5. Legacy Annotation
# ---------------------------------------------------------------------------

def build_legacy_annotation(
    art_genome: Dict[str, Any],
    existential_data: Dict[str, Any],
    fingerprint: dict,
    lineage: dict,
) -> dict:
    """
    Generate a future-facing documentation record that captures artistic
    intent, structural identity, and cultural context.

    Returns
    -------
    dict with keys:
        artistic_identity   – what this piece structurally is
        emotional_intent    – what it was reaching for
        creation_context    – why it was created (inferred archetype)
        formal_tradition    – which tradition(s) it sits in
        irreducible_zones   – what defies explanation
        legacy_note         – purpose statement
    """
    creation_reason = existential_data.get("creation_reason", {})
    primary_reason = creation_reason.get("primary_reason", "expression")
    survival = existential_data.get("survival", {})
    necessity = existential_data.get("emotional_necessity", {})
    irreducibility = existential_data.get("human_irreducibility", {})

    arc_dir = art_genome.get("emotional_arc", {}).get("arc_direction", "flat")
    form = art_genome.get("form_type", "unknown")
    complexity = art_genome.get("complexity_score", 0.0)

    # Artistic identity sentence
    artistic_identity = (
        f"A {form} with {arc_dir} emotional arc, "
        f"complexity {complexity:.2f}, "
        f"structural fingerprint: {fingerprint.get('structural_fingerprint', '[unknown]')}."
    )

    # Emotional intent sentence
    arc_intent_map = {
        "ascending":   "reaching toward — emergence, hope, resolution",
        "descending":  "moving inward — depth, grief, honesty",
        "oscillating": "holding contradiction — complexity, uncertainty, truth",
        "flat":        "sustaining presence — meditation, stillness, endurance",
    }
    emotional_intent = arc_intent_map.get(arc_dir, "expressing — the full range")

    # Creation context
    reason_phrases = {
        "catharsis": "made for release — to empty what was full",
        "testimony": "made to bear witness — to say: this happened",
        "survival": "made to survive — art as life-raft",
        "connection": "made for another — to say: you are not alone",
        "protest": "made to resist — art as refusal",
        "wonder": "made from awe — art as gratitude",
        "expression": "made because it needed to be made",
    }
    creation_context_note = reason_phrases.get(primary_reason, "made — the reason is the artist's own")

    # Irreducible zones
    irreducible_lines = irreducibility.get("irreducible_lines", [])
    irreducible_index = irreducibility.get("irreducibility_index", 0.0)
    if irreducible_index > 0.3:
        irreducible_note = (
            f"{len(irreducible_lines)} line(s) defy pattern explanation — "
            "this is where the human exceeds the algorithm."
        )
    else:
        irreducible_note = "Structure accounts for most of this piece — the craft is the art."

    return {
        "artistic_identity": artistic_identity,
        "emotional_intent": emotional_intent,
        "creation_context": creation_context_note,
        "formal_tradition": lineage.get("primary_tradition", "unknown"),
        "detected_traditions": [t["tradition"] for t in lineage.get("detected_traditions", [])],
        "irreducible_zones": {
            "count": len(irreducible_lines),
            "index": irreducible_index,
            "note": irreducible_note,
        },
        "legacy_note": (
            "This annotation is a record of what was made, why it was made, "
            "and what it structurally is. It belongs to the artist. "
            "Art does not need to justify its existence — this record is witness, not defence."
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def custody(
    text: str,
    pattern_analysis: Dict[str, Any],
    art_genome: Dict[str, Any],
    existential_data: Dict[str, Any],
    artist_name: Optional[str] = None,
    creation_context: Optional[str] = None,
) -> dict:
    """
    Full KalaCustody authorship and legacy analysis.

    Parameters
    ----------
    text              : original multi-line text
    pattern_analysis  : output of kalacore.pattern_engine.analyze()
    art_genome        : output of kalacore.art_genome.ArtGenome.to_dict()
    existential_data  : output of kalacore.existential.analyze_existential()
    artist_name       : optional — artist name to include in custody record
    creation_context  : optional — artist's note about creation context

    Returns
    -------
    dict with keys:
        fingerprint, custody_record, lineage, legacy_annotation
    """
    raw_lines = text.splitlines()
    lines = [l for l in raw_lines if l.strip()]

    if not lines:
        return {
            "fingerprint": {},
            "custody_record": {},
            "lineage": {},
            "legacy_annotation": {},
        }

    fp = generate_artistic_fingerprint(text, pattern_analysis, art_genome)
    lineage = assess_artistic_lineage(lines, pattern_analysis, art_genome)
    legacy = build_legacy_annotation(art_genome, existential_data, fp, lineage)
    record = create_custody_record(text, fp, art_genome, artist_name, creation_context)

    return {
        "fingerprint": fp,
        "custody_record": record,
        "lineage": lineage,
        "legacy_annotation": legacy,
    }

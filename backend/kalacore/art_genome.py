"""
ArtGenome Model
---------------
A structured representation of the artistic properties of a text.
Derived from the pattern_engine analysis output.

Scores are normalised to the [0.0, 1.0] range where applicable.
Phase 1 fields cover all KalaCore intelligence dimensions:
  structural complexity, rhyme, symmetry, improvisation, emotional arc,
  cognitive load, form type, and human-irreducible zones.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class ArtGenome:
    # Raw structural analysis from pattern_engine
    structure_analysis: Dict[str, Any] = field(default_factory=dict)

    # Proportion of lines that participate in end-rhyme groups
    rhyme_density: float = 0.0

    # 1.0 if the piece has mirror symmetry in line-length profile, else 0.0
    symmetry_score: float = 0.0

    # Detected improvisation markers (rhythm breaks, rhyme breaks, unique lines)
    improvisation_markers: List[str] = field(default_factory=list)

    # Heuristic combination of rhyme density, palindrome frequency,
    # syllable variance and repetition
    complexity_score: float = 0.0

    # Probable poetic / lyric form (e.g. "haiku", "sonnet", "free verse")
    form_type: str = "unknown"

    # Creative risk index from improvisation detector [0,1]
    creative_risk_index: float = 0.0

    # Per-line emotional valence scores and overall arc direction
    emotional_arc: Dict[str, Any] = field(default_factory=dict)

    # Cognitive load on the reader / listener [0,1]
    cognitive_load: float = 0.0

    # Lines / zones where algorithmic analysis cannot explain the artistic choice —
    # places where human creativity is irreducible to pattern.
    human_irreducible_zones: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def build_art_genome(analysis: dict) -> ArtGenome:
    """
    Derive an ArtGenome from pattern_engine.analyze() output.

    Parameters
    ----------
    analysis : dict
        Output from kalacore.pattern_engine.analyze()

    Returns
    -------
    ArtGenome instance
    """
    # Short-circuit: empty analysis produces a zeroed genome
    if not analysis or not analysis.get("syllables"):
        return ArtGenome()

    rhymes = analysis.get("rhymes", {})
    structure = analysis.get("structure", {})
    palindrome = analysis.get("palindrome", {})
    syllables = analysis.get("syllables", [])
    improvisation = analysis.get("improvisation", {})
    form_type_data = analysis.get("form_type", {})
    emotional_arc = analysis.get("emotional_arc", {})

    # --- Rhyme density ---
    rhyme_density = float(rhymes.get("end_rhyme_density", 0.0))

    # --- Symmetry score ---
    symmetry_score = 1.0 if structure.get("is_symmetric", False) else 0.0

    # --- Complexity score (heuristic) ---
    pal_lines = palindrome.get("lines", [])
    pal_richness = (
        sum(1 for l in pal_lines if l.get("partial_palindromes")) / len(pal_lines)
        if pal_lines else 0.0
    )

    syl_totals = [s.get("total_syllables", 0) for s in syllables]
    if len(syl_totals) > 1:
        mean_syl = sum(syl_totals) / len(syl_totals)
        variance = sum((x - mean_syl) ** 2 for x in syl_totals) / len(syl_totals)
        std_dev = variance ** 0.5
        syl_variance_norm = min(std_dev / 5.0, 1.0)
    else:
        syl_variance_norm = 0.0

    repetition_ratio = min(
        structure.get("repetition_count", 0) / max(len(pal_lines), 1), 1.0
    )

    complexity_score = round(
        (rhyme_density * 0.3)
        + (pal_richness * 0.2)
        + (syl_variance_norm * 0.3)
        + ((1.0 - repetition_ratio) * 0.2),
        4,
    )

    # --- Form type ---
    form_type = form_type_data.get("form", "unknown")

    # --- Improvisation markers ---
    imp_markers = improvisation.get("markers", [])
    creative_risk_index = float(improvisation.get("creative_risk_index", 0.0))

    # --- Human-irreducible zones ---
    # A line is "human-irreducible" if it sits in the chaos_lines set AND
    # has no detectable palindrome, rhyme, or repetition pattern — it simply
    # exists on its own artistic terms.
    chaos_lines = set(improvisation.get("chaos_lines", []))
    pal_line_texts = {l.get("line", "") for l in pal_lines if l.get("is_full_palindrome")}
    rhyming_line_indices = set()
    for indices in rhymes.get("end_rhyme_groups", {}).values():
        rhyming_line_indices.update(indices)
    all_lines_ordered = [s.get("line", s.get("syllables_per_word", "")) for s in syllables]
    rhyming_line_texts = {
        (syllables[i]["line"] if isinstance(syllables[i], dict) and "line" in syllables[i] else "")
        for i in rhyming_line_indices
        if i < len(syllables)
    }

    human_irreducible = [
        line for line in chaos_lines
        if line not in pal_line_texts and line not in rhyming_line_texts
    ]

    return ArtGenome(
        structure_analysis=structure,
        rhyme_density=round(rhyme_density, 4),
        symmetry_score=symmetry_score,
        improvisation_markers=imp_markers,
        complexity_score=complexity_score,
        form_type=form_type,
        creative_risk_index=creative_risk_index,
        emotional_arc=emotional_arc,
        cognitive_load=float(analysis.get("cognitive_load", 0.0)),
        human_irreducible_zones=human_irreducible,
    )

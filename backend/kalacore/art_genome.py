"""
ArtGenome Model
---------------
A structured representation of the artistic properties of a text.
Derived from the pattern_engine analysis output.

Scores are normalised to the [0.0, 1.0] range where applicable.
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

    # Placeholder for future improvisation markers (e.g. blues-call-response)
    improvisation_markers: List[str] = field(default_factory=list)

    # Heuristic: combination of rhyme density, palindrome frequency,
    # syllable variance and repetition
    complexity_score: float = 0.0

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

    # --- Rhyme density ---
    rhyme_density = float(rhymes.get("end_rhyme_density", 0.0))

    # --- Symmetry score ---
    symmetry_score = 1.0 if structure.get("is_symmetric", False) else 0.0

    # --- Complexity score (heuristic) ---
    # Components:
    #   1) Rhyme density (already [0,1])
    #   2) Palindrome richness: proportion of lines with partial palindromes
    pal_lines = palindrome.get("lines", [])
    pal_richness = (
        sum(1 for l in pal_lines if l.get("partial_palindromes")) / len(pal_lines)
        if pal_lines else 0.0
    )

    #   3) Syllable variance: std-dev of total syllables per line (normalised)
    syl_totals = [s.get("total_syllables", 0) for s in syllables]
    if len(syl_totals) > 1:
        mean_syl = sum(syl_totals) / len(syl_totals)
        variance = sum((x - mean_syl) ** 2 for x in syl_totals) / len(syl_totals)
        std_dev = variance ** 0.5
        # Normalise against a "typical" std-dev of 5 syllables
        syl_variance_norm = min(std_dev / 5.0, 1.0)
    else:
        syl_variance_norm = 0.0

    #   4) Repetition adds familiarity but lowers raw complexity
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

    return ArtGenome(
        structure_analysis=structure,
        rhyme_density=round(rhyme_density, 4),
        symmetry_score=symmetry_score,
        improvisation_markers=[],  # placeholder for future detection
        complexity_score=complexity_score,
    )

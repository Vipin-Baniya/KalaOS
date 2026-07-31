"""
KalaOS Ethical Infrastructure
------------------------------
Phase 0 – Foundational Principles (always active, non-configurable).
Phase 10 – Ethical guardrails applied at every API boundary.

These are not optional settings — they are architectural constants that
govern every feature of the platform.
"""

import unicodedata
from typing import List, NamedTuple


# ---------------------------------------------------------------------------
# Phase 0 — Foundational Principles (immutable constants)
# ---------------------------------------------------------------------------

class _Principles:
    """
    Read-only namespace encoding the KalaOS Phase 0 ethical axioms.

    These constants exist in code so the principles are machine-readable,
    versionable, and auditable — not just documented in a README.
    """
    ART_IS_NOT_CONTENT: bool = True
    ARTIST_IS_NOT_RESOURCE: bool = True
    AI_IS_NOT_AUTHOR: bool = True
    SILENCE_IS_NOT_FAILURE: bool = True
    VIRALITY_IS_NOT_VALUE: bool = True
    DIGNITY_OVER_GROWTH: bool = True

    # System-wide prohibitions
    NO_ENGAGEMENT_ADDICTION: bool = True
    NO_FORCED_OPTIMISATION: bool = True
    NO_SILENT_AI_TRAINING: bool = True
    NO_ARTIST_REPLACEMENT: bool = True
    FULL_OWNERSHIP_AND_ATTRIBUTION: bool = True


PRINCIPLES = _Principles()


# ---------------------------------------------------------------------------
# Phase 10 — Ethical Guardrails
# ---------------------------------------------------------------------------

class EthicsViolation(NamedTuple):
    """A single ethical violation detected in a user request."""
    code: str
    message: str


# Lightweight heuristic triggers for requests that ask KalaOS to impersonate
# or replace a specific named artist.  Production systems should complement
# this with a more robust classifier.
_IMITATION_TRIGGERS = (
    "write like ",
    "sound like ",
    "in the style of ",
    "pretend to be ",
    "imitate ",
    "replace ",
)

# Maximum text length — KalaOS analyses art thoughtfully, not at bulk scale.
MAX_TEXT_LENGTH = 50_000  # characters


_HOMOGLYPH_MAP = {
    # Cyrillic lookalikes for Latin letters (common bypass attempts)
    'а': 'a',  # U+0430 Cyrillic → U+0061 Latin
    'е': 'e',  # U+0435 Cyrillic → U+0065 Latin
    'о': 'o',  # U+043E Cyrillic → U+006F Latin
    'р': 'p',  # U+0440 Cyrillic → U+0070 Latin
    'с': 'c',  # U+0441 Cyrillic → U+0063 Latin
    'у': 'y',  # U+0443 Cyrillic → U+0079 Latin
    'х': 'x',  # U+0445 Cyrillic → U+0078 Latin
    'А': 'A',  # U+0410 Cyrillic → U+0041 Latin
    'Е': 'E',  # U+0415 Cyrillic → U+0045 Latin
    'О': 'O',  # U+041E Cyrillic → U+004F Latin
    'Р': 'P',  # U+0420 Cyrillic → U+0050 Latin
    'С': 'C',  # U+0421 Cyrillic → U+0043 Latin
    'У': 'Y',  # U+0423 Cyrillic → U+0059 Latin
    'Х': 'X',  # U+0425 Cyrillic → U+0058 Latin
}


def _normalize_for_screening(text: str) -> str:
    """
    Normalize text to prevent Unicode homoglyph and zero-width character bypasses.

    Applies:
    1. NFKC normalization: converts compatibility characters
    2. Homoglyph mapping: converts Cyrillic lookalikes to Latin equivalents
    3. Zero-width character removal: strips characters in Unicode category 'Cf'
       (e.g., zero-width joiners, zero-width non-joiners, etc.)

    This ensures that visually identical strings (even with hidden characters or
    Unicode lookalikes) are normalized to the same canonical form.
    """
    # NFKC: Compatibility decomposition, then composition
    normalized = unicodedata.normalize("NFKC", text)

    # Map homoglyphs: convert known lookalikes to their canonical forms
    homoglyph_replaced = "".join(
        _HOMOGLYPH_MAP.get(c, c) for c in normalized
    )

    # Remove zero-width and other format characters (Unicode category Cf)
    # This strips: zero-width joiner, zero-width non-joiner, zero-width space, etc.
    cleaned = "".join(
        c for c in homoglyph_replaced
        if unicodedata.category(c) != "Cf"
    )

    return cleaned


def check_request(text: str) -> List[EthicsViolation]:
    """
    Run ethical guardrail checks on a user-supplied text before processing.

    Returns
    -------
    List[EthicsViolation]
        Empty list means the request is clean.
        Non-empty list means the API layer should return a 422 with the
        violation messages surfaced to the caller.

    Checks performed
    ----------------
    1. TEXT_TOO_LONG    – text exceeds MAX_TEXT_LENGTH characters.
    2. IMITATION_REQUEST – text contains phrases that ask KalaOS to imitate
                           or replace a living artist.
    """
    violations: List[EthicsViolation] = []

    if not text or not text.strip():
        return violations  # empty text handled by request-level validation

    # Check 1: length
    if len(text) > MAX_TEXT_LENGTH:
        violations.append(EthicsViolation(
            code="TEXT_TOO_LONG",
            message=(
                f"Text exceeds the maximum of {MAX_TEXT_LENGTH:,} characters. "
                "KalaOS analyses art with intention — not at industrial scale."
            ),
        ))

    # Check 2: imitation request
    # Normalize text to prevent Unicode homoglyph and zero-width character bypasses
    normalized = _normalize_for_screening(text).lower()
    for trigger in _IMITATION_TRIGGERS:
        if trigger in normalized:
            violations.append(EthicsViolation(
                code="IMITATION_REQUEST",
                message=(
                    "KalaOS does not imitate or replace living artists. "
                    "We illuminate your art — not someone else's voice. "
                    f'(Detected phrase: "{trigger.strip()}")'
                ),
            ))
            break  # one imitation violation is sufficient

    return violations

"""
KalaCore Pattern Engine
-----------------------
Analyzes text (lyrics, poems) for artistic patterns:
  - Palindrome detection (full-line and partial)
  - Rhyme detection (end-rhyme and internal)
  - Syllable estimation (heuristic)
  - Structure analysis (repetition and symmetry)

All functions are pure and stateless — no external dependencies required.
"""

import re
from collections import Counter
from typing import Dict, List


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Lowercase and strip punctuation, keeping only letters and spaces."""
    return re.sub(r"[^a-z ]", "", text.lower())


def _words(line: str) -> List[str]:
    """Return the list of words in a line (normalised)."""
    return _normalise(line).split()


def _last_vowel_cluster(word: str) -> str:
    """
    Return the trailing vowel+consonant rhyme nucleus of a word.
    e.g. 'night' -> 'ight', 'play' -> 'ay'
    """
    word = word.lower()
    # Find the last vowel sequence and everything after it
    match = re.search(r"[aeiou][^aeiou]*$", word)
    return match.group(0) if match else word[-2:]


# ---------------------------------------------------------------------------
# 1. Palindrome Detection
# ---------------------------------------------------------------------------

def detect_palindrome(lines: List[str]) -> dict:
    """
    Detect palindrome structures across the provided lines.

    Full palindrome  – the normalised character sequence of a line reads
                       the same forwards and backwards.
    Partial palindrome – a line contains a contiguous sub-sequence of ≥4
                         characters that is palindromic (e.g. "level", "civic").
    """
    results = []
    for line in lines:
        norm = _normalise(line).replace(" ", "")
        is_full = norm == norm[::-1] and len(norm) > 0

        # Find longest palindromic sub-string (length ≥ 4)
        partial_hits = []
        n = len(norm)
        for i in range(n):
            for j in range(i + 4, n + 1):
                sub = norm[i:j]
                if sub == sub[::-1]:
                    # Keep longest non-overlapping finds
                    partial_hits.append(sub)

        # De-duplicate partial hits and keep only maximal ones
        maximal = []
        for s in partial_hits:
            if not any(s in other and s != other for other in partial_hits):
                if s not in maximal:
                    maximal.append(s)

        results.append({
            "line": line,
            "is_full_palindrome": is_full,
            "partial_palindromes": maximal,
        })

    return {
        "full_palindrome_count": sum(1 for r in results if r["is_full_palindrome"]),
        "lines": results,
    }


# ---------------------------------------------------------------------------
# 2. Rhyme Detection
# ---------------------------------------------------------------------------

def detect_rhymes(lines: List[str]) -> dict:
    """
    Detect end-rhymes and simple internal rhymes.

    End-rhyme   – the last word of consecutive (or all) lines shares a rhyme
                  nucleus with at least one other line's last word.
    Internal    – within a single line, two or more words share a rhyme nucleus.
    """
    end_words = []
    for line in lines:
        ws = _words(line)
        end_words.append(ws[-1] if ws else "")

    # Group end-words by their rhyme nucleus
    end_rhyme_groups: Dict[str, List[int]] = {}
    for idx, word in enumerate(end_words):
        nucleus = _last_vowel_cluster(word)
        end_rhyme_groups.setdefault(nucleus, []).append(idx)

    # Only report groups where at least two lines rhyme
    rhyming_pairs = {
        nucleus: indices
        for nucleus, indices in end_rhyme_groups.items()
        if len(indices) >= 2 and nucleus
    }

    # Internal rhymes per line
    internal_rhymes = []
    for line in lines:
        ws = _words(line)
        nuclei = [_last_vowel_cluster(w) for w in ws]
        nucleus_counts = Counter(nuclei)
        repeating = [n for n, c in nucleus_counts.items() if c >= 2]
        internal_rhymes.append({
            "line": line,
            "internal_rhyme_nuclei": repeating,
            "has_internal_rhyme": len(repeating) > 0,
        })

    return {
        "end_rhyme_groups": rhyming_pairs,
        "end_rhyme_density": len(rhyming_pairs) / max(len(lines), 1),
        "internal_rhymes": internal_rhymes,
    }


# ---------------------------------------------------------------------------
# 3. Syllable Estimation
# ---------------------------------------------------------------------------

def count_syllables(word: str) -> int:
    """
    Estimate syllable count for a single word using a vowel-run heuristic.
    Silent trailing 'e' is accounted for.
    """
    word = word.lower().strip(".,!?;:'\"")
    if not word:
        return 0
    # Count vowel groups
    vowels = re.findall(r"[aeiouy]+", word)
    count = len(vowels)
    # Silent trailing 'e' — subtract one if word ends with 'e' and count > 1
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def estimate_syllables(lines: List[str]) -> List[dict]:
    """Return syllable count per line."""
    results = []
    for line in lines:
        ws = _words(line)
        per_word = {w: count_syllables(w) for w in ws}
        total = sum(per_word.values())
        results.append({
            "line": line,
            "syllables_per_word": per_word,
            "total_syllables": total,
        })
    return results


# ---------------------------------------------------------------------------
# 4. Structure Analysis
# ---------------------------------------------------------------------------

def analyze_structure(lines: List[str]) -> dict:
    """
    Detect repetition and symmetry patterns across lines.

    Repetition  – exact or near-exact duplicate lines.
    Symmetry    – the sequence of line-length buckets reads the same
                  forwards and backwards (mirror structure).
    """
    # Repetition
    normalised_lines = [_normalise(line) for line in lines]
    line_counts = Counter(normalised_lines)
    repeated = {line: cnt for line, cnt in line_counts.items() if cnt > 1}

    # Symmetry: bucket each line by length (short/medium/long)
    def bucket(line: str) -> str:
        n = len(line.split())
        if n <= 3:
            return "S"
        if n <= 7:
            return "M"
        return "L"

    length_profile = [bucket(line) for line in lines]
    is_symmetric = length_profile == length_profile[::-1]

    # Refrain detection: a line that appears 3+ times is likely a refrain
    refrains = [line for line, cnt in line_counts.items() if cnt >= 3]

    return {
        "repeated_lines": repeated,
        "repetition_count": len(repeated),
        "length_profile": length_profile,
        "is_symmetric": is_symmetric,
        "refrains": refrains,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(text: str) -> dict:
    """
    Full analysis pipeline for a piece of text (lyrics / poem).

    Parameters
    ----------
    text : str
        Multi-line string (lyrics, poem, etc.)

    Returns
    -------
    dict with keys: palindrome, rhymes, syllables, structure
    """
    # Split on newlines; ignore blank lines for most analyses
    raw_lines = text.splitlines()
    lines = [l for l in raw_lines if l.strip()]

    if not lines:
        return {
            "palindrome": {},
            "rhymes": {},
            "syllables": [],
            "structure": {},
        }

    return {
        "palindrome": detect_palindrome(lines),
        "rhymes": detect_rhymes(lines),
        "syllables": estimate_syllables(lines),
        "structure": analyze_structure(lines),
    }

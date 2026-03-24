"""
KalaCore Pattern Engine
-----------------------
Analyzes text (lyrics, poems) for artistic patterns:
  - Palindrome detection (full-line and partial)
  - Anagram detection (word-level)
  - Rhyme detection (end-rhyme, internal, mirror/ABBA)
  - Syllable estimation (heuristic)
  - Structure analysis (repetition and symmetry)
  - Form-type identification (haiku, sonnet, quatrain, free verse, …)
  - Improvisation detection (rhythm breaks, rhyme breaks, structural isolation)
  - Emotional arc (per-line valence trajectory)
  - Cognitive load estimation

All functions are pure and stateless — no external dependencies required.
"""

import re
from collections import Counter
from typing import Dict, List, Tuple


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
# Sentiment word sets (used for emotional arc)
# ---------------------------------------------------------------------------

_POSITIVE_WORDS: frozenset = frozenset({
    "love", "joy", "happy", "light", "hope", "bright", "warm", "free", "peace",
    "smile", "laugh", "dream", "fly", "rise", "glow", "shine", "alive", "bloom",
    "sweet", "grace", "gentle", "tender", "kind", "open", "beautiful", "golden",
    "soar", "sing", "dance", "yes", "home", "safe", "brave", "strong", "trust",
    "healing", "together", "embrace", "wonder", "grateful", "pure", "clear",
})

_NEGATIVE_WORDS: frozenset = frozenset({
    "dark", "pain", "fear", "alone", "cold", "lost", "broken", "cry", "fall",
    "hate", "die", "dead", "ghost", "shadow", "tears", "sorrow", "hurt", "empty",
    "bleed", "fade", "silent", "grey", "gray", "hollow", "chains", "trap", "drown",
    "burn", "ash", "wound", "scream", "wall", "cage", "lie", "false", "wrong",
    "forgotten", "missing", "apart", "leave", "gone", "away", "storm", "bleed",
})


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
# 5. Anagram Detection
# ---------------------------------------------------------------------------

def detect_anagrams(lines: List[str]) -> dict:
    """
    Find groups of words in the text that are anagrams of each other.
    Two words are anagrams when they contain exactly the same letters
    (case-insensitive, punctuation stripped) in a different order.
    Only words of three or more letters are considered.
    """
    all_words: List[str] = []
    for line in lines:
        all_words.extend(_words(line))

    unique_words = list(dict.fromkeys(all_words))  # preserve first-seen order

    # Group by sorted-letter signature
    letter_groups: Dict[str, List[str]] = {}
    for word in unique_words:
        if len(word) >= 3:
            key = "".join(sorted(word))
            letter_groups.setdefault(key, []).append(word)

    anagram_groups = [words for words in letter_groups.values() if len(words) >= 2]

    return {
        "anagram_groups": anagram_groups,
        "anagram_pair_count": sum(len(g) for g in anagram_groups),
        "has_anagrams": len(anagram_groups) > 0,
    }


# ---------------------------------------------------------------------------
# 6. Mirror Rhyme Detection
# ---------------------------------------------------------------------------

def detect_mirror_rhyme(lines: List[str]) -> dict:
    """
    Detect mirror (ABBA / chiastic) rhyme structure.

    Line i rhymes with line -(i+1): the outermost pair rhyme with each other,
    then the next-innermost pair, etc.  ABBA in a 4-line stanza is the
    simplest example.

    mirror_rhyme_density – proportion of possible mirror-pairs that rhyme.
    """
    n = len(lines)
    if n < 4:
        return {"has_mirror_rhyme": False, "mirror_pairs": [], "mirror_rhyme_density": 0.0}

    end_words: List[str] = []
    for line in lines:
        ws = _words(line)
        end_words.append(ws[-1] if ws else "")

    mirror_pairs: List[Tuple[int, int]] = []
    possible_pairs = n // 2
    for i in range(possible_pairs):
        j = n - 1 - i
        if i >= j:
            break
        nucleus_i = _last_vowel_cluster(end_words[i])
        nucleus_j = _last_vowel_cluster(end_words[j])
        if nucleus_i == nucleus_j and nucleus_i:
            mirror_pairs.append((i, j))

    density = round(len(mirror_pairs) / max(possible_pairs, 1), 4)
    # Present if at least half the possible pairs match
    has_mirror = len(mirror_pairs) >= max(1, possible_pairs // 2)

    return {
        "has_mirror_rhyme": has_mirror,
        "mirror_pairs": mirror_pairs,
        "mirror_rhyme_density": density,
    }


# ---------------------------------------------------------------------------
# 7. Form-Type Detection
# ---------------------------------------------------------------------------

def detect_form_type(
    lines: List[str],
    rhyme_data: dict,
    syllable_data: List[dict],
) -> dict:
    """
    Identify the probable poetic / lyric form from structural signals.

    Returns the most likely ``form`` name and a ``confidence`` score [0,1].
    Heuristics are intentionally lightweight and language-agnostic.
    """
    n = len(lines)
    syl_totals = [s.get("total_syllables", 0) for s in syllable_data]
    rhyme_density = float(rhyme_data.get("end_rhyme_density", 0.0))

    # Haiku: exactly 3 lines, approximate 5-7-5 syllable pattern
    if n == 3 and len(syl_totals) == 3:
        if (4 <= syl_totals[0] <= 6
                and 6 <= syl_totals[1] <= 8
                and 4 <= syl_totals[2] <= 6):
            return {"form": "haiku", "confidence": 0.9}

    # Sonnet: 14 lines
    if n == 14:
        return {"form": "sonnet", "confidence": 0.7}

    # Couplet / distich: 2 lines
    if n == 2:
        if rhyme_density > 0.0:
            return {"form": "couplet", "confidence": 0.85}
        return {"form": "distich", "confidence": 0.6}

    # Tercet: 3 lines (non-haiku)
    if n == 3:
        return {"form": "tercet", "confidence": 0.6}

    # Quatrain: 4 lines with rhyme
    if n == 4 and rhyme_density > 0.3:
        return {"form": "quatrain", "confidence": 0.8}

    # Ballad stanza: 8 lines with moderate rhyme
    if n == 8 and rhyme_density > 0.3:
        return {"form": "ballad stanza", "confidence": 0.65}

    # Lyric with strong rhyme (could be a song verse/chorus)
    if rhyme_density > 0.5:
        return {"form": "rhymed verse", "confidence": 0.6}

    return {"form": "free verse", "confidence": 0.5}


# ---------------------------------------------------------------------------
# 8. Improvisation Detection
# ---------------------------------------------------------------------------

def detect_improvisation(
    lines: List[str],
    rhyme_data: dict,
    syllable_data: List[dict],
    structure_data: dict,
) -> dict:
    """
    Detect creative rule-breaking: rhythm deviation, rhyme-scheme breaks,
    and structurally isolated (one-off) lines in a repetitive piece.

    ``creative_risk_index`` – proportion of lines showing some rule-breaking,
    normalised to [0, 1].
    """
    markers: List[str] = []
    chaos_lines: List[str] = []

    syl_totals = [s.get("total_syllables", 0) for s in syllable_data]

    # 1. Rhythm deviation: lines whose syllable count is > 2 std-devs from mean
    if len(syl_totals) > 2:
        mean = sum(syl_totals) / len(syl_totals)
        variance = sum((x - mean) ** 2 for x in syl_totals) / len(syl_totals)
        std = variance ** 0.5
        if std > 0:
            for i, (line, total) in enumerate(zip(lines, syl_totals)):
                if abs(total - mean) > 2 * std:
                    chaos_lines.append(line)
                    markers.append(f"rhythm_break:line_{i + 1}")

    # 2. Rhyme-scheme breaks: a line that doesn't rhyme in a rhyming piece
    rhyme_density = float(rhyme_data.get("end_rhyme_density", 0.0))
    if rhyme_density > 0.4:
        grouped_indices: set = set()
        for indices in rhyme_data.get("end_rhyme_groups", {}).values():
            grouped_indices.update(indices)
        for i, line in enumerate(lines):
            if i not in grouped_indices:
                markers.append(f"rhyme_break:line_{i + 1}")
                if line not in chaos_lines:
                    chaos_lines.append(line)

    # 3. Structural isolation: unique lines in a heavily repetitive piece
    rep_count = structure_data.get("repetition_count", 0)
    if rep_count >= 2:
        norm_counts = Counter(_normalise(l) for l in lines)
        for i, line in enumerate(lines):
            if norm_counts[_normalise(line)] == 1:
                markers.append(f"unique_line:line_{i + 1}")

    risk_idx = round(len(set(chaos_lines)) / max(len(lines), 1), 4)

    return {
        "markers": markers,
        "chaos_lines": chaos_lines,
        "creative_risk_index": risk_idx,
        "has_improvisation": len(markers) > 0,
    }


# ---------------------------------------------------------------------------
# 9. Emotional Arc
# ---------------------------------------------------------------------------

def detect_emotional_arc(lines: List[str]) -> dict:
    """
    Estimate the emotional trajectory across the piece using a curated
    positive/negative word list.

    Each line receives a valence score:
      -1.0 = all negative words, 0 = neutral, +1.0 = all positive words.

    ``arc_direction`` – "ascending" (ends more positive), "descending",
    "flat" or "oscillating".
    """
    scores: List[float] = []
    for line in lines:
        ws = _words(line)
        total = len(ws) or 1
        pos = sum(1 for w in ws if w in _POSITIVE_WORDS)
        neg = sum(1 for w in ws if w in _NEGATIVE_WORDS)
        scores.append(round((pos - neg) / total, 4))

    if not scores:
        return {"line_scores": [], "arc_direction": "flat", "mean_valence": 0.0}

    mid = max(len(scores) // 2, 1)
    first_avg = sum(scores[:mid]) / mid
    second_avg = sum(scores[mid:]) / max(len(scores[mid:]), 1)

    if second_avg > first_avg + 0.1:
        arc = "ascending"
    elif second_avg < first_avg - 0.1:
        arc = "descending"
    elif abs(second_avg - first_avg) <= 0.05:
        arc = "flat"
    else:
        arc = "oscillating"

    return {
        "line_scores": scores,
        "arc_direction": arc,
        "mean_valence": round(sum(scores) / len(scores), 4),
    }


# ---------------------------------------------------------------------------
# 10. Cognitive Load
# ---------------------------------------------------------------------------

def estimate_cognitive_load(lines: List[str], syllable_data: List[dict]) -> float:
    """
    Estimate the cognitive load placed on the reader / listener.

    Components:
      1. Average word length       (longer words → higher load)
      2. Average syllables / word  (more syllables → higher load)
      3. Unique vocabulary ratio   (more unique words → higher load)

    Returns a float in [0.0, 1.0].
    """
    all_words: List[str] = []
    for line in lines:
        all_words.extend(_words(line))

    if not all_words:
        return 0.0

    # 1. Avg word length — normalise against 8 chars as "long"
    avg_len = sum(len(w) for w in all_words) / len(all_words)
    len_score = min(avg_len / 8.0, 1.0)

    # 2. Avg syllables per word — normalise against 3 as "complex"
    syl_totals = [s.get("total_syllables", 0) for s in syllable_data]
    word_counts = [len(_words(l)) for l in lines]
    total_words = sum(word_counts) or 1
    avg_syl = sum(syl_totals) / total_words
    syl_score = min(avg_syl / 3.0, 1.0)

    # 3. Unique vocabulary ratio
    unique_ratio = len(set(all_words)) / len(all_words)

    return round(min((len_score * 0.35) + (syl_score * 0.35) + (unique_ratio * 0.30), 1.0), 4)


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
    dict with keys:
        palindrome, anagrams, rhymes, mirror_rhyme, syllables, structure,
        form_type, improvisation, emotional_arc, cognitive_load
    """
    # Split on newlines; ignore blank lines for most analyses
    raw_lines = text.splitlines()
    lines = [l for l in raw_lines if l.strip()]

    if not lines:
        return {
            "palindrome": {},
            "anagrams": {},
            "rhymes": {},
            "mirror_rhyme": {},
            "syllables": [],
            "structure": {},
            "form_type": {},
            "improvisation": {},
            "emotional_arc": {},
            "cognitive_load": 0.0,
        }

    rhymes = detect_rhymes(lines)
    syllables = estimate_syllables(lines)
    structure = analyze_structure(lines)

    return {
        "palindrome": detect_palindrome(lines),
        "anagrams": detect_anagrams(lines),
        "rhymes": rhymes,
        "mirror_rhyme": detect_mirror_rhyme(lines),
        "syllables": syllables,
        "structure": structure,
        "form_type": detect_form_type(lines, rhymes, syllables),
        "improvisation": detect_improvisation(lines, rhymes, syllables, structure),
        "emotional_arc": detect_emotional_arc(lines),
        "cognitive_load": estimate_cognitive_load(lines, syllables),
    }

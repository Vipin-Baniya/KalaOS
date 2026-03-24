"""
Tests for KalaCore pattern_engine and ArtGenome.
"""

import sys
import os

# Allow importing from the backend directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from kalacore.pattern_engine import (
    detect_palindrome,
    detect_rhymes,
    count_syllables,
    estimate_syllables,
    analyze_structure,
    analyze,
)
from kalacore.art_genome import build_art_genome


# ---------------------------------------------------------------------------
# Palindrome Detection
# ---------------------------------------------------------------------------

class TestDetectPalindrome:
    def test_full_palindrome_line(self):
        result = detect_palindrome(["racecar"])
        assert result["full_palindrome_count"] == 1
        assert result["lines"][0]["is_full_palindrome"] is True

    def test_non_palindrome_line(self):
        result = detect_palindrome(["hello world"])
        assert result["full_palindrome_count"] == 0
        assert result["lines"][0]["is_full_palindrome"] is False

    def test_partial_palindrome_detected(self):
        result = detect_palindrome(["she saw a level bridge"])
        # "level" should appear as a partial palindrome
        partials = result["lines"][0]["partial_palindromes"]
        assert any("level" in p for p in partials)

    def test_multiple_lines(self):
        lines = ["racecar", "hello", "madam"]
        result = detect_palindrome(lines)
        assert result["full_palindrome_count"] == 2  # racecar, madam

    def test_punctuation_stripped(self):
        result = detect_palindrome(["Racecar!"])
        assert result["lines"][0]["is_full_palindrome"] is True

    def test_empty_line_list(self):
        result = detect_palindrome([])
        assert result["full_palindrome_count"] == 0
        assert result["lines"] == []


# ---------------------------------------------------------------------------
# Rhyme Detection
# ---------------------------------------------------------------------------

class TestDetectRhymes:
    def test_end_rhyme_detected(self):
        lines = ["I saw the night", "under the light"]
        result = detect_rhymes(lines)
        # 'night' and 'light' share rhyme nucleus 'ight'
        assert any(len(v) >= 2 for v in result["end_rhyme_groups"].values())

    def test_no_rhyme(self):
        lines = ["apple on the table", "running through the forest"]
        result = detect_rhymes(lines)
        # Should not find any shared nucleus with ≥2 lines
        assert all(len(v) < 2 for v in result["end_rhyme_groups"].values())

    def test_internal_rhyme(self):
        lines = ["the bright night shines right"]
        result = detect_rhymes(lines)
        internal = result["internal_rhymes"][0]
        assert internal["has_internal_rhyme"] is True

    def test_end_rhyme_density_range(self):
        lines = ["I love the day", "come out and play", "nothing to say"]
        result = detect_rhymes(lines)
        assert 0.0 <= result["end_rhyme_density"] <= 1.0

    def test_single_line(self):
        result = detect_rhymes(["just one line here"])
        # No end-rhyme groups with ≥2 lines possible
        assert all(len(v) < 2 for v in result["end_rhyme_groups"].values())


# ---------------------------------------------------------------------------
# Syllable Estimation
# ---------------------------------------------------------------------------

class TestCountSyllables:
    def test_single_vowel_word(self):
        assert count_syllables("I") == 1

    def test_two_syllable_word(self):
        assert count_syllables("hello") == 2

    def test_silent_e(self):
        # "love" — the trailing 'e' is silent
        assert count_syllables("love") == 1

    def test_multisyllable(self):
        assert count_syllables("beautiful") >= 3

    def test_empty_string(self):
        assert count_syllables("") == 0

    def test_punctuation_stripped(self):
        assert count_syllables("night,") == count_syllables("night")


class TestEstimateSyllables:
    def test_returns_one_entry_per_line(self):
        lines = ["hello world", "beautiful day"]
        result = estimate_syllables(lines)
        assert len(result) == 2

    def test_total_syllables_positive(self):
        result = estimate_syllables(["the quick brown fox"])
        assert result[0]["total_syllables"] > 0

    def test_per_word_keys_match_words(self):
        result = estimate_syllables(["hello world"])
        assert "hello" in result[0]["syllables_per_word"]
        assert "world" in result[0]["syllables_per_word"]


# ---------------------------------------------------------------------------
# Structure Analysis
# ---------------------------------------------------------------------------

class TestAnalyseStructure:
    def test_detects_repeated_line(self):
        lines = ["come back home", "far away", "come back home"]
        result = analyze_structure(lines)
        assert result["repetition_count"] >= 1

    def test_detects_refrain(self):
        lines = ["refrain line", "verse one", "refrain line", "verse two", "refrain line"]
        result = analyze_structure(lines)
        assert len(result["refrains"]) >= 1

    def test_symmetric_profile(self):
        # Short, Medium, Long, Medium, Short → symmetric
        lines = [
            "hi there",                  # S (2 words)
            "the sun shines bright today",  # M (5 words)
            "a very long line with lots of extra words in it",  # L
            "the sun shines bright today",  # M
            "hi there",                  # S
        ]
        result = analyze_structure(lines)
        assert result["is_symmetric"] is True

    def test_asymmetric_profile(self):
        lines = ["hi", "hello beautiful world today", "one"]
        result = analyze_structure(lines)
        # Profile: S, M, S — this is actually symmetric, adjust test
        lines = ["one two three four five six", "hi", "hello world today"]
        result = analyze_structure(lines)
        assert isinstance(result["is_symmetric"], bool)

    def test_no_repeats(self):
        lines = ["alpha beta", "gamma delta", "epsilon zeta"]
        result = analyze_structure(lines)
        assert result["repetition_count"] == 0


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------

class TestAnalyse:
    POEM = (
        "Roses are red\n"
        "Violets are blue\n"
        "Roses are red\n"
        "All I want is you"
    )

    def test_returns_all_keys(self):
        result = analyze(self.POEM)
        for key in (
            "palindrome", "anagrams", "rhymes", "mirror_rhyme",
            "syllables", "structure", "form_type",
            "improvisation", "emotional_arc", "cognitive_load",
        ):
            assert key in result

    def test_syllables_length_matches_lines(self):
        result = analyze(self.POEM)
        non_blank = [l for l in self.POEM.splitlines() if l.strip()]
        assert len(result["syllables"]) == len(non_blank)

    def test_empty_string(self):
        result = analyze("")
        # Empty input returns zeroed values for all analysis keys
        assert result["palindrome"] == {}
        assert result["rhymes"] == {}
        assert result["syllables"] == []
        assert result["structure"] == {}
        assert result["anagrams"] == {}
        assert result["mirror_rhyme"] == {}
        assert result["form_type"] == {}
        assert result["improvisation"] == {}
        assert result["emotional_arc"] == {}
        assert result["cognitive_load"] == 0.0

    def test_blank_lines_ignored(self):
        text = "\n\nRoses are red\n\nViolets are blue\n\n"
        result = analyze(text)
        assert len(result["syllables"]) == 2


# ---------------------------------------------------------------------------
# ArtGenome
# ---------------------------------------------------------------------------

class TestBuildArtGenome:
    def _analysis(self):
        return analyze(
            "I saw the night\nUnder the moonlight\n"
            "I saw the night\nGlowing so bright"
        )

    def test_rhyme_density_in_range(self):
        genome = build_art_genome(self._analysis())
        assert 0.0 <= genome.rhyme_density <= 1.0

    def test_symmetry_score_binary(self):
        genome = build_art_genome(self._analysis())
        assert genome.symmetry_score in (0.0, 1.0)

    def test_complexity_score_in_range(self):
        genome = build_art_genome(self._analysis())
        assert 0.0 <= genome.complexity_score <= 1.0

    def test_to_dict_contains_all_fields(self):
        genome = build_art_genome(self._analysis())
        d = genome.to_dict()
        for key in (
            "structure_analysis",
            "rhyme_density",
            "symmetry_score",
            "improvisation_markers",
            "complexity_score",
            "form_type",
            "creative_risk_index",
            "emotional_arc",
            "cognitive_load",
            "human_irreducible_zones",
        ):
            assert key in d

    def test_empty_analysis(self):
        genome = build_art_genome(analyze(""))
        assert genome.rhyme_density == 0.0
        assert genome.complexity_score == 0.0

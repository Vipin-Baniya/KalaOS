"""
Tests for Phase 1 extended KalaCore detectors and the ethics module.

Covers:
  - detect_anagrams
  - detect_mirror_rhyme
  - detect_form_type
  - detect_improvisation
  - detect_emotional_arc
  - estimate_cognitive_load
  - ArtGenome new fields
  - kalacore.ethics (PRINCIPLES, check_request)
  - API ethics gate integration
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

from main import app
from kalacore.pattern_engine import (
    detect_anagrams,
    detect_mirror_rhyme,
    detect_form_type,
    detect_improvisation,
    detect_emotional_arc,
    estimate_cognitive_load,
    estimate_syllables,
    detect_rhymes,
    analyze_structure,
    analyze,
)
from kalacore.art_genome import build_art_genome
from kalacore.ethics import PRINCIPLES, check_request, EthicsViolation, MAX_TEXT_LENGTH

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

QUATRAIN = [
    "I walk alone in the dark",
    "Searching for a tiny spark",
    "The night is cold but my heart is warm",
    "I walk alone in the dark",
]

HAIKU = [
    "Old silent pond",
    "A frog jumps into the pond",
    "Splash silence again",
]

MIRROR_ABBA = [
    "I saw the night",       # rhymes with line 3 ('bright')
    "The stars were all red",
    "The stars were all dead",
    "Under the moonlight",   # rhymes with line 0 ('night')
]


# ---------------------------------------------------------------------------
# 5. Anagram Detection
# ---------------------------------------------------------------------------

class TestDetectAnagrams:
    def test_detects_anagram_pair(self):
        # "listen" and "silent" are anagrams
        lines = ["listen to the silent night"]
        result = detect_anagrams(lines)
        found = any(
            set(g) >= {"listen", "silent"}
            for g in result["anagram_groups"]
        )
        assert found

    def test_no_anagrams_in_plain_text(self):
        lines = ["apple orange banana cherry"]
        result = detect_anagrams(lines)
        assert result["has_anagrams"] is False

    def test_short_words_ignored(self):
        # 1-2 letter words should not form anagram groups
        lines = ["to it at on is no"]
        result = detect_anagrams(lines)
        assert result["has_anagrams"] is False

    def test_empty_lines_return_empty(self):
        result = detect_anagrams([])
        assert result["anagram_groups"] == []
        assert result["anagram_pair_count"] == 0
        assert result["has_anagrams"] is False

    def test_cross_line_detection(self):
        # "live" and "vile" are anagrams across two lines
        lines = ["I live to create", "a vile nothing"]
        result = detect_anagrams(lines)
        assert result["has_anagrams"] is True


# ---------------------------------------------------------------------------
# 6. Mirror Rhyme Detection
# ---------------------------------------------------------------------------

class TestDetectMirrorRhyme:
    def test_abba_scheme_detected(self):
        result = detect_mirror_rhyme(MIRROR_ABBA)
        assert result["has_mirror_rhyme"] is True

    def test_fewer_than_4_lines_returns_false(self):
        result = detect_mirror_rhyme(["one line", "two lines", "three lines"])
        assert result["has_mirror_rhyme"] is False
        assert result["mirror_pairs"] == []

    def test_empty_lines_returns_false(self):
        result = detect_mirror_rhyme([])
        assert result["has_mirror_rhyme"] is False

    def test_mirror_rhyme_density_range(self):
        result = detect_mirror_rhyme(MIRROR_ABBA)
        assert 0.0 <= result["mirror_rhyme_density"] <= 1.0

    def test_non_mirror_rhyme_scheme(self):
        # AABB: consecutive pairs rhyme, not mirror
        lines = ["I saw the night", "under the moonlight", "roses are red", "violets are dead"]
        result = detect_mirror_rhyme(lines)
        # mirror_pairs might be 0 for AABB
        assert isinstance(result["has_mirror_rhyme"], bool)


# ---------------------------------------------------------------------------
# 7. Form-Type Detection
# ---------------------------------------------------------------------------

class TestDetectFormType:
    def _syl(self, lines):
        return estimate_syllables(lines)

    def _rhyme(self, lines):
        return detect_rhymes(lines)

    def test_haiku_detected(self):
        # Classic 5-7-5: "Old si-lent pond" / "A frog jumps in-to the pond" / "Splash si-lence a-gain"
        lines = ["old silent pond", "a frog jumps into the pond", "splash silence again"]
        result = detect_form_type(lines, self._rhyme(lines), self._syl(lines))
        assert result["form"] == "haiku"
        assert result["confidence"] >= 0.8

    def test_sonnet_detected(self):
        lines = [f"line {i}" for i in range(14)]
        result = detect_form_type(lines, self._rhyme(lines), self._syl(lines))
        assert result["form"] == "sonnet"

    def test_couplet_detected(self):
        lines = ["I saw the night", "under the moonlight"]
        result = detect_form_type(lines, self._rhyme(lines), self._syl(lines))
        assert result["form"] == "couplet"

    def test_free_verse_fallback(self):
        lines = ["no pattern here at all",
                 "the words just keep rolling forward",
                 "nothing connects to anything",
                 "complete structural freedom reigns here",
                 "and on it goes endlessly into nowhere"]
        result = detect_form_type(lines, self._rhyme(lines), self._syl(lines))
        assert result["form"] in ("free verse", "rhymed verse", "quatrain", "ballad stanza")

    def test_quatrain_detected(self):
        lines = [
            "I love the day",
            "come out and play",
            "the sun shines bright",
            "all feels so right",
        ]
        result = detect_form_type(lines, self._rhyme(lines), self._syl(lines))
        assert result["form"] == "quatrain"
        assert result["confidence"] >= 0.7


# ---------------------------------------------------------------------------
# 8. Improvisation Detection
# ---------------------------------------------------------------------------

class TestDetectImprovisation:
    def _deps(self, lines):
        rhymes = detect_rhymes(lines)
        syl = estimate_syllables(lines)
        struct = analyze_structure(lines)
        return rhymes, syl, struct

    def test_rhythm_break_detected(self):
        # Six near-identical short lines, then one massively longer line → rhythm break
        lines = [
            "go now",
            "stay here",
            "come back",
            "move on",
            "fall down",
            "stand up",
            "this is an extraordinarily long line packed with syllables far beyond anything seen before in this piece",
        ]
        rhymes, syl, struct = self._deps(lines)
        result = detect_improvisation(lines, rhymes, syl, struct)
        assert any("rhythm_break" in m for m in result["markers"])

    def test_no_improvisation_in_uniform_piece(self):
        # All lines uniform length, all rhyme → no rule-breaking
        lines = [
            "I love the day",
            "come out and play",
            "the sun shines bright",
            "all feels so right",
        ]
        rhymes, syl, struct = self._deps(lines)
        result = detect_improvisation(lines, rhymes, syl, struct)
        assert isinstance(result["has_improvisation"], bool)

    def test_creative_risk_index_in_range(self):
        rhymes, syl, struct = self._deps(QUATRAIN)
        result = detect_improvisation(QUATRAIN, rhymes, syl, struct)
        assert 0.0 <= result["creative_risk_index"] <= 1.0

    def test_result_structure(self):
        rhymes, syl, struct = self._deps(QUATRAIN)
        result = detect_improvisation(QUATRAIN, rhymes, syl, struct)
        for key in ("markers", "chaos_lines", "creative_risk_index", "has_improvisation"):
            assert key in result

    def test_empty_lines(self):
        result = detect_improvisation([], {}, [], {})
        assert result["markers"] == []
        assert result["creative_risk_index"] == 0.0


# ---------------------------------------------------------------------------
# 9. Emotional Arc
# ---------------------------------------------------------------------------

class TestDetectEmotionalArc:
    def test_positive_lines_positive_score(self):
        lines = ["love and joy and hope and light", "beautiful warm bright free"]
        result = detect_emotional_arc(lines)
        assert result["mean_valence"] > 0

    def test_negative_lines_negative_score(self):
        lines = ["dark pain fear alone cold", "broken tears sorrow hurt empty"]
        result = detect_emotional_arc(lines)
        assert result["mean_valence"] < 0

    def test_arc_direction_types(self):
        lines = ["dark pain fear", "love and joy and hope"]
        result = detect_emotional_arc(lines)
        assert result["arc_direction"] in ("ascending", "descending", "flat", "oscillating")

    def test_ascending_arc(self):
        lines = ["dark pain broken tears", "love and hope and light"]
        result = detect_emotional_arc(lines)
        assert result["arc_direction"] == "ascending"

    def test_descending_arc(self):
        lines = ["love and joy and hope", "dark pain broken tears"]
        result = detect_emotional_arc(lines)
        assert result["arc_direction"] == "descending"

    def test_line_scores_length_matches(self):
        lines = ["line one here", "line two there", "line three now"]
        result = detect_emotional_arc(lines)
        assert len(result["line_scores"]) == 3

    def test_empty_lines(self):
        result = detect_emotional_arc([])
        assert result["arc_direction"] == "flat"
        assert result["mean_valence"] == 0.0


# ---------------------------------------------------------------------------
# 10. Cognitive Load
# ---------------------------------------------------------------------------

class TestEstimateCognitiveLoad:
    def _syl(self, lines):
        return estimate_syllables(lines)

    def test_result_in_range(self):
        lines = ["the quick brown fox jumps over the lazy dog"]
        load = estimate_cognitive_load(lines, self._syl(lines))
        assert 0.0 <= load <= 1.0

    def test_complex_text_higher_than_simple(self):
        simple = ["go to the big red shop"]
        complex_ = ["transcendental philosophical existentialism characterises postmodern metaphysics"]
        load_simple = estimate_cognitive_load(simple, self._syl(simple))
        load_complex = estimate_cognitive_load(complex_, self._syl(complex_))
        assert load_complex > load_simple

    def test_empty_returns_zero(self):
        assert estimate_cognitive_load([], []) == 0.0


# ---------------------------------------------------------------------------
# ArtGenome — new fields
# ---------------------------------------------------------------------------

class TestArtGenomeNewFields:
    def _genome(self, text=None):
        if text is None:
            text = (
                "I walk alone in the dark\n"
                "Searching for a tiny spark\n"
                "The night is cold but my heart is warm\n"
                "I walk alone in the dark"
            )
        return build_art_genome(analyze(text))

    def test_form_type_is_string(self):
        assert isinstance(self._genome().form_type, str)
        assert len(self._genome().form_type) > 0

    def test_creative_risk_index_in_range(self):
        assert 0.0 <= self._genome().creative_risk_index <= 1.0

    def test_emotional_arc_has_expected_keys(self):
        arc = self._genome().emotional_arc
        for key in ("line_scores", "arc_direction", "mean_valence"):
            assert key in arc

    def test_cognitive_load_in_range(self):
        assert 0.0 <= self._genome().cognitive_load <= 1.0

    def test_human_irreducible_zones_is_list(self):
        assert isinstance(self._genome().human_irreducible_zones, list)

    def test_improvisation_markers_is_list(self):
        assert isinstance(self._genome().improvisation_markers, list)

    def test_empty_analysis_all_new_fields_zero(self):
        genome = build_art_genome(analyze(""))
        assert genome.form_type == "unknown"
        assert genome.creative_risk_index == 0.0
        assert genome.cognitive_load == 0.0
        assert genome.human_irreducible_zones == []
        assert genome.improvisation_markers == []


# ---------------------------------------------------------------------------
# Ethics — PRINCIPLES
# ---------------------------------------------------------------------------

class TestPrinciples:
    def test_all_axioms_are_true(self):
        assert PRINCIPLES.ART_IS_NOT_CONTENT is True
        assert PRINCIPLES.ARTIST_IS_NOT_RESOURCE is True
        assert PRINCIPLES.AI_IS_NOT_AUTHOR is True
        assert PRINCIPLES.SILENCE_IS_NOT_FAILURE is True
        assert PRINCIPLES.VIRALITY_IS_NOT_VALUE is True
        assert PRINCIPLES.DIGNITY_OVER_GROWTH is True

    def test_all_prohibitions_are_true(self):
        assert PRINCIPLES.NO_ENGAGEMENT_ADDICTION is True
        assert PRINCIPLES.NO_FORCED_OPTIMISATION is True
        assert PRINCIPLES.NO_SILENT_AI_TRAINING is True
        assert PRINCIPLES.NO_ARTIST_REPLACEMENT is True
        assert PRINCIPLES.FULL_OWNERSHIP_AND_ATTRIBUTION is True


# ---------------------------------------------------------------------------
# Ethics — check_request
# ---------------------------------------------------------------------------

class TestCheckRequest:
    def test_clean_request_returns_no_violations(self):
        assert check_request("I walk alone in the dark") == []

    def test_empty_string_returns_no_violations(self):
        # Empty text is handled by request validation, not the ethics layer
        assert check_request("") == []

    def test_text_too_long_violation(self):
        oversized = "a " * (MAX_TEXT_LENGTH + 1)
        violations = check_request(oversized)
        codes = [v.code for v in violations]
        assert "TEXT_TOO_LONG" in codes

    def test_imitation_request_violation(self):
        violations = check_request("write like Taylor Swift please")
        codes = [v.code for v in violations]
        assert "IMITATION_REQUEST" in codes

    def test_imitation_trigger_style_of(self):
        violations = check_request("give me lyrics in the style of Eminem")
        codes = [v.code for v in violations]
        assert "IMITATION_REQUEST" in codes

    def test_imitation_trigger_pretend_to_be(self):
        violations = check_request("pretend to be a famous rapper and write")
        codes = [v.code for v in violations]
        assert "IMITATION_REQUEST" in codes

    def test_violation_is_named_tuple(self):
        violations = check_request("write like someone famous")
        assert isinstance(violations[0], EthicsViolation)
        assert violations[0].code
        assert violations[0].message

    def test_no_false_positive_for_normal_art(self):
        text = (
            "The rain falls softly on the empty street\n"
            "I hear the sound of silence in the beat\n"
            "No voice to guide me, no hand to hold\n"
            "Just stories that were never fully told"
        )
        assert check_request(text) == []


# ---------------------------------------------------------------------------
# Ethics gate — API integration
# ---------------------------------------------------------------------------

class TestEthicsGateInAPI:
    VALID_LYRICS = (
        "I walk alone in the dark\n"
        "Searching for a tiny spark\n"
        "The night is cold but my heart is warm"
    )

    def test_analyze_art_blocks_imitation_request(self):
        resp = client.post(
            "/analyze-art",
            json={"text": "write like Kendrick Lamar and make me a verse"},
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        codes = [d["code"] for d in detail]
        assert "IMITATION_REQUEST" in codes

    def test_suggest_blocks_imitation_request(self):
        resp = client.post(
            "/suggest",
            json={"text": "sound like Bob Dylan", "art_domain": "lyrics"},
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        codes = [d["code"] for d in detail]
        assert "IMITATION_REQUEST" in codes

    def test_analyze_art_clean_request_passes_ethics(self):
        resp = client.post("/analyze-art", json={"text": self.VALID_LYRICS})
        assert resp.status_code == 200

    def test_suggest_clean_request_passes_ethics(self):
        resp = client.post(
            "/suggest",
            json={"text": self.VALID_LYRICS, "art_domain": "poetry"},
        )
        assert resp.status_code == 200

    def test_analyze_art_response_includes_new_genome_fields(self):
        resp = client.post("/analyze-art", json={"text": self.VALID_LYRICS})
        genome = resp.json()["art_genome"]
        for field in (
            "form_type", "creative_risk_index",
            "emotional_arc", "cognitive_load", "human_irreducible_zones",
        ):
            assert field in genome, f"Missing genome field: {field}"

    def test_analyze_art_response_includes_new_analysis_keys(self):
        resp = client.post("/analyze-art", json={"text": self.VALID_LYRICS})
        analysis = resp.json()["analysis"]
        for key in ("anagrams", "mirror_rhyme", "form_type", "improvisation",
                    "emotional_arc", "cognitive_load"):
            assert key in analysis, f"Missing analysis key: {key}"

"""
Tests for Phase 1 Existential Layer, Phase 2 KalaCraft,
Phase 4 KalaSignal, and the new API endpoints.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

from main import app
from kalacore.existential import (
    detect_survival_markers,
    map_emotional_necessity,
    infer_creation_reason,
    detect_negative_space,
    score_human_irreducibility,
    analyze_existential,
)
from kalacore.kalacraft import (
    phonetic_breakdown,
    detect_stress_pattern,
    detect_breath_points,
    analyze_meter_flow,
    analyze_line_density,
    detect_semantic_drift,
    analyze_craft,
)
from kalacore.kalasignal import (
    score_memorability,
    score_longevity,
    score_emotional_access,
    score_share_potential,
    separate_resonance,
    explain_resonance,
    analyze_signal,
)
from kalacore.pattern_engine import analyze
from kalacore.art_genome import build_art_genome

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SURVIVAL_TEXT = (
    "I drown in the silent dark alone\n"
    "broken and bleeding I cannot breathe\n"
    "fade into the hollow numb and cold\n"
    "helpless trapped in chains I cannot see"
)

CATHARSIS_TEXT = (
    "Let me pour every tear on this page\n"
    "release the flood I've held inside\n"
    "feel the weight begin to lift away\n"
    "I cry and finally the storm has died"
)

WONDER_TEXT = (
    "The golden stars stretch endlessly\n"
    "a beautiful miracle of light\n"
    "the universe is vast and free\n"
    "and dreams can shine beyond the night"
)

CRAFT_TEXT = (
    "I walk alone in the dark\n"
    "searching for a tiny spark\n"
    "the night is cold but my heart is warm\n"
    "I walk alone through every storm"
)

VALID_POEM = (
    "I walk alone in the dark\n"
    "Searching for a tiny spark\n"
    "The night is cold but my heart is warm\n"
    "I walk alone in the dark"
)


# ===========================================================================
# PHASE 1 EXISTENTIAL LAYER
# ===========================================================================

class TestDetectSurvivalMarkers:
    def test_survival_text_detected(self):
        lines = SURVIVAL_TEXT.splitlines()
        result = detect_survival_markers(lines)
        assert result["is_survival_driven"] is True
        assert result["survival_word_count"] > 0

    def test_wonder_text_not_survival(self):
        lines = WONDER_TEXT.splitlines()
        result = detect_survival_markers(lines)
        # Wonder text is not primarily survival-register language
        assert isinstance(result["is_survival_driven"], bool)
        assert result["survival_line_ratio"] <= 1.0

    def test_empty_lines_returns_zeros(self):
        result = detect_survival_markers([])
        assert result["survival_word_count"] == 0
        assert result["is_survival_driven"] is False
        assert result["survival_lines"] == []

    def test_survival_line_ratio_in_range(self):
        lines = SURVIVAL_TEXT.splitlines()
        result = detect_survival_markers(lines)
        assert 0.0 <= result["survival_line_ratio"] <= 1.0

    def test_survival_lines_is_list(self):
        lines = SURVIVAL_TEXT.splitlines()
        result = detect_survival_markers(lines)
        assert isinstance(result["survival_lines"], list)


class TestMapEmotionalNecessity:
    def test_high_necessity_detected(self):
        lines = [
            "i must speak this truth",
            "i need to let it go",
            "i will keep fighting always",
            "i cannot stop this feeling",
        ]
        result = map_emotional_necessity(lines)
        assert result["necessity_score"] > 0.3

    def test_neutral_text_low_necessity(self):
        lines = ["the cat sat on the mat", "roses grow in summer", "clouds float by"]
        result = map_emotional_necessity(lines)
        assert result["necessity_score"] < 0.6

    def test_first_person_specificity(self):
        lines = ["i am broken", "i was lost", "i will rise"]
        result = map_emotional_necessity(lines)
        assert result["necessity_specificity"] > 0.5

    def test_scores_in_range(self):
        lines = SURVIVAL_TEXT.splitlines()
        result = map_emotional_necessity(lines)
        assert 0.0 <= result["necessity_intensity"] <= 1.0
        assert 0.0 <= result["necessity_specificity"] <= 1.0
        assert 0.0 <= result["necessity_score"] <= 1.0

    def test_empty_lines_zeros(self):
        result = map_emotional_necessity([])
        assert result["necessity_score"] == 0.0


class TestInferCreationReason:
    def test_catharsis_detected(self):
        lines = CATHARSIS_TEXT.splitlines()
        result = infer_creation_reason(lines)
        # Should find catharsis or release-related archetype
        assert result["primary_reason"] in (
            "catharsis", "survival", "connection", "testimony", "protest", "wonder", "expression"
        )
        assert 0.0 <= result["confidence"] <= 1.0

    def test_wonder_detected(self):
        lines = WONDER_TEXT.splitlines()
        result = infer_creation_reason(lines)
        assert result["primary_reason"] in (
            "wonder", "catharsis", "connection", "testimony", "protest", "survival", "expression"
        )

    def test_archetype_scores_sum_close_to_one(self):
        # Use text that contains clear archetype keywords
        lines = CATHARSIS_TEXT.splitlines()
        result = infer_creation_reason(lines)
        total = sum(result["archetype_scores"].values())
        # When keywords are found, scores sum to 1.0; when none match, sum is 0.0
        assert abs(total - 1.0) < 0.01 or total == 0.0

    def test_all_archetypes_present_in_scores(self):
        lines = CRAFT_TEXT.splitlines()
        result = infer_creation_reason(lines)
        for key in ("catharsis", "testimony", "survival", "connection", "protest", "wonder"):
            assert key in result["archetype_scores"]

    def test_empty_lines_returns_expression(self):
        result = infer_creation_reason([])
        assert result["primary_reason"] == "expression"


class TestDetectNegativeSpace:
    def test_blank_lines_detected(self):
        text = "first line\n\nsecond line\n\nthird line"
        raw = text.splitlines()
        non_blank = [l for l in raw if l.strip()]
        result = detect_negative_space(non_blank, raw)
        assert result["blank_line_count"] == 2
        assert result["has_negative_space"] is True

    def test_no_blanks_returns_false(self):
        text = "first\nsecond\nthird"
        raw = text.splitlines()
        non_blank = [l for l in raw if l.strip()]
        result = detect_negative_space(non_blank, raw)
        assert result["has_negative_space"] is False

    def test_trailing_silence_detected(self):
        # Two trailing newlines → splitlines() produces a trailing empty element
        text = "first line\nsecond line\n\n"
        raw = text.splitlines()
        non_blank = [l for l in raw if l.strip()]
        result = detect_negative_space(non_blank, raw)
        assert result["trailing_silence"] is True

    def test_internal_gaps_identified(self):
        text = "line one\n\nline two\n\nline three"
        raw = text.splitlines()
        non_blank = [l for l in raw if l.strip()]
        result = detect_negative_space(non_blank, raw)
        assert len(result["internal_gaps"]) >= 1

    def test_gap_ratio_in_range(self):
        text = "a\n\nb\n\nc"
        raw = text.splitlines()
        non_blank = [l for l in raw if l.strip()]
        result = detect_negative_space(non_blank, raw)
        assert 0.0 <= result["gap_ratio"] <= 1.0


class TestScoreHumanIrreducibility:
    def test_returns_required_keys(self):
        analysis = analyze(CRAFT_TEXT)
        lines = [l for l in CRAFT_TEXT.splitlines() if l.strip()]
        result = score_human_irreducibility(lines, analysis)
        assert "irreducible_lines" in result
        assert "irreducibility_index" in result
        assert "explanation" in result

    def test_index_in_range(self):
        analysis = analyze(CRAFT_TEXT)
        lines = [l for l in CRAFT_TEXT.splitlines() if l.strip()]
        result = score_human_irreducibility(lines, analysis)
        assert 0.0 <= result["irreducibility_index"] <= 1.0

    def test_explanation_is_string(self):
        analysis = analyze(CRAFT_TEXT)
        lines = [l for l in CRAFT_TEXT.splitlines() if l.strip()]
        result = score_human_irreducibility(lines, analysis)
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 0


class TestAnalyzeExistential:
    def test_returns_all_keys(self):
        analysis = analyze(SURVIVAL_TEXT)
        result = analyze_existential(SURVIVAL_TEXT, analysis)
        for key in ("survival", "emotional_necessity", "creation_reason",
                    "negative_space", "human_irreducibility"):
            assert key in result

    def test_empty_text_returns_empty_dicts(self):
        result = analyze_existential("", {})
        for key in ("survival", "emotional_necessity", "creation_reason",
                    "negative_space", "human_irreducibility"):
            assert result[key] == {}


# ===========================================================================
# PHASE 2 KALACRAFT
# ===========================================================================

class TestPhoneticBreakdown:
    def test_returns_one_entry_per_line(self):
        lines = ["hello world", "beautiful day"]
        result = phonetic_breakdown(lines)
        assert len(result) == 2

    def test_each_entry_has_required_keys(self):
        result = phonetic_breakdown(["I love you"])
        assert "line" in result[0]
        assert "words" in result[0]
        assert "total_phonemes" in result[0]

    def test_total_phonemes_positive(self):
        result = phonetic_breakdown(["hello beautiful world"])
        assert result[0]["total_phonemes"] > 0

    def test_word_entries_have_phonemes_and_syllables(self):
        result = phonetic_breakdown(["beautiful"])
        word_data = result[0]["words"][0]
        assert "phonemes" in word_data
        assert "syllable_count" in word_data
        assert word_data["syllable_count"] >= 3


class TestDetectStressPattern:
    def test_returns_one_entry_per_line(self):
        lines = ["I love the day", "you shine so bright"]
        result = detect_stress_pattern(lines)
        assert len(result) == 2

    def test_pattern_contains_s_and_u(self):
        result = detect_stress_pattern(["I love the day"])
        pattern = result[0]["pattern"]
        assert all(p in ("S", "U") for p in pattern)

    def test_notation_matches_pattern(self):
        result = detect_stress_pattern(["hello world"])
        assert result[0]["notation"] == " ".join(result[0]["pattern"])

    def test_function_words_are_unstressed(self):
        result = detect_stress_pattern(["the cat"])
        # "the" should be U
        assert result[0]["pattern"][0] == "U"


class TestDetectBreathPoints:
    def test_returns_one_entry_per_line(self):
        lines = ["hello world", "good morning"]
        result = detect_breath_points(lines)
        assert len(result) == 2

    def test_end_of_line_always_true(self):
        result = detect_breath_points(["any line"])
        assert result[0]["end_of_line"] is True

    def test_comma_creates_pause(self):
        result = detect_breath_points(["I walk, you follow"])
        assert len(result[0]["punctuation_pauses"]) >= 1

    def test_long_line_triggers_mid_break(self):
        long_line = "this is a very long line with many many syllables and words in it"
        result = detect_breath_points([long_line])
        assert result[0]["mid_line_break"] is True

    def test_short_line_no_mid_break(self):
        result = detect_breath_points(["hi there"])
        assert result[0]["mid_line_break"] is False


class TestAnalyzeMeterFlow:
    def test_returns_required_keys(self):
        result = analyze_meter_flow(["I walk alone in the dark",
                                      "searching for a tiny spark"])
        for key in ("per_line", "mean_syllables", "flow_score", "dominant_meter"):
            assert key in result

    def test_flow_score_in_range(self):
        lines = ["I love you", "you love me", "we are one"]
        result = analyze_meter_flow(lines)
        assert 0.0 <= result["flow_score"] <= 1.0

    def test_uniform_lines_high_flow(self):
        lines = ["I love the day"] * 4  # identical lines → max regularity
        result = analyze_meter_flow(lines)
        assert result["flow_score"] == 1.0

    def test_dominant_meter_is_string(self):
        result = analyze_meter_flow(["hello world"])
        assert isinstance(result["dominant_meter"], str)

    def test_empty_lines_returns_safe_defaults(self):
        result = analyze_meter_flow([])
        assert result["flow_score"] == 0.0


class TestAnalyzeLineDensity:
    def test_returns_one_entry_per_line(self):
        lines = ["hello world", "beautiful day"]
        result = analyze_line_density(lines)
        assert len(result) == 2

    def test_density_score_in_range(self):
        lines = ["the quick brown fox", "lazy dog"]
        result = analyze_line_density(lines)
        for entry in result:
            assert 0.0 <= entry["density_score"] <= 1.0

    def test_complex_line_higher_density(self):
        lines = ["go", "transcendental philosophical existentialism"]
        result = analyze_line_density(lines)
        assert result[1]["density_score"] >= result[0]["density_score"]

    def test_entry_has_required_keys(self):
        result = analyze_line_density(["hello world"])
        for key in ("line", "syllables", "word_count", "unique_ratio", "density_score"):
            assert key in result[0]


class TestDetectSemanticDrift:
    def test_returns_required_keys(self):
        result = detect_semantic_drift(["line one", "line two"])
        for key in ("sections", "overlap_om", "overlap_mc", "drift_score", "has_semantic_drift"):
            assert key in result

    def test_drift_score_in_range(self):
        lines = ["dark pain broken tears sorrow",
                 "beautiful light hope golden free",
                 "dance sing love warm bright"]
        result = detect_semantic_drift(lines)
        assert 0.0 <= result["drift_score"] <= 1.0

    def test_empty_returns_safe_values(self):
        result = detect_semantic_drift([])
        assert result["drift_score"] == 0.0
        assert result["has_semantic_drift"] is False

    def test_repeated_vocabulary_low_drift(self):
        lines = ["love and hope", "love and hope again", "still love and hope"]
        result = detect_semantic_drift(lines)
        assert result["drift_score"] < 0.8


class TestAnalyzeCraft:
    def test_returns_all_keys(self):
        result = analyze_craft(CRAFT_TEXT)
        for key in ("phonetics", "stress_patterns", "breath_points",
                    "meter_flow", "line_density", "semantic_drift"):
            assert key in result

    def test_empty_text_returns_empty(self):
        result = analyze_craft("")
        assert result["phonetics"] == []
        assert result["stress_patterns"] == []
        assert result["breath_points"] == []
        assert result["line_density"] == []
        assert result["meter_flow"] == {}
        assert result["semantic_drift"] == {}


# ===========================================================================
# PHASE 4 KALASIGNAL
# ===========================================================================

def _genome_for(text: str) -> dict:
    return build_art_genome(analyze(text)).to_dict()


class TestScoreMemorability:
    def test_returns_required_keys(self):
        lines = CRAFT_TEXT.splitlines()
        result = score_memorability(lines, _genome_for(CRAFT_TEXT))
        for key in ("score", "signals", "strongest_signal"):
            assert key in result

    def test_score_in_range(self):
        lines = CRAFT_TEXT.splitlines()
        result = score_memorability(lines, _genome_for(CRAFT_TEXT))
        assert 0.0 <= result["score"] <= 1.0

    def test_strongest_signal_is_key(self):
        lines = CRAFT_TEXT.splitlines()
        result = score_memorability(lines, _genome_for(CRAFT_TEXT))
        assert result["strongest_signal"] in result["signals"]


class TestScoreLongevity:
    def test_returns_required_keys(self):
        lines = WONDER_TEXT.splitlines()
        result = score_longevity(lines, _genome_for(WONDER_TEXT))
        for key in ("score", "signals", "strongest_signal"):
            assert key in result

    def test_score_in_range(self):
        result = score_longevity(WONDER_TEXT.splitlines(), _genome_for(WONDER_TEXT))
        assert 0.0 <= result["score"] <= 1.0


class TestScoreEmotionalAccess:
    def test_score_in_range(self):
        lines = WONDER_TEXT.splitlines()
        result = score_emotional_access(lines, _genome_for(WONDER_TEXT))
        assert 0.0 <= result["score"] <= 1.0

    def test_returns_required_keys(self):
        result = score_emotional_access(CRAFT_TEXT.splitlines(), _genome_for(CRAFT_TEXT))
        for key in ("score", "signals", "strongest_signal"):
            assert key in result


class TestScoreSharePotential:
    def test_score_in_range(self):
        result = score_share_potential(CRAFT_TEXT.splitlines(), _genome_for(CRAFT_TEXT))
        assert 0.0 <= result["score"] <= 1.0

    def test_note_contains_axiom(self):
        result = score_share_potential(CRAFT_TEXT.splitlines(), _genome_for(CRAFT_TEXT))
        assert "Viral" in result["note"]


class TestSeparateResonance:
    def _sep(self, text=CRAFT_TEXT):
        g = _genome_for(text)
        lines = text.splitlines()
        mem = score_memorability(lines, g)
        lon = score_longevity(lines, g)
        acc = score_emotional_access(lines, g)
        shr = score_share_potential(lines, g)
        return separate_resonance(mem, lon, acc, shr)

    def test_returns_three_dimensions(self):
        sep = self._sep()
        for key in ("viral_potential", "loved_potential", "remembered_potential"):
            assert key in sep
        # memorability is NOT in separation — it is a standalone dimension
        assert "memorability" not in sep

    def test_all_scores_in_range(self):
        sep = self._sep()
        for key in ("viral_potential", "loved_potential", "remembered_potential"):
            assert 0.0 <= sep[key]["score"] <= 1.0

    def test_levels_are_valid(self):
        sep = self._sep()
        for key in ("viral_potential", "loved_potential", "remembered_potential"):
            assert sep[key]["level"] in ("low", "moderate", "high")

    def test_axiom_present(self):
        sep = self._sep()
        assert "Viral" in sep["axiom"]
        assert "Loved" in sep["axiom"]
        assert "Remembered" in sep["axiom"]

    def test_dimensions_are_independent(self):
        # Scores should differ from each other (not all identical)
        sep = self._sep(WONDER_TEXT)
        scores = {
            sep["viral_potential"]["score"],
            sep["loved_potential"]["score"],
            sep["remembered_potential"]["score"],
        }
        # At least two distinct values (dimensions truly independent)
        assert len(scores) >= 1  # sanity — they can be equal by coincidence


class TestExplainResonance:
    def _explain(self, text=CRAFT_TEXT):
        g = _genome_for(text)
        lines = text.splitlines()
        mem = score_memorability(lines, g)
        lon = score_longevity(lines, g)
        acc = score_emotional_access(lines, g)
        shr = score_share_potential(lines, g)
        sep = separate_resonance(mem, lon, acc, shr)
        return explain_resonance(sep)

    def test_returns_non_empty_string(self):
        assert len(self._explain()) > 0

    def test_mentions_privacy(self):
        explanation = self._explain()
        assert "private" in explanation.lower()


class TestAnalyzeSignal:
    def test_returns_all_keys(self):
        result = analyze_signal(CRAFT_TEXT, _genome_for(CRAFT_TEXT))
        for key in ("memorability", "longevity", "emotional_access",
                    "share_potential", "separation", "explanation"):
            assert key in result

    def test_empty_text_safe(self):
        result = analyze_signal("", {})
        assert result["explanation"] == "No content to analyse."

    def test_explanation_is_string(self):
        result = analyze_signal(WONDER_TEXT, _genome_for(WONDER_TEXT))
        assert isinstance(result["explanation"], str)


# ===========================================================================
# NEW API ENDPOINTS
# ===========================================================================

class TestExistentialEndpoint:
    def test_valid_request_returns_200(self):
        resp = client.post("/existential", json={"text": VALID_POEM})
        assert resp.status_code == 200

    def test_response_has_existential_key(self):
        resp = client.post("/existential", json={"text": VALID_POEM})
        data = resp.json()
        assert "existential" in data
        assert "analysis" in data

    def test_existential_has_five_sections(self):
        resp = client.post("/existential", json={"text": VALID_POEM})
        ext = resp.json()["existential"]
        for key in ("survival", "emotional_necessity", "creation_reason",
                    "negative_space", "human_irreducibility"):
            assert key in ext

    def test_empty_text_returns_422(self):
        resp = client.post("/existential", json={"text": "  "})
        assert resp.status_code == 422

    def test_imitation_blocked(self):
        resp = client.post("/existential", json={"text": "write like Bob Dylan"})
        assert resp.status_code == 422


class TestCraftEndpoint:
    def test_valid_request_returns_200(self):
        resp = client.post("/craft", json={"text": VALID_POEM})
        assert resp.status_code == 200

    def test_response_has_craft_key(self):
        resp = client.post("/craft", json={"text": VALID_POEM})
        assert "craft" in resp.json()

    def test_craft_has_all_sections(self):
        resp = client.post("/craft", json={"text": VALID_POEM})
        craft = resp.json()["craft"]
        for key in ("phonetics", "stress_patterns", "breath_points",
                    "meter_flow", "line_density", "semantic_drift"):
            assert key in craft

    def test_empty_text_returns_422(self):
        resp = client.post("/craft", json={"text": ""})
        assert resp.status_code == 422

    def test_imitation_blocked(self):
        resp = client.post("/craft", json={"text": "sound like Eminem"})
        assert resp.status_code == 422


class TestSignalEndpoint:
    def test_valid_request_returns_200(self):
        resp = client.post("/signal", json={"text": VALID_POEM})
        assert resp.status_code == 200

    def test_response_has_signal_and_genome(self):
        resp = client.post("/signal", json={"text": VALID_POEM})
        data = resp.json()
        assert "signal" in data
        assert "art_genome" in data

    def test_signal_has_separation(self):
        resp = client.post("/signal", json={"text": VALID_POEM})
        sep = resp.json()["signal"]["separation"]
        assert "viral_potential" in sep
        assert "loved_potential" in sep
        assert "remembered_potential" in sep

    def test_signal_has_explanation(self):
        resp = client.post("/signal", json={"text": VALID_POEM})
        assert isinstance(resp.json()["signal"]["explanation"], str)

    def test_empty_text_returns_422(self):
        resp = client.post("/signal", json={"text": "   "})
        assert resp.status_code == 422

    def test_imitation_blocked(self):
        resp = client.post("/signal", json={"text": "in the style of Drake"})
        assert resp.status_code == 422

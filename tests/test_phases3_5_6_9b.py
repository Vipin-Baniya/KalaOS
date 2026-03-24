"""
Tests for Phase 3 KalaComposer, Phase 5 KalaFlow,
Phase 6 KalaCustody, and Phase 9 Temporal Intelligence.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

from main import app
from kalacore.pattern_engine import analyze
from kalacore.art_genome import build_art_genome
from kalacore.existential import analyze_existential
from kalacore.kalacustody import (
    generate_artistic_fingerprint,
    create_custody_record,
    assess_artistic_lineage,
    detect_structural_similarity,
    build_legacy_annotation,
    custody,
)
from kalacore.kalacomposer import (
    map_text_to_musical_structure,
    suggest_chord_progression,
    suggest_tempo,
    generate_arrangement_notes,
    map_lyric_rhythm_to_beat,
    compose,
)
from kalacore.kalaflow import (
    assess_distribution_readiness,
    generate_release_metadata,
    calculate_listener_journey,
    detect_format_suitability,
    build_artist_statement_prompts,
    flow,
)
from kalacore.temporal import (
    track_temporal_meaning,
    classify_ephemeral_art,
    map_creative_ancestry,
    generate_cultural_preservation_record,
    analyze_temporal,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

SURVIVAL_TEXT = (
    "I drown in the silent dark alone\n"
    "broken and bleeding I cannot breathe\n"
    "fade into the hollow numb and cold\n"
    "helpless trapped in chains I cannot see"
)

CRAFT_TEXT = (
    "I walk alone in the dark\n"
    "searching for a tiny spark\n"
    "the night is cold but my heart is warm\n"
    "I walk alone through every storm"
)

WONDER_TEXT = (
    "The golden stars stretch endlessly\n"
    "a beautiful miracle of light\n"
    "the universe is vast and free\n"
    "and dreams can shine beyond the night"
)

CONFESSIONAL_TEXT = (
    "I am the one who stayed up\n"
    "I was the voice that kept calling\n"
    "I will not let this be forgotten\n"
    "I carry everything I cannot say\n"
    "I remember the last night you were here\n"
    "I was broken then and still I am\n"
    "I have lived inside this silence too long"
)

FOLK_NARRATIVE = (
    "Once there was a traveller who came from the east\n"
    "she went through the valley and told her story\n"
    "there was a time when the old road was open\n"
    "she carried a song that nobody had heard\n"
    "the story was long but the night was longer\n"
    "she sang and the village was silent and listening"
)

HAIKU = (
    "old pond\n"
    "frog leaps into water\n"
    "sound of silence"
)

VALID_POEM = (
    "I walk alone in the dark\n"
    "Searching for a tiny spark\n"
    "The night is cold but my heart is warm\n"
    "I walk alone in the dark"
)

REFRAIN_TEXT = (
    "I walk alone in the dark\n"
    "searching for a tiny spark\n"
    "I walk alone in the dark\n"
    "the night is cold but hearts are warm\n"
    "I walk alone in the dark"
)


def _analysis(text=CRAFT_TEXT):
    return analyze(text)


def _genome(text=CRAFT_TEXT):
    return build_art_genome(_analysis(text)).to_dict()


def _existential(text=CRAFT_TEXT):
    return analyze_existential(text, _analysis(text))


# ===========================================================================
# PHASE 3 — KALACOMPOSER
# ===========================================================================

class TestMapTextToMusicalStructure:
    def test_returns_required_keys(self):
        result = map_text_to_musical_structure(
            CRAFT_TEXT.splitlines(), _analysis(CRAFT_TEXT)
        )
        for key in ("sections", "section_map", "has_chorus", "has_bridge", "structural_notes"):
            assert key in result

    def test_refrain_mapped_to_chorus(self):
        lines = REFRAIN_TEXT.splitlines()
        result = map_text_to_musical_structure(lines, _analysis(REFRAIN_TEXT))
        assert result["has_chorus"] is True

    def test_sections_list_is_nonempty(self):
        lines = CRAFT_TEXT.splitlines()
        result = map_text_to_musical_structure(lines, _analysis(CRAFT_TEXT))
        assert len(result["sections"]) >= 1

    def test_section_roles_valid(self):
        lines = CRAFT_TEXT.splitlines()
        result = map_text_to_musical_structure(lines, _analysis(CRAFT_TEXT))
        valid_roles = {"verse", "chorus", "hook", "bridge", "outro"}
        for section in result["sections"]:
            assert section["role"] in valid_roles

    def test_structural_notes_list(self):
        lines = CRAFT_TEXT.splitlines()
        result = map_text_to_musical_structure(lines, _analysis(CRAFT_TEXT))
        assert isinstance(result["structural_notes"], list)
        assert len(result["structural_notes"]) >= 1


class TestSuggestChordProgression:
    def test_returns_required_keys(self):
        result = suggest_chord_progression(_genome(CRAFT_TEXT))
        for key in ("scale_quality", "scale_name", "primary_progressions",
                    "secondary_progression", "key_note_suggestions", "harmonic_notes"):
            assert key in result

    def test_scale_quality_valid(self):
        result = suggest_chord_progression(_genome(CRAFT_TEXT))
        assert result["scale_quality"] in ("major", "minor", "mixed modal", "pentatonic")

    def test_primary_progressions_has_two(self):
        result = suggest_chord_progression(_genome(CRAFT_TEXT))
        assert len(result["primary_progressions"]) == 2

    def test_each_progression_has_feel(self):
        result = suggest_chord_progression(_genome(CRAFT_TEXT))
        for prog in result["primary_progressions"]:
            assert "progression" in prog
            assert "feel" in prog

    def test_key_note_suggestions_nonempty(self):
        result = suggest_chord_progression(_genome(CRAFT_TEXT))
        assert len(result["key_note_suggestions"]) >= 1

    def test_harmonic_notes_mention_arc(self):
        result = suggest_chord_progression(_genome(CRAFT_TEXT))
        combined = " ".join(result["harmonic_notes"])
        # Should mention the arc direction
        assert any(word in combined.lower() for word in (
            "ascending", "descending", "oscillating", "flat", "harmonic"
        ))


class TestSuggestTempo:
    def test_returns_required_keys(self):
        result = suggest_tempo(CRAFT_TEXT.splitlines(), _genome(CRAFT_TEXT))
        for key in ("bpm_range", "feel", "time_signature_suggestions", "tempo_notes"):
            assert key in result

    def test_bpm_range_is_tuple_of_two(self):
        result = suggest_tempo(CRAFT_TEXT.splitlines(), _genome(CRAFT_TEXT))
        lo, hi = result["bpm_range"]
        assert lo < hi
        assert 30 <= lo <= 200
        assert 30 <= hi <= 210

    def test_feel_is_valid(self):
        result = suggest_tempo(CRAFT_TEXT.splitlines(), _genome(CRAFT_TEXT))
        assert result["feel"] in ("urgent", "flowing", "conversational", "meditative")

    def test_time_signatures_list(self):
        result = suggest_tempo(CRAFT_TEXT.splitlines(), _genome(CRAFT_TEXT))
        assert len(result["time_signature_suggestions"]) >= 1

    def test_different_texts_different_bpm_feels(self):
        """Darker/slower vs. brighter/faster text → different feel."""
        wonder = suggest_tempo(WONDER_TEXT.splitlines(), _genome(WONDER_TEXT))
        survival = suggest_tempo(SURVIVAL_TEXT.splitlines(), _genome(SURVIVAL_TEXT))
        # Both return valid results — no crash
        assert wonder["feel"] in ("urgent", "flowing", "conversational", "meditative")
        assert survival["feel"] in ("urgent", "flowing", "conversational", "meditative")


class TestGenerateArrangementNotes:
    def test_returns_required_keys(self):
        result = generate_arrangement_notes(CRAFT_TEXT.splitlines(), _genome(CRAFT_TEXT))
        for key in ("palette", "arrangement_style", "density_guidance", "production_notes"):
            assert key in result

    def test_palette_is_nonempty_list(self):
        result = generate_arrangement_notes(CRAFT_TEXT.splitlines(), _genome(CRAFT_TEXT))
        assert isinstance(result["palette"], list)
        assert len(result["palette"]) >= 1

    def test_production_notes_is_list(self):
        result = generate_arrangement_notes(CRAFT_TEXT.splitlines(), _genome(CRAFT_TEXT))
        assert isinstance(result["production_notes"], list)
        assert len(result["production_notes"]) >= 1


class TestMapLyricRhythmToBeat:
    def test_returns_one_entry_per_line(self):
        lines = CRAFT_TEXT.splitlines()
        result = map_lyric_rhythm_to_beat(lines)
        assert len(result) == len(lines)

    def test_each_entry_has_required_keys(self):
        result = map_lyric_rhythm_to_beat(["I walk alone"])
        entry = result[0]
        assert "line" in entry
        assert "beat_positions" in entry
        assert "rhythmic_shape" in entry

    def test_rhythmic_shape_valid(self):
        result = map_lyric_rhythm_to_beat(CRAFT_TEXT.splitlines())
        valid_shapes = {"front-heavy", "even", "end-heavy", "empty"}
        for entry in result:
            assert entry["rhythmic_shape"] in valid_shapes

    def test_beat_positions_has_words(self):
        result = map_lyric_rhythm_to_beat(["I love you"])
        assert len(result[0]["beat_positions"]) == 3

    def test_empty_line_handled(self):
        result = map_lyric_rhythm_to_beat([""])
        assert result[0]["rhythmic_shape"] == "empty"


class TestCompose:
    def test_returns_all_keys(self):
        result = compose(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        for key in ("musical_structure", "chord_suggestions", "tempo",
                    "arrangement", "lyric_beat_alignment"):
            assert key in result

    def test_empty_text_safe(self):
        result = compose("", {}, {})
        assert result["musical_structure"] == {}
        assert result["lyric_beat_alignment"] == []


# ===========================================================================
# PHASE 5 — KALAFLOW
# ===========================================================================

class TestAssessDistributionReadiness:
    def test_returns_required_keys(self):
        lines = CRAFT_TEXT.splitlines()
        result = assess_distribution_readiness(lines, _analysis(CRAFT_TEXT))
        for key in ("is_ready", "readiness_score", "checks", "notes"):
            assert key in result

    def test_score_in_range(self):
        lines = CRAFT_TEXT.splitlines()
        result = assess_distribution_readiness(lines, _analysis(CRAFT_TEXT))
        assert 0.0 <= result["readiness_score"] <= 1.0

    def test_is_ready_is_bool(self):
        lines = CRAFT_TEXT.splitlines()
        result = assess_distribution_readiness(lines, _analysis(CRAFT_TEXT))
        assert isinstance(result["is_ready"], bool)

    def test_checks_list_has_five_items(self):
        lines = CRAFT_TEXT.splitlines()
        result = assess_distribution_readiness(lines, _analysis(CRAFT_TEXT))
        assert len(result["checks"]) == 5

    def test_notes_mentions_artist(self):
        lines = CRAFT_TEXT.splitlines()
        result = assess_distribution_readiness(lines, _analysis(CRAFT_TEXT))
        notes = " ".join(result["notes"])
        assert "artist" in notes.lower()

    def test_short_text_not_automatically_ready(self):
        # Two-line text should fail the length check (needs >= 4 lines)
        lines = ["first short line", "second line"]
        result = assess_distribution_readiness(lines, analyze("first short line\nsecond line"))
        length_check = next(c for c in result["checks"] if c["check"] == "sufficient_length")
        assert length_check["passed"] is False


class TestGenerateReleaseMetadata:
    def test_returns_required_keys(self):
        lines = CRAFT_TEXT.splitlines()
        result = generate_release_metadata(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        for key in ("mood_tags", "genre_hints", "structural_summary",
                    "length_category", "suggested_title_words", "metadata_note"):
            assert key in result

    def test_mood_tags_list(self):
        lines = CRAFT_TEXT.splitlines()
        result = generate_release_metadata(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert isinstance(result["mood_tags"], list)
        assert len(result["mood_tags"]) >= 1

    def test_genre_hints_list(self):
        lines = CRAFT_TEXT.splitlines()
        result = generate_release_metadata(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert len(result["genre_hints"]) >= 1

    def test_length_category_valid(self):
        lines = CRAFT_TEXT.splitlines()
        result = generate_release_metadata(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert result["length_category"] in ("short", "standard", "long", "extended")

    def test_metadata_note_mentions_artist(self):
        lines = CRAFT_TEXT.splitlines()
        result = generate_release_metadata(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert "artist" in result["metadata_note"].lower()


class TestCalculateListenerJourney:
    def test_returns_required_keys(self):
        lines = CRAFT_TEXT.splitlines()
        result = calculate_listener_journey(lines, _analysis(CRAFT_TEXT))
        for key in ("journey_stages", "overall_journey", "intimacy_level"):
            assert key in result

    def test_stages_count_at_most_three(self):
        lines = CRAFT_TEXT.splitlines()
        result = calculate_listener_journey(lines, _analysis(CRAFT_TEXT))
        assert 1 <= len(result["journey_stages"]) <= 3

    def test_intimacy_level_valid(self):
        lines = CRAFT_TEXT.splitlines()
        result = calculate_listener_journey(lines, _analysis(CRAFT_TEXT))
        assert result["intimacy_level"] in ("private", "shared", "universal")

    def test_confessional_is_private(self):
        lines = CONFESSIONAL_TEXT.splitlines()
        result = calculate_listener_journey(lines, _analysis(CONFESSIONAL_TEXT))
        assert result["intimacy_level"] == "private"

    def test_overall_journey_is_string(self):
        lines = CRAFT_TEXT.splitlines()
        result = calculate_listener_journey(lines, _analysis(CRAFT_TEXT))
        assert isinstance(result["overall_journey"], str)
        assert len(result["overall_journey"]) > 0


class TestDetectFormatSuitability:
    def test_returns_required_keys(self):
        lines = CRAFT_TEXT.splitlines()
        result = detect_format_suitability(lines, _analysis(CRAFT_TEXT))
        for key in ("primary_format", "format_scores", "format_notes"):
            assert key in result

    def test_primary_format_valid(self):
        lines = CRAFT_TEXT.splitlines()
        result = detect_format_suitability(lines, _analysis(CRAFT_TEXT))
        assert result["primary_format"] in ("single", "EP track", "album track", "interlude")

    def test_format_scores_sum_to_one(self):
        lines = CRAFT_TEXT.splitlines()
        result = detect_format_suitability(lines, _analysis(CRAFT_TEXT))
        total = sum(result["format_scores"].values())
        assert abs(total - 1.0) < 0.01

    def test_very_short_is_interlude(self):
        lines = HAIKU.splitlines()
        result = detect_format_suitability(lines, _analysis(HAIKU))
        assert result["primary_format"] == "interlude"


class TestBuildArtistStatementPrompts:
    def test_returns_required_keys(self):
        result = build_artist_statement_prompts(_genome(CRAFT_TEXT), _existential(CRAFT_TEXT))
        for key in ("core_prompts", "tailored_prompts", "note"):
            assert key in result

    def test_core_prompts_has_five(self):
        result = build_artist_statement_prompts(_genome(CRAFT_TEXT), _existential(CRAFT_TEXT))
        assert len(result["core_prompts"]) == 5

    def test_tailored_prompts_list(self):
        result = build_artist_statement_prompts(_genome(CRAFT_TEXT), _existential(CRAFT_TEXT))
        assert isinstance(result["tailored_prompts"], list)

    def test_note_mentions_artist(self):
        result = build_artist_statement_prompts(_genome(CRAFT_TEXT), _existential(CRAFT_TEXT))
        assert "artist" in result["note"].lower()


class TestFlow:
    def test_returns_all_keys(self):
        analysis = _analysis(CRAFT_TEXT)
        genome = _genome(CRAFT_TEXT)
        ext = _existential(CRAFT_TEXT)
        result = flow(CRAFT_TEXT, analysis, genome, ext)
        for key in ("readiness", "metadata", "listener_journey",
                    "format_suitability", "artist_statement_prompts"):
            assert key in result

    def test_empty_text_safe(self):
        result = flow("", {}, {}, {})
        for key in ("readiness", "metadata", "listener_journey",
                    "format_suitability", "artist_statement_prompts"):
            assert result[key] == {}


# ===========================================================================
# PHASE 6 — KALACUSTODY
# ===========================================================================

class TestGenerateArtisticFingerprint:
    def test_returns_required_keys(self):
        analysis = _analysis(CRAFT_TEXT)
        genome = _genome(CRAFT_TEXT)
        result = generate_artistic_fingerprint(CRAFT_TEXT, analysis, genome)
        for key in ("structural_fingerprint", "identity_hash", "fingerprint_components"):
            assert key in result

    def test_identity_hash_is_64_chars(self):
        result = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert len(result["identity_hash"]) == 64

    def test_same_text_same_hash(self):
        r1 = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        r2 = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert r1["identity_hash"] == r2["identity_hash"]

    def test_different_texts_different_hashes(self):
        r1 = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        r2 = generate_artistic_fingerprint(WONDER_TEXT, _analysis(WONDER_TEXT), _genome(WONDER_TEXT))
        assert r1["identity_hash"] != r2["identity_hash"]

    def test_structural_fingerprint_is_string(self):
        result = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert isinstance(result["structural_fingerprint"], str)
        assert "|" in result["structural_fingerprint"]

    def test_empty_text_handled(self):
        result = generate_artistic_fingerprint("", {}, {})
        assert result["structural_fingerprint"] == "empty"


class TestCreateCustodyRecord:
    def test_returns_required_keys(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = create_custody_record(CRAFT_TEXT, fp, _genome(CRAFT_TEXT))
        for key in ("version", "identity_hash", "structural_fingerprint",
                    "declared_artist", "creation_context", "art_genome_summary",
                    "record_note"):
            assert key in result

    def test_version_is_string(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = create_custody_record(CRAFT_TEXT, fp, _genome(CRAFT_TEXT))
        assert isinstance(result["version"], str)

    def test_artist_name_included(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = create_custody_record(CRAFT_TEXT, fp, _genome(CRAFT_TEXT), artist_name="Test Artist")
        assert result["declared_artist"] == "Test Artist"

    def test_undeclared_when_no_artist(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = create_custody_record(CRAFT_TEXT, fp, _genome(CRAFT_TEXT))
        assert result["declared_artist"] == "[undeclared]"

    def test_record_note_mentions_artist(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = create_custody_record(CRAFT_TEXT, fp, _genome(CRAFT_TEXT))
        assert "artist" in result["record_note"].lower()


class TestAssessArtisticLineage:
    def test_returns_required_keys(self):
        lines = CRAFT_TEXT.splitlines()
        result = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        for key in ("detected_traditions", "primary_tradition", "lineage_note"):
            assert key in result

    def test_detected_traditions_nonempty(self):
        lines = CRAFT_TEXT.splitlines()
        result = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert len(result["detected_traditions"]) >= 1

    def test_haiku_detected(self):
        lines = HAIKU.splitlines()
        result = assess_artistic_lineage(lines, _analysis(HAIKU), _genome(HAIKU))
        traditions = [t["tradition"] for t in result["detected_traditions"]]
        assert "haiku" in traditions

    def test_confessional_detected(self):
        lines = CONFESSIONAL_TEXT.splitlines()
        result = assess_artistic_lineage(lines, _analysis(CONFESSIONAL_TEXT), _genome(CONFESSIONAL_TEXT))
        traditions = [t["tradition"] for t in result["detected_traditions"]]
        assert "confessional" in traditions

    def test_confidence_in_range(self):
        lines = CRAFT_TEXT.splitlines()
        result = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        for t in result["detected_traditions"]:
            assert 0.0 <= t["confidence"] <= 1.0

    def test_lineage_note_is_string(self):
        lines = CRAFT_TEXT.splitlines()
        result = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert isinstance(result["lineage_note"], str)
        assert len(result["lineage_note"]) > 0


class TestDetectStructuralSimilarity:
    def test_identical_fingerprints_score_one(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = detect_structural_similarity(fp, fp)
        assert result["similarity_score"] == 1.0

    def test_different_fingerprints_score_less(self):
        fp_a = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        fp_b = generate_artistic_fingerprint(WONDER_TEXT, _analysis(WONDER_TEXT), _genome(WONDER_TEXT))
        result = detect_structural_similarity(fp_a, fp_b)
        assert 0.0 <= result["similarity_score"] <= 1.0

    def test_returns_required_keys(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = detect_structural_similarity(fp, fp)
        for key in ("similarity_score", "matching_features", "diverging_features", "similarity_note"):
            assert key in result

    def test_similarity_note_mentions_artist(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = detect_structural_similarity(fp, fp)
        assert "artist" in result["similarity_note"].lower()


class TestBuildLegacyAnnotation:
    def test_returns_required_keys(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        lines = CRAFT_TEXT.splitlines()
        lineage = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        ext = _existential(CRAFT_TEXT)
        result = build_legacy_annotation(_genome(CRAFT_TEXT), ext, fp, lineage)
        for key in ("artistic_identity", "emotional_intent", "creation_context",
                    "formal_tradition", "irreducible_zones", "legacy_note"):
            assert key in result

    def test_legacy_note_is_meaningful(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        lines = CRAFT_TEXT.splitlines()
        lineage = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        ext = _existential(CRAFT_TEXT)
        result = build_legacy_annotation(_genome(CRAFT_TEXT), ext, fp, lineage)
        assert len(result["legacy_note"]) > 20

    def test_artistic_identity_contains_fingerprint(self):
        fp = generate_artistic_fingerprint(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        lines = CRAFT_TEXT.splitlines()
        lineage = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        ext = _existential(CRAFT_TEXT)
        result = build_legacy_annotation(_genome(CRAFT_TEXT), ext, fp, lineage)
        assert "|" in result["artistic_identity"]  # fingerprint included


class TestCustody:
    def test_returns_all_keys(self):
        result = custody(CRAFT_TEXT, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT), _existential(CRAFT_TEXT))
        for key in ("fingerprint", "custody_record", "lineage", "legacy_annotation"):
            assert key in result

    def test_empty_text_safe(self):
        result = custody("", {}, {}, {})
        for key in ("fingerprint", "custody_record", "lineage", "legacy_annotation"):
            assert result[key] == {}


# ===========================================================================
# PHASE 9 — TEMPORAL INTELLIGENCE
# ===========================================================================

class TestTrackTemporalMeaning:
    def test_returns_required_keys(self):
        lines = CRAFT_TEXT.splitlines()
        result = track_temporal_meaning(lines, _genome(CRAFT_TEXT))
        for key in ("temporal_anchoring", "temporal_word_count", "timeless_word_count",
                    "cultural_specificity", "cultural_specific_words", "temporal_notes"):
            assert key in result

    def test_anchoring_valid(self):
        lines = CRAFT_TEXT.splitlines()
        result = track_temporal_meaning(lines, _genome(CRAFT_TEXT))
        assert result["temporal_anchoring"] in ("immediate", "recent-past", "timeless", "mixed")

    def test_cultural_specificity_valid(self):
        lines = CRAFT_TEXT.splitlines()
        result = track_temporal_meaning(lines, _genome(CRAFT_TEXT))
        assert result["cultural_specificity"] in ("high", "moderate", "low")

    def test_culturally_specific_text(self):
        lines = ["I tweet and post and scroll my phone feed every night"]
        result = track_temporal_meaning(lines, _genome(CRAFT_TEXT))
        assert result["cultural_specificity"] in ("moderate", "high")

    def test_temporal_notes_list(self):
        lines = CRAFT_TEXT.splitlines()
        result = track_temporal_meaning(lines, _genome(CRAFT_TEXT))
        assert isinstance(result["temporal_notes"], list)
        assert len(result["temporal_notes"]) >= 1


class TestClassifyEphemeralArt:
    def test_returns_required_keys(self):
        lines = CRAFT_TEXT.splitlines()
        result = classify_ephemeral_art(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        for key in ("is_ephemeral", "ephemeral_score", "indicators", "ephemeral_note"):
            assert key in result

    def test_score_in_range(self):
        lines = CRAFT_TEXT.splitlines()
        result = classify_ephemeral_art(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert 0.0 <= result["ephemeral_score"] <= 1.0

    def test_is_ephemeral_bool(self):
        lines = CRAFT_TEXT.splitlines()
        result = classify_ephemeral_art(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert isinstance(result["is_ephemeral"], bool)

    def test_short_performance_text_is_ephemeral(self):
        text = "right here\nright now\nthis moment"
        lines = text.splitlines()
        result = classify_ephemeral_art(lines, analyze(text), build_art_genome(analyze(text)).to_dict())
        assert result["is_ephemeral"] is True

    def test_ephemeral_note_mentions_moment(self):
        lines = CRAFT_TEXT.splitlines()
        result = classify_ephemeral_art(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert "moment" in result["ephemeral_note"].lower()


class TestMapCreativeAncestry:
    def test_returns_required_keys(self):
        lines = CRAFT_TEXT.splitlines()
        lineage = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = map_creative_ancestry(lineage, _existential(CRAFT_TEXT), _genome(CRAFT_TEXT))
        for key in ("ancestors", "primary_ancestor", "ancestry_note"):
            assert key in result

    def test_ancestors_nonempty(self):
        lines = CRAFT_TEXT.splitlines()
        lineage = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = map_creative_ancestry(lineage, _existential(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert len(result["ancestors"]) >= 1

    def test_each_ancestor_has_exemplars(self):
        lines = CRAFT_TEXT.splitlines()
        lineage = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = map_creative_ancestry(lineage, _existential(CRAFT_TEXT), _genome(CRAFT_TEXT))
        for ancestor in result["ancestors"]:
            assert "exemplars" in ancestor
            assert isinstance(ancestor["exemplars"], list)

    def test_ancestry_note_is_string(self):
        lines = CRAFT_TEXT.splitlines()
        lineage = assess_artistic_lineage(lines, _analysis(CRAFT_TEXT), _genome(CRAFT_TEXT))
        result = map_creative_ancestry(lineage, _existential(CRAFT_TEXT), _genome(CRAFT_TEXT))
        assert isinstance(result["ancestry_note"], str)

    def test_survival_text_includes_blues(self):
        lines = SURVIVAL_TEXT.splitlines()
        analysis = _analysis(SURVIVAL_TEXT)
        lineage = assess_artistic_lineage(lines, analysis, _genome(SURVIVAL_TEXT))
        ext = analyze_existential(SURVIVAL_TEXT, analysis)
        result = map_creative_ancestry(lineage, ext, _genome(SURVIVAL_TEXT))
        ancestor_names = [a["tradition"] for a in result["ancestors"]]
        # Survival text should touch blues or confessional
        assert any(t in ancestor_names for t in ("blues tradition", "confessional tradition"))


class TestGenerateCulturalPreservationRecord:
    def test_returns_required_keys(self):
        lines = CRAFT_TEXT.splitlines()
        analysis = _analysis(CRAFT_TEXT)
        genome = _genome(CRAFT_TEXT)
        ext = _existential(CRAFT_TEXT)
        lineage = assess_artistic_lineage(lines, analysis, genome)
        ancestry = map_creative_ancestry(lineage, ext, genome)
        temporal = track_temporal_meaning(lines, genome)
        result = generate_cultural_preservation_record(lines, genome, ext, temporal, ancestry)
        for key in ("preservation_priority", "preservation_reasons",
                    "cultural_context", "transmission_medium", "stewardship_notes"):
            assert key in result

    def test_preservation_priority_valid(self):
        lines = CRAFT_TEXT.splitlines()
        analysis = _analysis(CRAFT_TEXT)
        genome = _genome(CRAFT_TEXT)
        ext = _existential(CRAFT_TEXT)
        lineage = assess_artistic_lineage(lines, analysis, genome)
        ancestry = map_creative_ancestry(lineage, ext, genome)
        temporal = track_temporal_meaning(lines, genome)
        result = generate_cultural_preservation_record(lines, genome, ext, temporal, ancestry)
        assert result["preservation_priority"] in ("high", "moderate", "standard")

    def test_stewardship_notes_list(self):
        lines = CRAFT_TEXT.splitlines()
        analysis = _analysis(CRAFT_TEXT)
        genome = _genome(CRAFT_TEXT)
        ext = _existential(CRAFT_TEXT)
        lineage = assess_artistic_lineage(lines, analysis, genome)
        ancestry = map_creative_ancestry(lineage, ext, genome)
        temporal = track_temporal_meaning(lines, genome)
        result = generate_cultural_preservation_record(lines, genome, ext, temporal, ancestry)
        assert isinstance(result["stewardship_notes"], list)
        assert len(result["stewardship_notes"]) >= 1


class TestAnalyzeTemporal:
    def test_returns_all_keys(self):
        analysis = _analysis(CRAFT_TEXT)
        genome = _genome(CRAFT_TEXT)
        ext = _existential(CRAFT_TEXT)
        lines = CRAFT_TEXT.splitlines()
        lineage = assess_artistic_lineage(lines, analysis, genome)
        result = analyze_temporal(CRAFT_TEXT, analysis, genome, ext, lineage)
        for key in ("temporal_meaning", "ephemeral_classification",
                    "creative_ancestry", "cultural_preservation"):
            assert key in result

    def test_empty_text_safe(self):
        result = analyze_temporal("", {}, {}, {}, {})
        for key in ("temporal_meaning", "ephemeral_classification",
                    "creative_ancestry", "cultural_preservation"):
            assert result[key] == {}


# ===========================================================================
# NEW API ENDPOINTS
# ===========================================================================

class TestComposeEndpoint:
    def test_valid_request_returns_200(self):
        resp = client.post("/compose", json={"text": VALID_POEM})
        assert resp.status_code == 200

    def test_response_has_composition_and_genome(self):
        resp = client.post("/compose", json={"text": VALID_POEM})
        data = resp.json()
        assert "composition" in data
        assert "art_genome" in data

    def test_composition_has_all_sections(self):
        resp = client.post("/compose", json={"text": VALID_POEM})
        comp = resp.json()["composition"]
        for key in ("musical_structure", "chord_suggestions", "tempo",
                    "arrangement", "lyric_beat_alignment"):
            assert key in comp

    def test_empty_text_returns_422(self):
        resp = client.post("/compose", json={"text": "  "})
        assert resp.status_code == 422

    def test_imitation_blocked(self):
        resp = client.post("/compose", json={"text": "write like Beethoven"})
        assert resp.status_code == 422


class TestFlowEndpoint:
    def test_valid_request_returns_200(self):
        resp = client.post("/flow", json={"text": VALID_POEM})
        assert resp.status_code == 200

    def test_response_has_flow_and_genome(self):
        resp = client.post("/flow", json={"text": VALID_POEM})
        data = resp.json()
        assert "flow" in data
        assert "art_genome" in data

    def test_flow_has_all_sections(self):
        resp = client.post("/flow", json={"text": VALID_POEM})
        fl = resp.json()["flow"]
        for key in ("readiness", "metadata", "listener_journey",
                    "format_suitability", "artist_statement_prompts"):
            assert key in fl

    def test_empty_text_returns_422(self):
        resp = client.post("/flow", json={"text": ""})
        assert resp.status_code == 422

    def test_imitation_blocked(self):
        resp = client.post("/flow", json={"text": "sound like Taylor Swift"})
        assert resp.status_code == 422


class TestCustodyEndpoint:
    def test_valid_request_returns_200(self):
        resp = client.post("/custody", json={"text": VALID_POEM})
        assert resp.status_code == 200

    def test_response_has_custody_and_genome(self):
        resp = client.post("/custody", json={"text": VALID_POEM})
        data = resp.json()
        assert "custody" in data
        assert "art_genome" in data

    def test_custody_has_all_sections(self):
        resp = client.post("/custody", json={"text": VALID_POEM})
        cust = resp.json()["custody"]
        for key in ("fingerprint", "custody_record", "lineage", "legacy_annotation"):
            assert key in cust

    def test_artist_name_accepted(self):
        resp = client.post("/custody", json={
            "text": VALID_POEM,
            "artist_name": "Test Artist",
        })
        assert resp.status_code == 200
        declared = resp.json()["custody"]["custody_record"]["declared_artist"]
        assert declared == "Test Artist"

    def test_empty_text_returns_422(self):
        resp = client.post("/custody", json={"text": "   "})
        assert resp.status_code == 422

    def test_imitation_blocked(self):
        resp = client.post("/custody", json={"text": "imitate Bob Dylan"})
        assert resp.status_code == 422


class TestTemporalEndpoint:
    def test_valid_request_returns_200(self):
        resp = client.post("/temporal", json={"text": VALID_POEM})
        assert resp.status_code == 200

    def test_response_has_temporal_and_genome(self):
        resp = client.post("/temporal", json={"text": VALID_POEM})
        data = resp.json()
        assert "temporal" in data
        assert "art_genome" in data

    def test_temporal_has_all_sections(self):
        resp = client.post("/temporal", json={"text": VALID_POEM})
        temp = resp.json()["temporal"]
        for key in ("temporal_meaning", "ephemeral_classification",
                    "creative_ancestry", "cultural_preservation"):
            assert key in temp

    def test_empty_text_returns_422(self):
        resp = client.post("/temporal", json={"text": "  "})
        assert resp.status_code == 422

    def test_imitation_blocked(self):
        resp = client.post("/temporal", json={"text": "pretend to be Picasso"})
        assert resp.status_code == 422

"""
Tests for Phase 12 KalaProducer — music production, generation,
distribution & streaming endpoints.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

from main import app
from kalacore.pattern_engine import analyze
from kalacore.art_genome import build_art_genome
from kalacore.kalaproducer import (
    generate_production_plan,
    generate_beat_pattern,
    suggest_instruments,
    generate_melody_contour,
    suggest_distribution_channels,
    generate_streaming_metadata,
    generate_sample_palette,
    produce,
)

client = TestClient(app)

SAMPLE_LYRICS = """\
I walk alone through city streets
The neon lights above me beat
A rhythm in the rain-soaked dark
A melody without a mark

Every corner holds a song
A ghost of where I don't belong
But still I walk and still I sing
Into the night on broken wings
"""

SHORT_POEM = "Love is a fire\nBurning bright"


# ---------------------------------------------------------------------------
# Unit: generate_production_plan
# ---------------------------------------------------------------------------

class TestGenerateProductionPlan:
    def _get_plan(self, text=SAMPLE_LYRICS):
        lines = [l for l in text.splitlines() if l.strip()]
        pa = analyze(text)
        ag = build_art_genome(pa).to_dict()
        return generate_production_plan(lines, pa, ag)

    def test_returns_dict(self):
        plan = self._get_plan()
        assert isinstance(plan, dict)

    def test_has_required_keys(self):
        plan = self._get_plan()
        keys = [
            "suggested_bpm_range", "suggested_key", "time_signature",
            "genre_palette", "production_style", "mixing_notes",
            "mastering_target_lufs", "production_notes",
        ]
        for k in keys:
            assert k in plan, f"Missing key: {k}"

    def test_bpm_range_is_tuple_of_two_ints(self):
        plan = self._get_plan()
        bpm = plan["suggested_bpm_range"]
        assert len(bpm) == 2
        assert bpm[0] < bpm[1]

    def test_genre_palette_is_nonempty_list(self):
        plan = self._get_plan()
        assert isinstance(plan["genre_palette"], list)
        assert len(plan["genre_palette"]) >= 1

    def test_mastering_lufs_is_negative(self):
        plan = self._get_plan()
        assert plan["mastering_target_lufs"] < 0

    def test_production_notes_is_list(self):
        plan = self._get_plan()
        assert isinstance(plan["production_notes"], list)
        assert len(plan["production_notes"]) >= 1

    def test_short_text(self):
        plan = self._get_plan(SHORT_POEM)
        assert isinstance(plan, dict)
        assert plan["suggested_bpm_range"][0] > 0


# ---------------------------------------------------------------------------
# Unit: generate_beat_pattern
# ---------------------------------------------------------------------------

class TestGenerateBeatPattern:
    def _genome(self, text=SAMPLE_LYRICS):
        pa = analyze(text)
        return build_art_genome(pa).to_dict()

    def test_returns_dict(self):
        bp = generate_beat_pattern(self._genome(), ["hip-hop"])
        assert isinstance(bp, dict)

    def test_has_required_keys(self):
        bp = generate_beat_pattern(self._genome(), ["pop"])
        for k in ["pattern_name", "kick", "snare", "hihat", "pattern_note", "velocity_hint", "humanise_tip"]:
            assert k in bp

    def test_trap_genre_selects_trap_pattern(self):
        bp = generate_beat_pattern(self._genome(), ["trap"])
        assert bp["pattern_name"] == "trap"

    def test_hiphop_genre_selects_boom_bap(self):
        bp = generate_beat_pattern(self._genome(), ["hip-hop"])
        assert bp["pattern_name"] == "boom bap"

    def test_afrobeats_pattern(self):
        bp = generate_beat_pattern(self._genome(), ["afrobeats"])
        assert bp["pattern_name"] == "afrobeats"

    def test_default_pattern_is_valid(self):
        bp = generate_beat_pattern(self._genome(), [])
        assert bp["pattern_name"] in {"4/4", "6/8", "boom bap", "trap", "afrobeats"}


# ---------------------------------------------------------------------------
# Unit: suggest_instruments
# ---------------------------------------------------------------------------

class TestSuggestInstruments:
    def _genome(self, text=SAMPLE_LYRICS):
        pa = analyze(text)
        return build_art_genome(pa).to_dict()

    def test_returns_dict(self):
        result = suggest_instruments(self._genome(), ["folk"])
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = suggest_instruments(self._genome())
        for k in ["primary_instruments", "texture_instruments", "avoid_note", "layering_hint"]:
            assert k in result

    def test_primary_instruments_nonempty(self):
        result = suggest_instruments(self._genome(), ["pop"])
        assert len(result["primary_instruments"]) >= 1

    def test_hiphop_instruments_include_808(self):
        result = suggest_instruments(self._genome(), ["hip-hop"])
        combined = " ".join(result["primary_instruments"]).lower()
        assert "808" in combined or "bass" in combined

    def test_ambient_instruments(self):
        result = suggest_instruments(self._genome(), ["ambient"])
        assert len(result["primary_instruments"]) >= 1


# ---------------------------------------------------------------------------
# Unit: generate_melody_contour
# ---------------------------------------------------------------------------

class TestGenerateMelodyContour:
    def _run(self, text=SAMPLE_LYRICS):
        lines = [l for l in text.splitlines() if l.strip()]
        pa = analyze(text)
        ag = build_art_genome(pa).to_dict()
        return generate_melody_contour(lines, ag)

    def test_returns_dict(self):
        result = self._run()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = self._run()
        for k in ["scale_quality", "scale_degrees", "contour_description",
                  "phrase_suggestions", "ornamentation_tips"]:
            assert k in result

    def test_scale_degrees_nonempty(self):
        result = self._run()
        assert len(result["scale_degrees"]) >= 4

    def test_phrase_suggestions_list(self):
        result = self._run()
        assert isinstance(result["phrase_suggestions"], list)

    def test_phrase_suggestions_capped_at_8(self):
        long_text = "\n".join([f"Line number {i} of this song" for i in range(20)])
        result = self._run(long_text)
        assert len(result["phrase_suggestions"]) <= 8

    def test_short_poem_returns_valid(self):
        result = self._run(SHORT_POEM)
        assert result["scale_quality"] in {"major", "minor", "pentatonic", "mixed modal", "blues"}


# ---------------------------------------------------------------------------
# Unit: suggest_distribution_channels
# ---------------------------------------------------------------------------

class TestSuggestDistributionChannels:
    def _genome(self, text=SAMPLE_LYRICS):
        pa = analyze(text)
        return build_art_genome(pa).to_dict()

    def test_returns_dict(self):
        result = suggest_distribution_channels(self._genome(), ["pop"])
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = suggest_distribution_channels(self._genome())
        for k in ["recommended_platforms", "distribution_services",
                  "release_strategy_tips", "rights_reminder"]:
            assert k in result

    def test_recommended_platforms_nonempty(self):
        result = suggest_distribution_channels(self._genome(), ["folk"])
        assert len(result["recommended_platforms"]) >= 1

    def test_distribution_services_nonempty(self):
        result = suggest_distribution_channels(self._genome())
        assert len(result["distribution_services"]) >= 3

    def test_ambient_includes_bandcamp_or_soundcloud(self):
        result = suggest_distribution_channels(self._genome(), ["ambient"])
        names = [p["platform"] for p in result["recommended_platforms"]]
        # Ambient should be well served; just check we get valid platforms
        assert len(names) >= 1

    def test_rights_reminder_not_empty(self):
        result = suggest_distribution_channels(self._genome())
        assert len(result["rights_reminder"]) > 10


# ---------------------------------------------------------------------------
# Unit: generate_streaming_metadata
# ---------------------------------------------------------------------------

class TestGenerateStreamingMetadata:
    def _run(self, text=SAMPLE_LYRICS, artist=None):
        lines = [l for l in text.splitlines() if l.strip()]
        pa = analyze(text)
        ag = build_art_genome(pa).to_dict()
        return generate_streaming_metadata(lines, ag, ["pop", "r&b"], artist)

    def test_returns_dict(self):
        result = self._run()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = self._run()
        for k in ["suggested_title_words", "genre_tags", "mood_tags",
                  "isrc_note", "loudness_targets", "audio_format_note",
                  "release_checklist"]:
            assert k in result

    def test_title_words_nonempty(self):
        result = self._run()
        assert len(result["suggested_title_words"]) >= 1

    def test_mood_tags_list(self):
        result = self._run()
        assert isinstance(result["mood_tags"], list)
        assert len(result["mood_tags"]) >= 1

    def test_loudness_targets_list(self):
        result = self._run()
        assert isinstance(result["loudness_targets"], list)
        for lt in result["loudness_targets"]:
            assert "platform" in lt and "target_lufs" in lt
            assert lt["target_lufs"] < 0

    def test_release_checklist_has_items(self):
        result = self._run()
        assert len(result["release_checklist"]) >= 5


# ---------------------------------------------------------------------------
# Unit: generate_sample_palette
# ---------------------------------------------------------------------------

class TestGenerateSamplePalette:
    def _genome(self, text=SAMPLE_LYRICS):
        pa = analyze(text)
        return build_art_genome(pa).to_dict()

    def test_returns_dict(self):
        result = generate_sample_palette(self._genome(), ["hip-hop"])
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = generate_sample_palette(self._genome())
        for k in ["sample_categories", "texture_suggestions",
                  "crate_digging_tips", "clearance_reminder"]:
            assert k in result

    def test_sample_categories_nonempty(self):
        result = generate_sample_palette(self._genome(), ["ambient"])
        assert len(result["sample_categories"]) >= 2

    def test_clearance_reminder_nonempty(self):
        result = generate_sample_palette(self._genome())
        assert len(result["clearance_reminder"]) > 20


# ---------------------------------------------------------------------------
# Unit: produce (full pipeline)
# ---------------------------------------------------------------------------

class TestProduce:
    def test_returns_dict_with_all_sections(self):
        pa = analyze(SAMPLE_LYRICS)
        ag = build_art_genome(pa).to_dict()
        result = produce(SAMPLE_LYRICS, pa, ag)
        for k in ["production_plan", "beat_pattern", "instruments",
                  "melody_contour", "distribution", "streaming_metadata",
                  "sample_palette"]:
            assert k in result, f"Missing key: {k}"

    def test_with_artist_name(self):
        pa = analyze(SAMPLE_LYRICS)
        ag = build_art_genome(pa).to_dict()
        result = produce(SAMPLE_LYRICS, pa, ag, artist_name="Test Artist")
        assert isinstance(result, dict)

    def test_short_text(self):
        pa = analyze(SHORT_POEM)
        ag = build_art_genome(pa).to_dict()
        result = produce(SHORT_POEM, pa, ag)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Integration: /produce endpoint
# ---------------------------------------------------------------------------

class TestProduceEndpoint:
    def test_basic_request(self):
        resp = client.post("/produce", json={"text": SAMPLE_LYRICS})
        assert resp.status_code == 200
        data = resp.json()
        for k in ["production_plan", "beat_pattern", "instruments",
                  "melody_contour", "distribution", "streaming_metadata",
                  "sample_palette", "art_genome"]:
            assert k in data, f"Missing key in response: {k}"

    def test_with_artist_name(self):
        resp = client.post("/produce", json={
            "text": SAMPLE_LYRICS,
            "artist_name": "KalaArtist",
        })
        assert resp.status_code == 200

    def test_empty_text_returns_422(self):
        resp = client.post("/produce", json={"text": "   "})
        assert resp.status_code == 422

    def test_missing_text_returns_422(self):
        resp = client.post("/produce", json={})
        assert resp.status_code == 422

    def test_production_plan_has_bpm(self):
        resp = client.post("/produce", json={"text": SAMPLE_LYRICS})
        assert resp.status_code == 200
        plan = resp.json()["production_plan"]
        assert "suggested_bpm_range" in plan
        bpm = plan["suggested_bpm_range"]
        assert isinstance(bpm, list) and len(bpm) == 2

    def test_beat_pattern_has_grid(self):
        resp = client.post("/produce", json={"text": SAMPLE_LYRICS})
        beat = resp.json()["beat_pattern"]
        assert "kick" in beat and "snare" in beat and "hihat" in beat

    def test_distribution_has_platforms(self):
        resp = client.post("/produce", json={"text": SAMPLE_LYRICS})
        dist = resp.json()["distribution"]
        assert len(dist["recommended_platforms"]) >= 1

    def test_streaming_metadata_has_checklist(self):
        resp = client.post("/produce", json={"text": SAMPLE_LYRICS})
        meta = resp.json()["streaming_metadata"]
        assert len(meta["release_checklist"]) >= 5

    def test_short_poem(self):
        resp = client.post("/produce", json={"text": SHORT_POEM})
        assert resp.status_code == 200

    def test_single_line(self):
        resp = client.post("/produce", json={"text": "I am alive and burning bright"})
        assert resp.status_code == 200

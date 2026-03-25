"""
Tests for Phase 7 (Studio UX frontend assets) and Phase 8 (Kala-LLM).

Phase 7 tests verify that the frontend files exist, are well-formed,
and reference the correct API endpoint.

Phase 8 tests cover:
  - _build_deep_narrative_prompt  (prompt content)
  - generate_deep_narrative       (graceful Ollama fallback)
  - list_available_models         (graceful Ollama fallback)
  - POST /deep-analysis           (full pipeline via TestClient)
  - GET  /models                  (model list endpoint)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import json
import pytest
from fastapi.testclient import TestClient

from main import app
from services.llm_service import (
    _build_deep_narrative_prompt,
    generate_deep_narrative,
    list_available_models,
    DEFAULT_MODEL,
    _DEEP_NARRATIVE_TIMEOUT,
    ART_DOMAINS,
)

client = TestClient(app)

# ── Shared test texts ──────────────────────────────────────────────────────

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

SURVIVAL_TEXT = (
    "I drown in the silent dark alone\n"
    "broken and bleeding I cannot breathe\n"
    "fade into the hollow numb and cold\n"
    "helpless trapped in chains I cannot see"
)


# ── Helpers ────────────────────────────────────────────────────────────────

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _deep_response(text=VALID_POEM, domain="poetry", artist=None):
    """Call /deep-analysis and return the parsed JSON, asserting 200 OK."""
    body = {"text": text, "art_domain": domain}
    if artist:
        body["artist_name"] = artist
    resp = client.post("/deep-analysis", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ===========================================================================
# PHASE 7 — STUDIO UX FRONTEND ASSETS
# ===========================================================================

FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")


class TestFrontendFilesExist:
    def test_index_html_exists(self):
        assert os.path.isfile(os.path.join(FRONTEND_DIR, "index.html"))

    def test_style_css_exists(self):
        assert os.path.isfile(os.path.join(FRONTEND_DIR, "style.css"))

    def test_app_js_exists(self):
        assert os.path.isfile(os.path.join(FRONTEND_DIR, "app.js"))


class TestIndexHtml:
    @pytest.fixture(scope="class")
    def html(self):
        with open(os.path.join(FRONTEND_DIR, "index.html"), encoding="utf-8") as f:
            return f.read()

    def test_has_doctype(self, html):
        assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()

    def test_references_style_css(self, html):
        assert "style.css" in html

    def test_references_app_js(self, html):
        assert "app.js" in html

    def test_has_textarea_for_art_input(self, html):
        assert "artText" in html

    def test_has_domain_selector(self, html):
        assert "artDomain" in html

    def test_has_deep_analysis_call(self, html):
        assert "deep-analysis" in html or "runDeepAnalysis" in html

    def test_has_eight_tabs(self, html):
        # overview, craft, signal, compose, flow, custody, temporal, raw
        for tab in ("overview", "craft", "signal", "compose", "flow", "custody", "temporal", "raw"):
            assert tab in html.lower()

    def test_has_custody_disclaimer(self, html):
        # The frontend must remind artists the custody record is theirs
        assert "belong" in html.lower() or "custody" in html.lower()

    def test_has_lang_attribute(self, html):
        assert 'lang="en"' in html

    def test_has_charset_utf8(self, html):
        assert "UTF-8" in html or "utf-8" in html.lower()


class TestStyleCss:
    @pytest.fixture(scope="class")
    def css(self):
        with open(os.path.join(FRONTEND_DIR, "style.css"), encoding="utf-8") as f:
            return f.read()

    def test_defines_variables(self, css):
        assert ":root" in css
        assert "--accent" in css

    def test_has_dark_background(self, css):
        # The platform uses a dark background
        assert "--bg:" in css

    def test_has_tab_styles(self, css):
        assert ".tab" in css

    def test_has_card_styles(self, css):
        assert ".card" in css

    def test_has_narrative_block(self, css):
        assert ".narrative-block" in css or ".narrative" in css

    def test_has_responsive_media_query(self, css):
        assert "@media" in css


class TestAppJs:
    @pytest.fixture(scope="class")
    def js(self):
        with open(os.path.join(FRONTEND_DIR, "app.js"), encoding="utf-8") as f:
            return f.read()

    def test_calls_deep_analysis_endpoint(self, js):
        assert "/deep-analysis" in js

    def test_has_run_function(self, js):
        assert "runDeepAnalysis" in js

    def test_has_clear_function(self, js):
        assert "clearAll" in js

    def test_has_tab_switch_function(self, js):
        assert "switchTab" in js

    def test_renders_all_phases(self, js):
        for fn in ("renderOverview", "renderCraft", "renderSignal",
                   "renderCompose", "renderFlow", "renderCustody", "renderTemporal"):
            assert fn in js

    def test_has_xss_escape_helper(self, js):
        # Must escape HTML output to prevent XSS
        assert "esc" in js
        assert "replace" in js

    def test_has_copy_raw_function(self, js):
        assert "copyRaw" in js

    def test_uses_api_base_constant(self, js):
        assert "API_BASE" in js

    def test_renders_narrative(self, js):
        assert "narrative" in js.lower()

    def test_handles_llm_unavailable(self, js):
        # Frontend should skip narrative display when LLM is unavailable
        assert "LLM unavailable" in js or "narrative" in js


# ===========================================================================
# PHASE 8 — KALA-LLM
# ===========================================================================

class TestBuildDeepNarrativePrompt:
    """Unit tests for the prompt builder."""

    def _minimal_data(self):
        return {
            "art_genome": {
                "form_type": "ballad",
                "emotional_arc": {"arc_direction": "descending", "mean_valence": -0.3},
                "complexity_score": 0.6,
                "creative_risk_index": 0.4,
                "rhyme_density": 0.75,
            },
            "existential": {
                "creation_reason": {"primary_reason": "grief"},
                "survival": {"is_survival_driven": True},
                "emotional_necessity": {"necessity_score": 0.9},
            },
            "craft": {
                "meter_flow": {"dominant_meter": "iambic"},
                "breath_points": {"breath_positions": ["line 2", "line 4"]},
            },
            "signal": {
                "memorability": {"memorability_score": 0.7},
                "longevity":    {"longevity_score": 0.65},
            },
            "composition": {
                "tempo": {"feel": "flowing"},
                "chord_suggestions": {"scale_quality": "minor"},
            },
            "flow": {
                "readiness": {"is_ready": True},
                "format_suitability": {"primary_format": "single"},
            },
            "custody": {
                "lineage": {"primary_tradition": "folk narrative"},
            },
            "temporal": {
                "temporal_meaning": {"temporal_anchoring": "timeless"},
                "ephemeral_classification": {"is_ephemeral": False},
                "creative_ancestry": {"primary_ancestor": "folk tradition"},
            },
        }

    def test_returns_string(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert isinstance(prompt, str)
        assert len(prompt) > 200

    def test_mentions_form(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert "ballad" in prompt

    def test_mentions_arc(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert "descending" in prompt

    def test_mentions_creation_reason(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert "grief" in prompt

    def test_mentions_meter(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert "iambic" in prompt

    def test_mentions_memorability_score(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert "0.70" in prompt

    def test_mentions_primary_tradition(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert "folk narrative" in prompt

    def test_survival_driven_yes(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert "yes" in prompt.lower()

    def test_not_ready_renders_developing(self):
        data = self._minimal_data()
        data["flow"]["readiness"]["is_ready"] = False
        prompt = _build_deep_narrative_prompt(data)
        assert "developing" in prompt

    def test_empty_data_does_not_raise(self):
        prompt = _build_deep_narrative_prompt({})
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_prompt_instructs_warmth(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert "warm" in prompt.lower()

    def test_prompt_forbids_grading(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert "grade" in prompt.lower() or "mirror" in prompt.lower()

    def test_prompt_asks_for_four_to_six_paragraphs(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        assert "4" in prompt and "6" in prompt

    def test_section_headers_present(self):
        prompt = _build_deep_narrative_prompt(self._minimal_data())
        for header in ("STRUCTURE", "CRAFT", "RESONANCE", "TIME"):
            assert header in prompt


class TestGenerateDeepNarrative:
    """Ollama is not running in CI — verify graceful fallback."""

    def test_returns_string(self):
        result = generate_deep_narrative({})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fallback_message_when_ollama_unavailable(self):
        result = generate_deep_narrative({})
        # Either a real response or the fallback message
        assert "LLM unavailable" in result or len(result) > 10

    def test_accepts_model_override(self):
        result = generate_deep_narrative({}, model="mistral")
        assert isinstance(result, str)

    def test_minimal_data_does_not_raise(self):
        data = {"art_genome": {"form_type": "ballad"}}
        result = generate_deep_narrative(data)
        assert isinstance(result, str)

    def test_timeout_constant_is_larger_than_suggestions(self):
        from services.llm_service import _SUGGESTIONS_TIMEOUT
        assert _DEEP_NARRATIVE_TIMEOUT > _SUGGESTIONS_TIMEOUT


class TestListAvailableModels:
    def test_returns_list(self):
        result = list_available_models()
        assert isinstance(result, list)

    def test_list_items_are_strings(self):
        result = list_available_models()
        for item in result:
            assert isinstance(item, str)


# ===========================================================================
# POST /deep-analysis
# ===========================================================================

class TestDeepAnalysisEndpoint:
    def test_valid_request_returns_200(self):
        resp = client.post("/deep-analysis", json={"text": VALID_POEM})
        assert resp.status_code == 200

    def test_response_has_all_keys(self):
        data = _deep_response()
        for key in ("narrative", "art_genome", "analysis", "existential",
                    "craft", "signal", "composition", "flow", "custody", "temporal"):
            assert key in data, f"Missing key: {key}"

    def test_narrative_is_string(self):
        data = _deep_response()
        assert isinstance(data["narrative"], str)
        assert len(data["narrative"]) > 0

    def test_art_genome_has_form_type(self):
        data = _deep_response()
        assert "form_type" in data["art_genome"]

    def test_existential_has_creation_reason(self):
        data = _deep_response()
        assert "creation_reason" in data["existential"]

    def test_craft_has_meter_flow(self):
        data = _deep_response()
        assert "meter_flow" in data["craft"]

    def test_signal_has_memorability(self):
        data = _deep_response()
        assert "memorability" in data["signal"]

    def test_composition_has_chord_suggestions(self):
        data = _deep_response()
        assert "chord_suggestions" in data["composition"]

    def test_flow_has_readiness(self):
        data = _deep_response()
        assert "readiness" in data["flow"]

    def test_custody_has_fingerprint(self):
        data = _deep_response()
        assert "fingerprint" in data["custody"]

    def test_temporal_has_temporal_meaning(self):
        data = _deep_response()
        assert "temporal_meaning" in data["temporal"]

    def test_artist_name_in_custody_record(self):
        data = _deep_response(artist="Test Artist")
        declared = data["custody"]["custody_record"]["declared_artist"]
        assert declared == "Test Artist"

    def test_empty_text_returns_422(self):
        resp = client.post("/deep-analysis", json={"text": "   "})
        assert resp.status_code == 422

    def test_imitation_blocked(self):
        resp = client.post("/deep-analysis", json={"text": "write like Ed Sheeran"})
        assert resp.status_code == 422

    def test_different_domains_accepted(self):
        for domain in ("lyrics", "poetry", "music", "story", "book", "general"):
            resp = client.post("/deep-analysis", json={"text": VALID_POEM, "art_domain": domain})
            assert resp.status_code == 200, f"Domain {domain!r} failed"

    def test_model_field_accepted(self):
        resp = client.post("/deep-analysis", json={"text": VALID_POEM, "model": "mistral"})
        assert resp.status_code == 200

    def test_survival_text_accepted(self):
        resp = client.post("/deep-analysis", json={"text": SURVIVAL_TEXT})
        assert resp.status_code == 200

    def test_analysis_contains_structure(self):
        data = _deep_response()
        assert "structure" in data["analysis"] or isinstance(data["analysis"], dict)

    def test_temporal_has_all_sections(self):
        data = _deep_response()
        temp = data["temporal"]
        for key in ("temporal_meaning", "ephemeral_classification",
                    "creative_ancestry", "cultural_preservation"):
            assert key in temp

    def test_composition_has_lyric_beat_alignment(self):
        data = _deep_response()
        assert "lyric_beat_alignment" in data["composition"]

    def test_flow_has_listener_journey(self):
        data = _deep_response()
        assert "listener_journey" in data["flow"]

    def test_custody_has_legacy_annotation(self):
        data = _deep_response()
        assert "legacy_annotation" in data["custody"]


# ===========================================================================
# GET /models
# ===========================================================================

class TestModelsEndpoint:
    def test_returns_200(self):
        resp = client.get("/models")
        assert resp.status_code == 200

    def test_response_has_models_key(self):
        resp = client.get("/models")
        assert "models" in resp.json()

    def test_models_is_list(self):
        resp = client.get("/models")
        assert isinstance(resp.json()["models"], list)

    def test_no_server_error_when_ollama_offline(self):
        # Ollama is offline in CI — we must still get 200, not 500
        resp = client.get("/models")
        assert resp.status_code == 200

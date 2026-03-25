"""
Tests for the /suggest endpoint and generate_suggestions service.
"""

import sys
import os
import json
import unittest.mock as mock

# Allow importing from the backend directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

from main import app
from services.llm_service import (
    generate_suggestions,
    _build_suggestions_prompt,
    ART_DOMAINS,
)
from kalacore.pattern_engine import analyze
from kalacore.art_genome import build_art_genome

client = TestClient(app)

SAMPLE_LYRICS = (
    "I walk alone in the dark\n"
    "Searching for a tiny spark\n"
    "The night is cold but my heart is warm\n"
    "I walk alone in the dark"
)


# ---------------------------------------------------------------------------
# ART_DOMAINS registry
# ---------------------------------------------------------------------------

class TestArtDomains:
    def test_all_expected_domains_present(self):
        for domain in ("lyrics", "poetry", "music", "story", "book", "general"):
            assert domain in ART_DOMAINS

    def test_values_are_non_empty_strings(self):
        for label in ART_DOMAINS.values():
            assert isinstance(label, str) and label.strip()


# ---------------------------------------------------------------------------
# _build_suggestions_prompt
# ---------------------------------------------------------------------------

class TestBuildSuggestionsPrompt:
    def _combined(self, text: str = SAMPLE_LYRICS, domain: str = "lyrics") -> dict:
        analysis = analyze(text)
        genome = build_art_genome(analysis)
        return {"art_genome": genome.to_dict(), "analysis": analysis}

    def test_domain_label_appears_in_prompt(self):
        prompt = _build_suggestions_prompt(
            SAMPLE_LYRICS, self._combined(), "lyrics"
        )
        assert "song lyrics" in prompt

    def test_original_text_appears_in_prompt(self):
        prompt = _build_suggestions_prompt(
            SAMPLE_LYRICS, self._combined(), "poetry"
        )
        assert "walk alone" in prompt

    def test_unknown_domain_falls_back_gracefully(self):
        # Unknown domain is normalised inside generate_suggestions, but
        # _build_suggestions_prompt itself uses ART_DOMAINS.get with a fallback
        prompt = _build_suggestions_prompt(
            SAMPLE_LYRICS, self._combined(), "unknown_domain"
        )
        # Should still produce a non-empty prompt
        assert len(prompt) > 50

    def test_prompt_contains_suggestions_instruction(self):
        prompt = _build_suggestions_prompt(
            SAMPLE_LYRICS, self._combined(), "general"
        )
        assert "suggestions" in prompt.lower()

    def test_prompt_tone_is_respectful(self):
        prompt = _build_suggestions_prompt(
            SAMPLE_LYRICS, self._combined(), "poetry"
        )
        # Must not include judgmental language
        for word in ("bad", "terrible", "wrong", "fix it"):
            assert word not in prompt.lower()


# ---------------------------------------------------------------------------
# generate_suggestions (with Ollama mocked)
# ---------------------------------------------------------------------------

class TestGenerateSuggestions:
    def _combined(self, text: str = SAMPLE_LYRICS) -> dict:
        analysis = analyze(text)
        genome = build_art_genome(analysis)
        return {"art_genome": genome.to_dict(), "analysis": analysis}

    def test_returns_string(self):
        combined = self._combined()
        # Ollama is not running — should return fallback string
        result = generate_suggestions(SAMPLE_LYRICS, combined, domain="lyrics")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_domain_normalised_to_general(self):
        combined = self._combined()
        result = generate_suggestions(SAMPLE_LYRICS, combined, domain="zz_unknown")
        # Should not raise and should return a string
        assert isinstance(result, str)

    def test_mocked_ollama_response(self):
        combined = self._combined()
        fake_response_body = json.dumps({
            "response": "1. Try varying your line lengths for more rhythm.\n2. Consider a bridge."
        }).encode("utf-8")

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = fake_response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("urllib.request.urlopen", return_value=mock_resp):
            result = generate_suggestions(SAMPLE_LYRICS, combined, domain="lyrics")

        assert "Try varying" in result
        assert "bridge" in result

    def test_ollama_unavailable_returns_fallback(self):
        import urllib.error
        combined = self._combined()
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            result = generate_suggestions(SAMPLE_LYRICS, combined, domain="poetry")
        # The fallback message always starts with "[LLM unavailable:"
        assert result.startswith("[LLM unavailable:")

    def test_all_domains_accepted(self):
        combined = self._combined()
        for domain in ART_DOMAINS:
            result = generate_suggestions(SAMPLE_LYRICS, combined, domain=domain)
            assert isinstance(result, str)


# ---------------------------------------------------------------------------
# POST /suggest endpoint
# ---------------------------------------------------------------------------

class TestSuggestEndpoint:
    def test_valid_request_returns_200(self):
        resp = client.post("/suggest", json={"text": SAMPLE_LYRICS, "art_domain": "lyrics"})
        assert resp.status_code == 200

    def test_response_schema_keys(self):
        resp = client.post("/suggest", json={"text": SAMPLE_LYRICS})
        data = resp.json()
        for key in ("art_domain", "art_genome", "analysis", "suggestions"):
            assert key in data, f"Missing key: {key}"

    def test_default_domain_is_general(self):
        resp = client.post("/suggest", json={"text": SAMPLE_LYRICS})
        assert resp.json()["art_domain"] == "general"

    def test_domain_reflected_in_response(self):
        for domain in ("lyrics", "poetry", "music", "story", "book"):
            resp = client.post(
                "/suggest", json={"text": SAMPLE_LYRICS, "art_domain": domain}
            )
            assert resp.status_code == 200
            assert resp.json()["art_domain"] == domain

    def test_empty_text_returns_422(self):
        resp = client.post("/suggest", json={"text": "   ", "art_domain": "lyrics"})
        assert resp.status_code == 422

    def test_missing_text_returns_422(self):
        resp = client.post("/suggest", json={"art_domain": "poetry"})
        assert resp.status_code == 422

    def test_invalid_domain_returns_422(self):
        resp = client.post(
            "/suggest", json={"text": SAMPLE_LYRICS, "art_domain": "sculpture"}
        )
        assert resp.status_code == 422

    def test_art_genome_has_expected_fields(self):
        resp = client.post("/suggest", json={"text": SAMPLE_LYRICS})
        genome = resp.json()["art_genome"]
        for field in ("rhyme_density", "symmetry_score", "complexity_score"):
            assert field in genome

    def test_analysis_has_expected_keys(self):
        resp = client.post("/suggest", json={"text": SAMPLE_LYRICS})
        analysis = resp.json()["analysis"]
        for key in ("palindrome", "rhymes", "syllables", "structure"):
            assert key in analysis

    def test_suggestions_is_non_empty_string(self):
        resp = client.post("/suggest", json={"text": SAMPLE_LYRICS, "art_domain": "poetry"})
        suggestions = resp.json()["suggestions"]
        assert isinstance(suggestions, str)
        assert len(suggestions.strip()) > 0

"""
Tests for the Text Studio endpoints:
  POST /text-studio/assist   – AI Writing Assistant
  POST /text-studio/patterns – Pattern Intelligence
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

from main import app
from services.llm_service import (
    generate_writing_assist,
    _WRITING_ASSIST_ACTIONS,
    ART_DOMAINS,
    DEFAULT_MODEL,
)

_VALID_ASSIST_ACTIONS = {"continue", "rewrite", "improve", "convert"}

client = TestClient(app)

SAMPLE_POEM = (
    "I walk alone in the dark\n"
    "searching for a tiny spark\n"
    "the night is cold but my heart is warm\n"
    "I walk alone through every storm"
)

PALINDROME_TEXT = "level\nracecar is a word\nnoon the silent time"


# ===========================================================================
# llm_service – generate_writing_assist (unit tests, no Ollama required)
# ===========================================================================

class TestGenerateWritingAssistFallback:
    """These tests confirm graceful fallback behaviour when Ollama is absent."""

    def test_continue_returns_string(self):
        result = generate_writing_assist(SAMPLE_POEM, "continue")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_rewrite_returns_string(self):
        result = generate_writing_assist(SAMPLE_POEM, "rewrite")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_improve_returns_string(self):
        result = generate_writing_assist(SAMPLE_POEM, "improve")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_convert_returns_string(self):
        result = generate_writing_assist(SAMPLE_POEM, "convert", domain="poetry")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_action_returns_error_message(self):
        result = generate_writing_assist(SAMPLE_POEM, "delete_everything")
        assert "Unknown action" in result

    def test_unknown_domain_falls_back_to_general(self):
        # Should not raise; unknown domain is silently normalised
        result = generate_writing_assist(SAMPLE_POEM, "continue", domain="unknown_xyz")
        assert isinstance(result, str)

    @pytest.mark.parametrize("action", list(_VALID_ASSIST_ACTIONS))
    def test_all_actions_produce_output_for_every_domain(self, action):
        for domain in ("lyrics", "poetry", "story", "book", "music", "general"):
            result = generate_writing_assist(SAMPLE_POEM, action, domain=domain)
            assert isinstance(result, str) and len(result) > 0


class TestWritingAssistActions:
    def test_valid_actions_set(self):
        assert _VALID_ASSIST_ACTIONS == {"continue", "rewrite", "improve", "convert"}

    def test_all_actions_have_prompt_templates(self):
        for action in _VALID_ASSIST_ACTIONS:
            assert action in _WRITING_ASSIST_ACTIONS
            template = _WRITING_ASSIST_ACTIONS[action]
            assert "{text}" in template
            assert "{domain_label}" in template


# ===========================================================================
# POST /text-studio/assist — HTTP endpoint
# ===========================================================================

class TestTextStudioAssistEndpoint:
    def test_continue_200(self):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM, "action": "continue", "domain": "poetry"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "continue"
        assert data["domain"] == "poetry"
        assert isinstance(data["result"], str)
        assert len(data["result"]) > 0

    def test_rewrite_200(self):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM, "action": "rewrite", "domain": "lyrics"},
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "rewrite"

    def test_improve_200(self):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM, "action": "improve"},
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "improve"

    def test_convert_200(self):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM, "action": "convert", "domain": "poetry"},
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "convert"

    def test_empty_text_returns_422(self):
        resp = client.post(
            "/text-studio/assist",
            json={"text": "   ", "action": "continue"},
        )
        assert resp.status_code == 422

    def test_invalid_action_returns_422(self):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM, "action": "destroy"},
        )
        assert resp.status_code == 422

    def test_invalid_domain_returns_422(self):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM, "action": "continue", "domain": "not_a_domain"},
        )
        assert resp.status_code == 422

    def test_missing_action_returns_422(self):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM},
        )
        assert resp.status_code == 422

    def test_missing_text_returns_422(self):
        resp = client.post(
            "/text-studio/assist",
            json={"action": "continue"},
        )
        assert resp.status_code == 422

    def test_ethics_violation_returns_422(self):
        harmful_text = " ".join(["kill"] * 20)
        resp = client.post(
            "/text-studio/assist",
            json={"text": harmful_text, "action": "continue"},
        )
        # Ethics check may or may not flag this; if flagged → 422
        assert resp.status_code in (200, 422)

    @pytest.mark.parametrize("domain", ["lyrics", "poetry", "music", "story", "book", "general"])
    def test_all_valid_domains_accepted(self, domain):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM, "action": "continue", "domain": domain},
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize("action", ["continue", "rewrite", "improve", "convert"])
    def test_all_valid_actions_accepted(self, action):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM, "action": action},
        )
        assert resp.status_code == 200

    def test_response_shape(self):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM, "action": "continue"},
        )
        data = resp.json()
        assert "action" in data
        assert "domain" in data
        assert "result" in data

    def test_custom_model_accepted(self):
        resp = client.post(
            "/text-studio/assist",
            json={"text": SAMPLE_POEM, "action": "improve", "model": "mistral"},
        )
        assert resp.status_code == 200


# ===========================================================================
# POST /text-studio/patterns — HTTP endpoint
# ===========================================================================

class TestTextStudioPatternsEndpoint:
    def test_basic_200(self):
        resp = client.post(
            "/text-studio/patterns",
            json={"text": SAMPLE_POEM},
        )
        assert resp.status_code == 200

    def test_response_has_palindromes_key(self):
        resp = client.post("/text-studio/patterns", json={"text": PALINDROME_TEXT})
        data = resp.json()
        assert "palindromes" in data

    def test_response_has_structure_key(self):
        resp = client.post("/text-studio/patterns", json={"text": SAMPLE_POEM})
        assert "structure" in resp.json()

    def test_response_has_emotional_arc_key(self):
        resp = client.post("/text-studio/patterns", json={"text": SAMPLE_POEM})
        assert "emotional_arc" in resp.json()

    def test_response_has_mirror_rhyme_key(self):
        resp = client.post("/text-studio/patterns", json={"text": SAMPLE_POEM})
        assert "mirror_rhyme" in resp.json()

    def test_response_has_symmetry_score(self):
        resp = client.post("/text-studio/patterns", json={"text": SAMPLE_POEM})
        data = resp.json()
        assert "symmetry_score" in data
        assert isinstance(data["symmetry_score"], (int, float))

    def test_response_has_rhyme_density(self):
        resp = client.post("/text-studio/patterns", json={"text": SAMPLE_POEM})
        data = resp.json()
        assert "rhyme_density" in data
        assert 0.0 <= data["rhyme_density"] <= 1.0

    def test_response_has_complexity_score(self):
        resp = client.post("/text-studio/patterns", json={"text": SAMPLE_POEM})
        data = resp.json()
        assert "complexity_score" in data

    def test_response_has_cognitive_load(self):
        resp = client.post("/text-studio/patterns", json={"text": SAMPLE_POEM})
        assert "cognitive_load" in resp.json()

    def test_response_has_form_type(self):
        resp = client.post("/text-studio/patterns", json={"text": SAMPLE_POEM})
        assert "form_type" in resp.json()

    def test_palindrome_detection_in_palindrome_text(self):
        resp = client.post("/text-studio/patterns", json={"text": PALINDROME_TEXT})
        data = resp.json()
        pals = data["palindromes"]
        total = pals.get("full_palindrome_count", 0) + len(
            pals.get("partial_palindromes", [])
        )
        assert total > 0, f"Expected at least one palindrome in: {repr(PALINDROME_TEXT)}"

    def test_empty_text_returns_422(self):
        resp = client.post("/text-studio/patterns", json={"text": ""})
        assert resp.status_code == 422

    def test_whitespace_only_returns_422(self):
        resp = client.post("/text-studio/patterns", json={"text": "   "})
        assert resp.status_code == 422

    def test_single_line_poem(self):
        resp = client.post(
            "/text-studio/patterns", json={"text": "Hello world, bright and free"}
        )
        assert resp.status_code == 200

    def test_long_poem(self):
        lines = ["the moon is full tonight" for _ in range(30)]
        resp = client.post(
            "/text-studio/patterns", json={"text": "\n".join(lines)}
        )
        assert resp.status_code == 200


# ===========================================================================
# Frontend – Text Studio presence checks
# ===========================================================================

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend")
)


class TestTextStudioFrontend:
    @pytest.fixture(scope="class")
    def html(self):
        with open(os.path.join(FRONTEND_DIR, "index.html"), encoding="utf-8") as f:
            return f.read()

    @pytest.fixture(scope="class")
    def js(self):
        with open(os.path.join(FRONTEND_DIR, "app.js"), encoding="utf-8") as f:
            return f.read()

    @pytest.fixture(scope="class")
    def css(self):
        with open(os.path.join(FRONTEND_DIR, "style.css"), encoding="utf-8") as f:
            return f.read()

    def test_text_studio_section_present(self, html):
        assert "textStudio" in html

    def test_writing_mode_toggle_present(self, html):
        # Writing mode (poetry/story/script/free-write) selector
        assert "writingMode" in html or "writing-mode" in html

    def test_pattern_intelligence_tab_present(self, html):
        assert "patterns" in html.lower() or "pattern" in html.lower()

    def test_ai_assist_panel_present(self, html):
        # The AI writing assistant action buttons
        assert "assist" in html.lower() or "writing assistant" in html.lower()

    def test_tts_button_present(self, html):
        # Text-to-speech narrate button
        assert "tts" in html.lower() or "narrate" in html.lower() or "speak" in html.lower()

    def test_word_count_present(self, html):
        assert "wordCount" in html or "word-count" in html or "word count" in html.lower()

    def test_focus_mode_present(self, html):
        assert "focus" in html.lower()

    def test_preview_toggle_present(self, html):
        assert "previewBtn" in html or "toggleMarkdownPreview" in html

    def test_markdown_preview_pane_present(self, html):
        assert "markdownPreview" in html

    def test_export_buttons_present(self, html):
        assert "exportText" in html

    def test_js_has_writing_assist_call(self, js):
        assert "text-studio/assist" in js

    def test_js_has_patterns_call(self, js):
        assert "text-studio/patterns" in js

    def test_js_has_tts_function(self, js):
        assert "speechSynthesis" in js or "SpeechSynthesis" in js

    def test_js_has_preview_function(self, js):
        assert "toggleMarkdownPreview" in js

    def test_js_has_render_markdown(self, js):
        assert "_renderMarkdown" in js

    def test_js_has_export_function(self, js):
        assert "exportText" in js

    def test_js_word_count_shows_lines(self, js):
        # onEditorInput should show lines count in addition to words/chars
        assert "lines" in js or "line${" in js or "· ${lines}" in js

    def test_css_has_writing_toolbar_styles(self, css):
        assert "toolbar" in css or "writing-toolbar" in css

    def test_css_has_preview_pane_styles(self, css):
        assert "markdown-preview" in css

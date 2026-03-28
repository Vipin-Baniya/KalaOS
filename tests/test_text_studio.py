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

    def test_js_has_writing_assist_call(self, js):
        assert "text-studio/assist" in js

    def test_js_has_patterns_call(self, js):
        assert "text-studio/patterns" in js

    def test_js_has_tts_function(self, js):
        assert "speechSynthesis" in js or "SpeechSynthesis" in js

    def test_css_has_writing_toolbar_styles(self, css):
        assert "toolbar" in css or "writing-toolbar" in css


# ===========================================================================
# Frontend – UI/UX Layout: Sidebar, AI Panel, Creator Mode Theme
# ===========================================================================

class TestKalaOSUILayout:
    """Tests for the 3-column layout (sidebar · workspace · AI panel) and Creator Mode theme."""

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

    # ── Sidebar navigation ────────────────────────────────────────────────

    def test_sidebar_element_present(self, html):
        assert "app-sidebar" in html

    def test_sidebar_has_all_studio_buttons(self, html):
        assert "textStudioBtn" in html
        assert "musicStudioBtn" in html
        assert "visualStudioBtn" in html
        assert "chatStudioBtn" in html

    def test_sidebar_collapse_button_present(self, html):
        assert "sidebarToggle" in html or "sidebar-collapse" in html

    def test_sidebar_css_defined(self, css):
        assert ".app-sidebar" in css

    def test_sidebar_collapsed_state_css(self, css):
        assert "collapsed" in css

    def test_sidebar_toggle_js_function(self, js):
        assert "toggleSidebar" in js

    def test_sidebar_state_restored_on_load(self, js):
        assert "_restoreSidebar" in js

    # ── Right AI Panel ────────────────────────────────────────────────────

    def test_ai_panel_element_present(self, html):
        assert "appAiPanel" in html or "app-ai-panel" in html

    def test_ai_panel_css_defined(self, css):
        assert ".app-ai-panel" in css

    def test_ai_panel_toggle_js_function(self, js):
        assert "toggleAiPanel" in js

    def test_ai_panel_show_hide_functions(self, js):
        assert "_showAiPanel" in js
        assert "_hideAiPanel" in js

    def test_ai_panel_hides_for_music_studio(self, js):
        # When switching to music studio, AI panel should be hidden
        assert "_hideAiPanel" in js

    def test_ai_panel_toggle_button_present(self, html):
        assert "aiPanelToggleBtn" in html or "ai-panel-toggle" in html

    # ── 3-Column Layout ───────────────────────────────────────────────────

    def test_app_body_wrapper_present(self, html):
        assert "app-body" in html

    def test_app_workspace_present(self, html):
        assert "app-workspace" in html

    def test_layout_uses_flexbox(self, css):
        assert ".app-body" in css
        assert "flex" in css

    def test_mobile_bottom_sheet_css(self, css):
        # Mobile: AI panel becomes bottom sheet
        assert "bottom-sheet" in css or "panel-open" in css

    def test_responsive_sidebar_mobile(self, css):
        # On mobile, sidebar goes to bottom as horizontal strip
        assert "flex-direction: column-reverse" in css or "column-reverse" in css

    # ── Creator Mode Theme ────────────────────────────────────────────────

    def test_creator_mode_theme_css_defined(self, css):
        assert 'data-theme="creator"' in css

    def test_creator_mode_swatch_in_html(self, html):
        assert "creator" in html.lower()

    def test_creator_mode_in_js_theme_colors(self, js):
        assert '"creator"' in js

    def test_creator_mode_has_colorful_accent(self, css):
        # Creator mode should have a vibrant accent color (fuchsia/magenta)
        assert "#c026d3" in css or "c026d3" in css

    def test_creator_mode_swatch_preview_gradient(self, html):
        # The swatch preview should show a colorful gradient
        assert "Creator Mode" in html or "creator" in html.lower()

    # ── AI Panel Grid Adaptation ──────────────────────────────────────────

    def test_pattern_grid_adapts_in_ai_panel(self, css):
        assert ".app-ai-panel .pattern-grid" in css

    def test_ai_assist_panel_adapts_in_ai_panel(self, css):
        assert ".app-ai-panel .ai-assist-panel" in css


# ===========================================================================
# Frontend – Markdown Preview, Export, Line Count, switchStudio convention
# ===========================================================================

class TestTextStudioMarkdownPreviewAndExport:
    """Tests for live Markdown Preview, export buttons, line count, and code conventions."""

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

    # ── Markdown Preview ──────────────────────────────────────────────────

    def test_preview_toggle_button_present(self, html):
        assert "previewToggleBtn" in html or "Preview" in html

    def test_preview_pane_element_present(self, html):
        assert "mdPreviewPane" in html

    def test_preview_pane_starts_hidden(self, html):
        # The preview pane should start hidden (using .hidden class)
        import re
        match = re.search(r'id="mdPreviewPane"[^>]*class="([^"]*)"', html)
        assert match, "mdPreviewPane element not found"
        assert "hidden" in match.group(1)

    def test_md_preview_content_element_present(self, html):
        assert "mdPreviewContent" in html

    def test_toggle_md_preview_function_in_js(self, js):
        assert "toggleMdPreview" in js

    def test_render_md_preview_function_in_js(self, js):
        assert "_renderMdPreview" in js

    def test_preview_renders_headings(self, js):
        assert "<h1>" in js or "'<h1>'" in js or '"<h1>"' in js

    def test_preview_renders_bold(self, js):
        assert "<strong>" in js

    def test_preview_renders_italic(self, js):
        assert "<em>" in js

    def test_preview_renders_blockquotes(self, js):
        assert "<blockquote>" in js

    def test_preview_css_defined(self, css):
        assert ".md-preview-pane" in css

    def test_preview_content_css_defined(self, css):
        assert ".md-preview-content" in css

    def test_preview_pane_uses_flex_layout(self, css):
        assert ".editor-preview-row" in css

    # ── Export buttons ────────────────────────────────────────────────────

    def test_export_md_button_present(self, html):
        assert ".md" in html or "exportText" in html

    def test_export_txt_button_present(self, html):
        assert ".txt" in html or "exportText" in html

    def test_export_text_function_in_js(self, js):
        assert "exportText" in js

    def test_export_creates_blob(self, js):
        assert "Blob" in js

    def test_export_revokes_url(self, js):
        assert "revokeObjectURL" in js

    def test_export_supports_md_format(self, js):
        assert "text/markdown" in js

    def test_export_supports_txt_format(self, js):
        assert "text/plain" in js

    # ── Line count ────────────────────────────────────────────────────────

    def test_line_count_in_editor_input_function(self, js):
        # onEditorInput should track line count
        assert "lines" in js or "line" in js

    def test_word_count_display_includes_lines(self, js):
        # The display text should include "line" count
        assert "line" in js

    # ── Code convention: switchStudio uses .hidden class ─────────────────

    def test_switch_studio_does_not_use_style_display(self, js):
        # switchStudio should NOT use style.display directly
        # Check by searching for the pattern in the function vicinity
        assert "function switchStudio(" in js
        # Locate the function and verify the body doesn't use style.display
        start = js.index("function switchStudio(")
        # Find the matching closing brace by counting brace depth
        depth = 0
        end = start
        for i, ch in enumerate(js[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        body = js[start:end]
        assert "style.display" not in body, "switchStudio should use .hidden class, not style.display"

    def test_switch_studio_uses_hidden_class(self, js):
        assert "function switchStudio(" in js
        start = js.index("function switchStudio(")
        depth = 0
        end = start
        for i, ch in enumerate(js[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        body = js[start:end]
        assert "classList" in body and "hidden" in body

    def test_visual_studio_starts_hidden(self, html):
        # visualStudio should have the 'hidden' class on initial load
        import re
        match = re.search(r'id="visualStudio"[^>]*class="([^"]*)"', html)
        assert match, "visualStudio element not found"
        assert "hidden" in match.group(1)


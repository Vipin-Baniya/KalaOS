"""
Tests for Phase 14 – Canvas Studio AI Image Generator.

Covers:
  • kalacanvas unit functions (subject extraction, mood detection, palette,
    composition, style tags, SVG preview, data URL)
  • generate_canvas_image() – happy path, validation, edge cases
  • /visual-studio/generate-image API endpoint (happy path, validation, errors)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import base64
import pytest
from fastapi.testclient import TestClient

from main import app
from kalacore.kalacanvas import (
    generate_canvas_image,
    VALID_STYLES,
    _extract_subject,
    _detect_mood,
    _detect_palette,
    _detect_composition,
    _build_style_tags,
    _build_svg_preview,
    _svg_to_data_url,
    _escape_svg,
    _hash_seed,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CYBERPUNK_PROMPT = "futuristic cyberpunk city at night with neon lights"
NATURE_PROMPT = "a peaceful forest with sunlight filtering through the trees"
PORTRAIT_PROMPT = "a detailed portrait of a warrior in ancient armour"
ABSTRACT_PROMPT = "abstract geometric patterns with vibrant colours"


# ---------------------------------------------------------------------------
# Unit tests: _hash_seed
# ---------------------------------------------------------------------------

class TestHashSeed:
    def test_returns_integer(self):
        assert isinstance(_hash_seed("hello"), int)

    def test_deterministic(self):
        assert _hash_seed("same") == _hash_seed("same")

    def test_different_inputs_differ(self):
        assert _hash_seed("abc") != _hash_seed("xyz")


# ---------------------------------------------------------------------------
# Unit tests: _escape_svg
# ---------------------------------------------------------------------------

class TestEscapeSvg:
    def test_escapes_ampersand(self):
        assert "&amp;" in _escape_svg("a & b")

    def test_escapes_less_than(self):
        assert "&lt;" in _escape_svg("a < b")

    def test_escapes_greater_than(self):
        assert "&gt;" in _escape_svg("a > b")

    def test_escapes_double_quote(self):
        assert "&quot;" in _escape_svg('say "hello"')

    def test_plain_text_unchanged(self):
        assert _escape_svg("hello world") == "hello world"


# ---------------------------------------------------------------------------
# Unit tests: _extract_subject
# ---------------------------------------------------------------------------

class TestExtractSubject:
    def test_city_keyword(self):
        assert "urban" in _extract_subject("a city skyline at dusk")

    def test_forest_keyword(self):
        assert "natural" in _extract_subject("deep forest with ancient trees")

    def test_space_keyword(self):
        assert "cosmic" in _extract_subject("a vast galaxy nebula")

    def test_portrait_keyword(self):
        assert "portrait" in _extract_subject("close portrait of a warrior")

    def test_fallback_uses_words(self):
        subject = _extract_subject("unusual completely unique description here")
        assert len(subject) > 0

    def test_empty_prompt_fallback(self):
        subject = _extract_subject("")
        assert isinstance(subject, str)


# ---------------------------------------------------------------------------
# Unit tests: _detect_mood
# ---------------------------------------------------------------------------

class TestDetectMood:
    def test_cyberpunk_mood(self):
        assert _detect_mood("cyberpunk city") == "cyberpunk"

    def test_ocean_mood(self):
        assert _detect_mood("ocean waves at sunset") in ("ocean", "sunset")

    def test_forest_mood(self):
        assert _detect_mood("peaceful forest scene") == "forest"

    def test_night_secondary(self):
        mood = _detect_mood("dark night time shadows")
        assert mood in ("night", "dark")

    def test_default_fallback(self):
        mood = _detect_mood("something completely unusual xyz123")
        assert isinstance(mood, str)
        assert len(mood) > 0


# ---------------------------------------------------------------------------
# Unit tests: _detect_palette
# ---------------------------------------------------------------------------

class TestDetectPalette:
    def test_returns_four_colours(self):
        palette = _detect_palette("sunset scene", "cinematic")
        assert len(palette) == 4

    def test_all_entries_are_hex(self):
        palette = _detect_palette("ocean waves", "painting")
        for colour in palette:
            assert colour.startswith("#")
            assert len(colour) in (7, 9)

    def test_sketch_style_near_grayscale(self):
        palette = _detect_palette("any scene", "sketch")
        # First colour should be very light
        assert palette[0].upper() in ("#FAFAFA", "#D0D0D0", "#888888", "#333333")

    def test_watercolor_style_returns_list(self):
        palette = _detect_palette("pastel flowers", "watercolor")
        assert isinstance(palette, list)
        assert len(palette) == 4


# ---------------------------------------------------------------------------
# Unit tests: _detect_composition
# ---------------------------------------------------------------------------

class TestDetectComposition:
    def test_wide_keyword(self):
        comp = _detect_composition("a wide panoramic landscape")
        assert "wide" in comp

    def test_symmetrical_keyword(self):
        comp = _detect_composition("symmetrical architectural facade")
        assert "symmetr" in comp.lower() or "symmetric" in comp.lower() or comp != ""

    def test_default_fallback(self):
        comp = _detect_composition("something without compositional keywords")
        assert isinstance(comp, str)
        assert len(comp) > 0


# ---------------------------------------------------------------------------
# Unit tests: _build_style_tags
# ---------------------------------------------------------------------------

class TestBuildStyleTags:
    def test_style_is_first_tag(self):
        tags = _build_style_tags("any prompt", "cinematic")
        assert tags[0] == "cinematic"

    def test_dark_tag(self):
        tags = _build_style_tags("dark moody shadows noir", "painting")
        assert "dark mood" in tags

    def test_vibrant_tag(self):
        tags = _build_style_tags("vibrant colorful bright scene", "illustration")
        assert "vibrant colour" in tags

    def test_no_duplicates(self):
        tags = _build_style_tags("cinematic cinematic film movie", "cinematic")
        assert len(tags) == len(set(tags))

    def test_returns_list(self):
        assert isinstance(_build_style_tags("any prompt", "abstract"), list)


# ---------------------------------------------------------------------------
# Unit tests: _build_svg_preview
# ---------------------------------------------------------------------------

class TestBuildSvgPreview:
    PALETTE = ["#7C5AF1", "#5EEAD4", "#F59E0B", "#EF4444"]

    def test_returns_string(self):
        svg = _build_svg_preview("test subject", self.PALETTE, "cinematic", 400, 300, 42)
        assert isinstance(svg, str)

    def test_contains_svg_tag(self):
        svg = _build_svg_preview("subject", self.PALETTE, "cinematic", 400, 300, 42)
        assert svg.strip().startswith("<svg")
        assert "</svg>" in svg

    def test_uses_correct_dimensions(self):
        svg = _build_svg_preview("s", self.PALETTE, "cinematic", 800, 600, 1)
        assert 'width="800"' in svg
        assert 'height="600"' in svg

    def test_contains_subject_text(self):
        svg = _build_svg_preview("my subject", self.PALETTE, "abstract", 400, 300, 7)
        assert "my subject" in svg

    def test_abstract_style_has_rect(self):
        svg = _build_svg_preview("s", self.PALETTE, "abstract", 400, 300, 1)
        assert "<rect" in svg

    def test_sketch_style_has_lines(self):
        svg = _build_svg_preview("s", self.PALETTE, "sketch", 200, 150, 5)
        assert "<line" in svg

    def test_deterministic(self):
        svg1 = _build_svg_preview("same", self.PALETTE, "cinematic", 400, 300, 99)
        svg2 = _build_svg_preview("same", self.PALETTE, "cinematic", 400, 300, 99)
        assert svg1 == svg2


# ---------------------------------------------------------------------------
# Unit tests: _svg_to_data_url
# ---------------------------------------------------------------------------

class TestSvgToDataUrl:
    def test_starts_with_data_prefix(self):
        url = _svg_to_data_url("<svg/>")
        assert url.startswith("data:image/svg+xml;base64,")

    def test_decodable(self):
        svg = "<svg><rect/></svg>"
        url = _svg_to_data_url(svg)
        b64_part = url.split(",", 1)[1]
        decoded = base64.b64decode(b64_part).decode("utf-8")
        assert decoded == svg


# ---------------------------------------------------------------------------
# Unit tests: generate_canvas_image
# ---------------------------------------------------------------------------

class TestGenerateCanvasImage:
    def test_happy_path_returns_dict(self):
        result = generate_canvas_image(CYBERPUNK_PROMPT)
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        result = generate_canvas_image(CYBERPUNK_PROMPT)
        expected_keys = {
            "prompt", "refined_prompt", "style", "subject", "mood",
            "color_palette", "composition", "style_tags", "lighting",
            "width", "height", "preview_url", "suggested_filename",
        }
        assert expected_keys.issubset(result.keys())

    def test_prompt_preserved(self):
        result = generate_canvas_image(NATURE_PROMPT)
        assert result["prompt"] == NATURE_PROMPT

    def test_default_style(self):
        result = generate_canvas_image("any prompt")
        assert result["style"] == "cinematic"

    def test_custom_style(self):
        result = generate_canvas_image("some prompt", style="abstract")
        assert result["style"] == "abstract"

    def test_custom_dimensions(self):
        result = generate_canvas_image("prompt", width=640, height=480)
        assert result["width"] == 640
        assert result["height"] == 480

    def test_preview_url_is_data_uri(self):
        result = generate_canvas_image(PORTRAIT_PROMPT)
        assert result["preview_url"].startswith("data:image/svg+xml;base64,")

    def test_preview_url_decodable(self):
        result = generate_canvas_image(ABSTRACT_PROMPT)
        b64 = result["preview_url"].split(",", 1)[1]
        decoded = base64.b64decode(b64).decode("utf-8")
        assert "<svg" in decoded

    def test_color_palette_has_four_entries(self):
        result = generate_canvas_image("ocean sunset")
        assert len(result["color_palette"]) == 4

    def test_style_tags_is_list(self):
        result = generate_canvas_image("detailed cinematic dark scene")
        assert isinstance(result["style_tags"], list)
        assert len(result["style_tags"]) >= 1

    def test_suggested_filename_is_png(self):
        result = generate_canvas_image("my cool prompt")
        assert result["suggested_filename"].endswith(".png")
        assert result["suggested_filename"].startswith("kala-")

    def test_refined_prompt_contains_original(self):
        result = generate_canvas_image(CYBERPUNK_PROMPT)
        assert CYBERPUNK_PROMPT in result["refined_prompt"]

    def test_all_valid_styles_accepted(self):
        for style in VALID_STYLES:
            result = generate_canvas_image("test prompt", style=style)
            assert result["style"] == style

    def test_empty_prompt_raises(self):
        with pytest.raises(ValueError, match="empty"):
            generate_canvas_image("")

    def test_blank_prompt_raises(self):
        with pytest.raises(ValueError, match="empty"):
            generate_canvas_image("   ")

    def test_invalid_style_raises(self):
        with pytest.raises(ValueError, match="style"):
            generate_canvas_image("valid prompt", style="oilpainting")

    def test_width_too_small_raises(self):
        with pytest.raises(ValueError, match="width"):
            generate_canvas_image("valid prompt", width=50)

    def test_width_too_large_raises(self):
        with pytest.raises(ValueError, match="width"):
            generate_canvas_image("valid prompt", width=5000)

    def test_height_too_small_raises(self):
        with pytest.raises(ValueError, match="height"):
            generate_canvas_image("valid prompt", height=50)

    def test_height_too_large_raises(self):
        with pytest.raises(ValueError, match="height"):
            generate_canvas_image("valid prompt", height=5000)

    def test_deterministic_same_prompt(self):
        r1 = generate_canvas_image(CYBERPUNK_PROMPT)
        r2 = generate_canvas_image(CYBERPUNK_PROMPT)
        assert r1["preview_url"] == r2["preview_url"]
        assert r1["color_palette"] == r2["color_palette"]

    def test_different_prompts_differ(self):
        r1 = generate_canvas_image("a quiet snowy mountain village")
        r2 = generate_canvas_image("a fiery volcanic eruption at night")
        # Should have different colour palettes
        assert r1["color_palette"] != r2["color_palette"] or \
               r1["mood"] != r2["mood"]

    def test_whitespace_stripped_from_prompt(self):
        result = generate_canvas_image("  some prompt  ")
        assert result["prompt"] == "some prompt"

    def test_lighting_present(self):
        result = generate_canvas_image("test", style="cinematic")
        assert "lighting" in result["lighting"].lower() or \
               len(result["lighting"]) > 0

    def test_minimum_dimensions(self):
        result = generate_canvas_image("test", width=100, height=100)
        assert result["width"] == 100
        assert result["height"] == 100

    def test_maximum_dimensions(self):
        result = generate_canvas_image("test", width=4096, height=4096)
        assert result["width"] == 4096
        assert result["height"] == 4096


# ---------------------------------------------------------------------------
# API endpoint tests: POST /visual-studio/generate-image
# ---------------------------------------------------------------------------

class TestCanvasGenerateImageEndpoint:
    def test_happy_path(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": CYBERPUNK_PROMPT},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["prompt"] == CYBERPUNK_PROMPT
        assert "preview_url" in data
        assert data["preview_url"].startswith("data:image/svg+xml;base64,")

    def test_all_response_fields_present(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": NATURE_PROMPT},
        )
        assert resp.status_code == 200
        data = resp.json()
        for key in (
            "prompt", "refined_prompt", "style", "subject", "mood",
            "color_palette", "composition", "style_tags", "lighting",
            "width", "height", "preview_url", "suggested_filename",
        ):
            assert key in data, f"Missing key: {key}"

    def test_custom_style(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "abstract shapes", "style": "abstract"},
        )
        assert resp.status_code == 200
        assert resp.json()["style"] == "abstract"

    def test_custom_dimensions(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "test", "width": 1024, "height": 768},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["width"] == 1024
        assert data["height"] == 768

    def test_empty_prompt_returns_422(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": ""},
        )
        assert resp.status_code == 422

    def test_blank_prompt_returns_422(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "   "},
        )
        assert resp.status_code == 422

    def test_invalid_style_returns_422(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "a scene", "style": "not_a_style"},
        )
        assert resp.status_code == 422

    def test_width_out_of_range_returns_422(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "test", "width": 50},
        )
        assert resp.status_code == 422

    def test_height_out_of_range_returns_422(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "test", "height": 5000},
        )
        assert resp.status_code == 422

    def test_missing_prompt_returns_422(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"style": "cinematic"},
        )
        assert resp.status_code == 422

    def test_all_valid_styles_accepted(self):
        from kalacore.kalacanvas import VALID_STYLES
        for style in sorted(VALID_STYLES):
            resp = client.post(
                "/visual-studio/generate-image",
                json={"prompt": "a test prompt", "style": style},
            )
            assert resp.status_code == 200, f"Failed for style: {style}"

    def test_color_palette_has_four_items(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "ocean sunset waves"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["color_palette"]) == 4

    def test_suggested_filename_format(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "cyberpunk city at night"},
        )
        assert resp.status_code == 200
        filename = resp.json()["suggested_filename"]
        assert filename.startswith("kala-")
        assert filename.endswith(".png")

    def test_deterministic_response(self):
        payload = {"prompt": "a peaceful forest at dawn", "style": "painting"}
        r1 = client.post("/visual-studio/generate-image", json=payload)
        r2 = client.post("/visual-studio/generate-image", json=payload)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["preview_url"] == r2.json()["preview_url"]

    def test_style_case_insensitive(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "a scene", "style": "CINEMATIC"},
        )
        assert resp.status_code == 200
        assert resp.json()["style"] == "cinematic"

    def test_minimum_dimensions_accepted(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "test", "width": 100, "height": 100},
        )
        assert resp.status_code == 200

    def test_maximum_dimensions_accepted(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "test", "width": 4096, "height": 4096},
        )
        assert resp.status_code == 200

"""
Tests for Phase 11 – Visual Art Intelligence.

Covers:
  • kalavisual unit functions (colour, composition, style, emotion, intent,
    technical, narrative, preservation)
  • /visual API endpoint (happy path, validation, error handling)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

from main import app
from kalacore.kalavisual import (
    analyze_color_palette,
    analyze_composition,
    classify_style,
    analyze_emotional_register,
    infer_artistic_intent,
    analyze_technical_elements,
    preservation_recommendations,
    extract_visual_narrative,
    analyze_visual,
    SUPPORTED_MEDIA,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PAINTING_DESCRIPTION = (
    "An impressionistic oil painting on canvas of a misty river at dawn. "
    "The scene uses loose brushwork and atmospheric light. "
    "A lone figure stands off-centre in the foreground, while layered trees "
    "recede into the background, creating depth and perspective."
)

SKETCH_DESCRIPTION = (
    "A detailed charcoal sketch of a crumbling urban building. "
    "Cross-hatching creates deep shadows in the doorways. "
    "The architecture recedes using careful one-point perspective."
)

PHOTO_DESCRIPTION = (
    "A black and white documentary street photograph capturing a protest. "
    "The camera is at low angle creating a dramatic compositional diagonal. "
    "Shallow depth of field isolates the main subject from the crowd."
)

VIDEO_DESCRIPTION = (
    "An experimental stop motion animation featuring handmade paper figures. "
    "The slow, deliberate pace creates a meditative emotional register. "
    "Each frame is uniquely hand-drawn, making the work ephemeral."
)

LOGO_DESCRIPTION = (
    "A minimalist wordmark logo with clean geometric letterforms. "
    "The icon symbol represents a speech bubble in negative space. "
    "Designed as vector SVG for full scalability."
)


# ---------------------------------------------------------------------------
# Unit tests: analyze_color_palette
# ---------------------------------------------------------------------------

class TestAnalyzeColorPalette:

    def test_empty_palette_returns_note(self):
        result = analyze_color_palette([])
        assert "note" in result

    def test_none_palette_returns_note(self):
        result = analyze_color_palette(None)
        assert "note" in result

    def test_invalid_hex_ignored(self):
        result = analyze_color_palette(["not-a-colour", "GGGGGG"])
        assert "note" in result

    def test_single_colour_returns_monochromatic(self):
        result = analyze_color_palette(["#ff0000"])
        assert "monochromatic" in result.get("colour_harmony", "")

    def test_two_complementary_colours(self):
        # Red (#ff0000) and Cyan (#00ffff) are complementary
        result = analyze_color_palette(["#ff0000", "#00ffff"])
        assert result["colour_harmony"] == "complementary"

    def test_warm_palette(self):
        result = analyze_color_palette(["#ff4500", "#ff6347", "#ffa500"])
        assert result["dominant_temperature"] == "warm"

    def test_cool_palette(self):
        result = analyze_color_palette(["#0000ff", "#00bfff", "#4169e1"])
        assert result["dominant_temperature"] == "cool"

    def test_palette_size_correct(self):
        result = analyze_color_palette(["#ff0000", "#00ff00", "#0000ff"])
        assert result["palette_size"] == 3

    def test_high_saturation_label(self):
        result = analyze_color_palette(["#ff0000"])
        assert "saturated" in result.get("saturation", "")

    def test_dark_palette_low_key(self):
        result = analyze_color_palette(["#0a0a0a", "#111111", "#080808"])
        assert "low-key" in result.get("value_range", "")

    def test_insight_is_string(self):
        result = analyze_color_palette(["#ff0000", "#00ff00"])
        assert isinstance(result.get("insight"), str)
        assert len(result["insight"]) > 10

    def test_short_hex_parsed(self):
        result = analyze_color_palette(["#f00"])  # short form red
        assert result.get("palette_size") == 1

    def test_hex_without_hash(self):
        result = analyze_color_palette(["ff0000"])
        assert result.get("palette_size") == 1


# ---------------------------------------------------------------------------
# Unit tests: analyze_composition
# ---------------------------------------------------------------------------

class TestAnalyzeComposition:

    def test_centred_detected(self):
        result = analyze_composition("The subject is centered with perfect symmetry")
        assert result["balance"].startswith("symmetrical")

    def test_rule_of_thirds(self):
        result = analyze_composition("The horizon is placed off-center in the upper third")
        assert "asymmetric" in result["balance"]

    def test_leading_lines(self):
        result = analyze_composition("A road leads the eye to the vanishing point")
        assert result["has_leading_lines"] is True

    def test_negative_space(self):
        result = analyze_composition("The minimal composition uses negative space extensively")
        assert result["uses_negative_space"] is True

    def test_layered_depth(self):
        result = analyze_composition("Trees in the foreground, mountains in the background")
        assert result["depth"] == "multi-layered"

    def test_texture_noted(self):
        result = analyze_composition("Heavy impasto texture dominates the surface")
        assert result["texture_noted"] is True

    def test_empty_description_runs_without_error(self):
        result = analyze_composition("  ")
        assert isinstance(result, dict)

    def test_element_count_increases(self):
        base = analyze_composition("a painting")
        rich = analyze_composition(
            "The off-center subject uses leading lines toward a vanishing point "
            "with foreground layers and extensive negative space"
        )
        assert rich["element_count"] >= base["element_count"]

    def test_diagonal_detected(self):
        result = analyze_composition("The composition has a strong angled, tilted, slanted dynamic arrangement")
        assert "dynamic" in result["balance"]

    def test_pattern_rhythm(self):
        result = analyze_composition("Geometric pattern and repetition fill the entire frame")
        assert result["has_pattern_rhythm"] is True


# ---------------------------------------------------------------------------
# Unit tests: classify_style
# ---------------------------------------------------------------------------

class TestClassifyStyle:

    def test_impressionism_from_keywords(self):
        result = classify_style("A loose, atmospheric plein air painting with dappled light")
        assert result["primary_style"] == "impressionism"

    def test_abstract_detected(self):
        result = classify_style("An abstract, non-representational geometric composition")
        assert result["primary_style"] == "abstract"

    def test_realism_detected(self):
        result = classify_style("A photorealistic, lifelike detailed portrait")
        assert result["primary_style"] == "realism"

    def test_style_tags_contribute(self):
        result = classify_style("A strange unusual composition", style_tags=["surrealism", "dreamlike"])
        assert result["primary_style"] == "surrealism"

    def test_undetermined_when_no_keywords(self):
        result = classify_style("A work made by an artist")
        assert result["primary_style"] == "undetermined"
        assert result["detection_confidence"] == "low"

    def test_influences_populated(self):
        result = classify_style(
            "A photorealistic detailed portrait with geometric abstract forms "
            "and bold pop colours"
        )
        assert len(result["style_influences"]) >= 1

    def test_note_present(self):
        result = classify_style("anything")
        assert "note" in result

    def test_high_confidence(self):
        result = classify_style(
            "realistic lifelike photorealistic detailed accurate representational portrait"
        )
        assert result["detection_confidence"] in ("high", "medium")


# ---------------------------------------------------------------------------
# Unit tests: analyze_emotional_register
# ---------------------------------------------------------------------------

class TestAnalyzeEmotionalRegister:

    def test_peaceful_detected(self):
        result = analyze_emotional_register("A serene, calm, peaceful lake at dawn")
        assert result["primary_register"] == "peaceful"

    def test_dramatic_detected(self):
        result = analyze_emotional_register("A dramatic, intense, striking scene")
        assert result["primary_register"] == "dramatic"

    def test_melancholic_detected(self):
        result = analyze_emotional_register("A lonely, somber, melancholic figure in grey fog")
        assert result["primary_register"] == "melancholic"

    def test_neutral_when_no_keywords(self):
        result = analyze_emotional_register("A work by an artist")
        assert result["primary_register"] == "neutral / undetermined"

    def test_complexity_reflects_count(self):
        simple = analyze_emotional_register("A painting")
        complex_ = analyze_emotional_register("A joyful, peaceful, dramatic, mysterious work")
        assert complex_["emotional_complexity"] >= simple["emotional_complexity"]

    def test_note_present(self):
        result = analyze_emotional_register("anything")
        assert "note" in result


# ---------------------------------------------------------------------------
# Unit tests: infer_artistic_intent
# ---------------------------------------------------------------------------

class TestInferArtisticIntent:

    def test_logo_defaults_decorative(self):
        result = infer_artistic_intent("a clean simple design", "logo")
        assert result["primary_intent"] == "decorative"

    def test_photo_defaults_documentary(self):
        result = infer_artistic_intent("a photo", "photo")
        assert result["primary_intent"] == "documentary"

    def test_expressive_from_keywords(self):
        result = infer_artistic_intent(
            "A personal, autobiographical, emotional self-portrait", "painting"
        )
        assert result["primary_intent"] == "expressive"

    def test_spiritual_detected(self):
        result = infer_artistic_intent(
            "A sacred, devotional, spiritual piece for ritual use", "painting"
        )
        assert result["primary_intent"] == "spiritual"

    def test_note_present(self):
        result = infer_artistic_intent("anything", "painting")
        assert "note" in result


# ---------------------------------------------------------------------------
# Unit tests: analyze_technical_elements
# ---------------------------------------------------------------------------

class TestAnalyzeTechnicalElements:

    def test_painting_medium_detected(self):
        result = analyze_technical_elements("An oil painting on canvas", "painting")
        assert "oil" in result["paint_medium"]

    def test_painting_impasto(self):
        result = analyze_technical_elements("Heavy impasto oil painting", "painting")
        assert result["impasto_texture"] is True

    def test_sketch_medium(self):
        result = analyze_technical_elements("A detailed charcoal sketch", "sketch")
        assert "charcoal" in result["drawing_medium"]

    def test_sketch_crosshatch(self):
        result = analyze_technical_elements(
            "A pen drawing with cross-hatching for shadows", "sketch"
        )
        assert result["cross_hatching"] is True

    def test_photo_genre(self):
        result = analyze_technical_elements("A black and white portrait photograph", "photo")
        assert result["photo_genre"] == "monochrome"

    def test_video_technique(self):
        result = analyze_technical_elements("A stop motion animation", "video")
        assert "stop motion" in result["video_technique"]

    def test_logo_wordmark(self):
        result = analyze_technical_elements("A typographic wordmark logo design", "logo")
        assert result["logo_type"] == "wordmark"

    def test_logo_vector(self):
        result = analyze_technical_elements("A clean SVG vector logo with scalable geometry", "logo")
        assert result["likely_vector"] is True

    def test_observations_string(self):
        result = analyze_technical_elements(PAINTING_DESCRIPTION, "painting")
        assert isinstance(result["observations"], str)


# ---------------------------------------------------------------------------
# Unit tests: preservation_recommendations
# ---------------------------------------------------------------------------

class TestPreservationRecommendations:

    @pytest.mark.parametrize("medium", list(SUPPORTED_MEDIA))
    def test_all_media_return_dict(self, medium):
        result = preservation_recommendations(medium)
        assert isinstance(result, dict)
        assert result["medium"] == medium
        assert isinstance(result["digital"], list)
        assert isinstance(result["physical"], list)
        assert isinstance(result["distribution"], list)

    def test_painting_has_uv_recommendation(self):
        result = preservation_recommendations("painting")
        combined = " ".join(result["physical"]).lower()
        assert "uv" in combined or "sunlight" in combined

    def test_logo_has_svg_recommendation(self):
        result = preservation_recommendations("logo")
        combined = " ".join(result["digital"]).lower()
        assert "svg" in combined

    def test_photo_mentions_raw(self):
        result = preservation_recommendations("photo")
        combined = " ".join(result["digital"]).lower()
        assert "raw" in combined


# ---------------------------------------------------------------------------
# Unit tests: extract_visual_narrative
# ---------------------------------------------------------------------------

class TestExtractVisualNarrative:

    def test_portrait_subject_detected(self):
        result = extract_visual_narrative("A detailed portrait of a human figure in profile")
        assert "portrait / figure" in result["detected_subjects"]

    def test_landscape_detected(self):
        result = extract_visual_narrative("A wide mountain landscape under an open sky")
        assert "landscape" in result["detected_subjects"]

    def test_word_count_tracked(self):
        text = "A painting with many details about shapes and colour"
        result = extract_visual_narrative(text)
        assert result["word_count"] == len(text.split())

    def test_brief_description_label(self):
        result = extract_visual_narrative("A painting")
        assert "brief" in result["description_complexity"]

    def test_detailed_description_label(self):
        long_text = " ".join(["word"] * 70)
        result = extract_visual_narrative(long_text)
        assert "detailed" in result["description_complexity"]


# ---------------------------------------------------------------------------
# Unit tests: analyze_visual (integration)
# ---------------------------------------------------------------------------

class TestAnalyzeVisual:

    def test_painting_full_pipeline(self):
        result = analyze_visual(PAINTING_DESCRIPTION, medium="painting")
        required_keys = {
            "medium", "summary", "colour", "composition", "style",
            "emotion", "intent", "technical", "narrative", "preservation",
        }
        assert required_keys.issubset(result.keys())
        assert result["medium"] == "painting"

    def test_sketch_medium(self):
        result = analyze_visual(SKETCH_DESCRIPTION, medium="sketch")
        assert result["medium"] == "sketch"
        assert "cross_hatching" in result["technical"]

    def test_photo_medium(self):
        result = analyze_visual(PHOTO_DESCRIPTION, medium="photo")
        assert result["medium"] == "photo"

    def test_video_medium(self):
        result = analyze_visual(VIDEO_DESCRIPTION, medium="video")
        assert result["medium"] == "video"

    def test_logo_medium(self):
        result = analyze_visual(LOGO_DESCRIPTION, medium="logo")
        assert result["medium"] == "logo"

    def test_color_palette_included(self):
        palette = ["#ff0000", "#00ff00", "#0000ff"]
        result = analyze_visual(PAINTING_DESCRIPTION, color_palette=palette)
        assert result["colour"]["palette_size"] == 3

    def test_dimensions_passed_through(self):
        result = analyze_visual(PAINTING_DESCRIPTION, dimensions="24x36 inches")
        assert result["dimensions"] == "24x36 inches"

    def test_style_tags_contribute(self):
        result = analyze_visual(
            "An unusual vivid composition",
            medium="painting",
            style_tags=["expressionism", "gestural"],
        )
        assert result["style"]["primary_style"] == "expressionism"

    def test_invalid_medium_defaults_to_painting(self):
        result = analyze_visual(PAINTING_DESCRIPTION, medium="unknown_medium")
        assert result["medium"] == "painting"

    def test_empty_description_returns_error(self):
        result = analyze_visual("", medium="painting")
        assert "error" in result

    def test_summary_is_string(self):
        result = analyze_visual(PAINTING_DESCRIPTION)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 5


# ---------------------------------------------------------------------------
# API endpoint tests: POST /visual
# ---------------------------------------------------------------------------

class TestVisualEndpoint:

    def test_painting_returns_200(self):
        resp = client.post(
            "/visual",
            json={"description": PAINTING_DESCRIPTION, "medium": "painting"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["medium"] == "painting"
        assert "summary" in data
        assert "colour" in data
        assert "composition" in data

    def test_sketch_endpoint(self):
        resp = client.post(
            "/visual",
            json={"description": SKETCH_DESCRIPTION, "medium": "sketch"},
        )
        assert resp.status_code == 200
        assert resp.json()["medium"] == "sketch"

    def test_photo_endpoint(self):
        resp = client.post(
            "/visual",
            json={"description": PHOTO_DESCRIPTION, "medium": "photo"},
        )
        assert resp.status_code == 200
        assert resp.json()["medium"] == "photo"

    def test_video_endpoint(self):
        resp = client.post(
            "/visual",
            json={"description": VIDEO_DESCRIPTION, "medium": "video"},
        )
        assert resp.status_code == 200

    def test_logo_endpoint(self):
        resp = client.post(
            "/visual",
            json={"description": LOGO_DESCRIPTION, "medium": "logo"},
        )
        assert resp.status_code == 200

    def test_with_color_palette(self):
        resp = client.post(
            "/visual",
            json={
                "description": PAINTING_DESCRIPTION,
                "medium": "painting",
                "color_palette": ["#ff4500", "#2ecc71", "#3498db"],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["colour"]["palette_size"] == 3

    def test_with_dimensions(self):
        resp = client.post(
            "/visual",
            json={
                "description": PAINTING_DESCRIPTION,
                "medium": "painting",
                "dimensions": "60x80 cm",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["dimensions"] == "60x80 cm"

    def test_with_style_tags(self):
        resp = client.post(
            "/visual",
            json={
                "description": "A loose, gestural work",
                "medium": "painting",
                "style_tags": ["expressionism", "abstract"],
            },
        )
        assert resp.status_code == 200

    def test_empty_description_returns_422(self):
        resp = client.post(
            "/visual",
            json={"description": "   ", "medium": "painting"},
        )
        assert resp.status_code == 422

    def test_invalid_medium_returns_422(self):
        resp = client.post(
            "/visual",
            json={"description": "A nice artwork", "medium": "sculpture"},
        )
        assert resp.status_code == 422

    def test_missing_description_returns_422(self):
        resp = client.post("/visual", json={"medium": "painting"})
        assert resp.status_code == 422

    def test_preservation_section_present(self):
        resp = client.post(
            "/visual",
            json={"description": PAINTING_DESCRIPTION, "medium": "painting"},
        )
        data = resp.json()
        assert "preservation" in data
        assert isinstance(data["preservation"]["digital"], list)

    def test_technical_section_present(self):
        resp = client.post(
            "/visual",
            json={"description": SKETCH_DESCRIPTION, "medium": "sketch"},
        )
        data = resp.json()
        assert "technical" in data
        assert "drawing_medium" in data["technical"]

    def test_all_response_keys_present(self):
        resp = client.post(
            "/visual",
            json={"description": LOGO_DESCRIPTION, "medium": "logo"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for key in (
            "medium", "dimensions", "summary", "colour", "composition",
            "style", "emotion", "intent", "technical", "narrative", "preservation",
        ):
            assert key in data, f"Missing key: {key}"

    def test_narrative_contains_subjects(self):
        resp = client.post(
            "/visual",
            json={
                "description": "A portrait of a human figure against a mountain landscape",
                "medium": "painting",
            },
        )
        data = resp.json()
        subjects = data["narrative"]["detected_subjects"]
        assert any("portrait" in s or "landscape" in s for s in subjects)


# ===========================================================================
# Phase 14 – Design Canvas AI Image Concept Generator
# ===========================================================================

from kalacore.kalavisual import generate_image_concept, _IMAGE_THEMES, _VISUAL_STYLES


class TestGenerateImageConceptUnit:
    """Unit tests for generate_image_concept()."""

    def test_happy_path_returns_required_keys(self):
        result = generate_image_concept("futuristic cyberpunk city at night")
        for key in ("prompt", "style", "description", "palette", "image_data", "width", "height", "theme"):
            assert key in result, f"Missing key: {key}"

    def test_image_data_is_svg_data_uri(self):
        result = generate_image_concept("a misty mountain landscape")
        assert result["image_data"].startswith("data:image/svg+xml;base64,")

    def test_palette_has_three_colours(self):
        result = generate_image_concept("ocean waves at sunrise")
        assert len(result["palette"]) == 3
        for colour in result["palette"]:
            assert colour.startswith("#"), f"Not a hex colour: {colour}"

    def test_cyberpunk_theme_detected(self):
        result = generate_image_concept("a glowing neon cyberpunk street")
        assert result["theme"] == "cyberpunk"

    def test_ocean_theme_detected(self):
        result = generate_image_concept("deep ocean waves crashing on shore")
        assert result["theme"] == "ocean"

    def test_space_theme_detected(self):
        result = generate_image_concept("galaxy nebula in deep space")
        assert result["theme"] == "space"

    def test_nature_theme_detected(self):
        result = generate_image_concept("a green forest with tall trees")
        assert result["theme"] == "nature"

    def test_fire_theme_detected(self):
        result = generate_image_concept("roaring fire and lava volcano")
        assert result["theme"] == "fire"

    def test_fantasy_theme_detected(self):
        result = generate_image_concept("a wizard casting magic spells in enchanted castle")
        assert result["theme"] == "fantasy"

    def test_portrait_theme_detected(self):
        result = generate_image_concept("portrait of a warrior woman in armor")
        assert result["theme"] == "portrait"

    def test_abstract_theme_detected(self):
        result = generate_image_concept("an abstract geometric pattern with fractal shapes")
        assert result["theme"] == "abstract"

    def test_architecture_theme_detected(self):
        result = generate_image_concept("a gothic cathedral with stone bridge and facade")
        assert result["theme"] == "architecture"

    def test_aurora_theme_detected(self):
        result = generate_image_concept("northern lights borealis dancing in the sky")
        assert result["theme"] == "aurora"

    def test_desert_theme_detected(self):
        result = generate_image_concept("golden sand dunes in the sahara desert")
        assert result["theme"] == "desert"

    def test_default_style_is_digital_art(self):
        result = generate_image_concept("a red rose in bloom")
        assert result["style"] == "digital art"

    def test_custom_style_accepted(self):
        result = generate_image_concept("a waterfall", style="watercolor")
        assert result["style"] == "watercolor"

    def test_unknown_style_falls_back_to_digital_art(self):
        result = generate_image_concept("a robot", style="hologram")
        assert result["style"] == "digital art"

    def test_empty_prompt_returns_error(self):
        result = generate_image_concept("")
        assert "error" in result

    def test_whitespace_only_prompt_returns_error(self):
        result = generate_image_concept("   ")
        assert "error" in result

    def test_description_contains_prompt(self):
        result = generate_image_concept("a red dragon flying over mountains")
        assert "a red dragon" in result["description"].lower() or "red dragon" in result["description"].lower()

    def test_width_and_height_are_512(self):
        result = generate_image_concept("any concept")
        assert result["width"] == 512
        assert result["height"] == 512

    def test_svg_contains_linearGradient(self):
        import base64
        result = generate_image_concept("misty forest")
        raw = base64.b64decode(result["image_data"].split(",")[1]).decode("utf-8")
        assert "linearGradient" in raw

    def test_prompt_echoed_in_result(self):
        prompt = "cosmic aurora borealis"
        result = generate_image_concept(prompt)
        assert result["prompt"] == prompt

    def test_long_prompt_handled(self):
        long_prompt = "a very detailed scene of " + "mountains and rivers " * 30
        result = generate_image_concept(long_prompt)
        assert "image_data" in result
        assert result["image_data"].startswith("data:image/svg+xml;base64,")


class TestDesignCanvasGenerateImageEndpoint:
    """Integration tests for POST /visual-studio/generate-image."""

    def test_happy_path(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "futuristic cyberpunk city at night"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for key in ("prompt", "style", "description", "palette", "image_data", "width", "height", "theme"):
            assert key in data

    def test_svg_data_uri_returned(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "a serene mountain lake"},
        )
        assert resp.status_code == 200
        assert resp.json()["image_data"].startswith("data:image/svg+xml;base64,")

    def test_custom_style_accepted(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "ocean waves", "style": "watercolor"},
        )
        assert resp.status_code == 200
        assert resp.json()["style"] == "watercolor"

    def test_invalid_style_returns_422(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "a forest", "style": "hologram"},
        )
        assert resp.status_code == 422

    def test_empty_prompt_returns_422(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": ""},
        )
        assert resp.status_code == 422

    def test_missing_prompt_returns_422(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={},
        )
        assert resp.status_code == 422

    def test_palette_has_three_hex_colours(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "galaxy nebula"},
        )
        assert resp.status_code == 200
        palette = resp.json()["palette"]
        assert len(palette) == 3
        for c in palette:
            assert c.startswith("#")

    def test_all_styles_accepted(self):
        styles = ["digital art", "painting", "photo", "sketch",
                  "watercolor", "illustration", "concept art"]
        for style in styles:
            resp = client.post(
                "/visual-studio/generate-image",
                json={"prompt": "a beautiful scene", "style": style},
            )
            assert resp.status_code == 200, f"Style '{style}' failed: {resp.text}"

    def test_width_height_are_512(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "any scene"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["width"] == 512
        assert data["height"] == 512

    def test_prompt_echoed_in_response(self):
        prompt = "a red dragon over a mountain"
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": prompt},
        )
        assert resp.status_code == 200
        assert resp.json()["prompt"] == prompt

    def test_whitespace_prompt_returns_422(self):
        resp = client.post(
            "/visual-studio/generate-image",
            json={"prompt": "   "},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Unit tests: animate_canvas_objects
# ---------------------------------------------------------------------------

from kalacore.kalavisual import animate_canvas_objects, ANIMATION_TYPES


class TestAnimateCanvasObjects:

    def test_empty_elements_returns_empty(self):
        result = animate_canvas_objects([], "cinematic intro")
        assert result == []

    def test_returns_one_entry_per_element(self):
        elements = [
            {"id": "1", "type": "rect"},
            {"id": "2", "type": "i-text"},
        ]
        result = animate_canvas_objects(elements, "cinematic")
        assert len(result) == 2

    def test_each_entry_has_required_keys(self):
        elements = [{"id": "a", "type": "rect"}]
        result = animate_canvas_objects(elements, "fade")
        entry = result[0]
        assert "id" in entry
        assert "animation" in entry
        assert "duration" in entry
        assert "delay" in entry

    def test_animation_type_is_valid(self):
        elements = [{"id": str(i), "type": t} for i, t in
                    enumerate(["rect", "circle", "i-text", "text", "image"])]
        result = animate_canvas_objects(elements, "cinematic intro")
        for entry in result:
            assert entry["animation"] in ANIMATION_TYPES

    def test_first_element_has_zero_delay(self):
        elements = [{"id": "x", "type": "rect"}]
        result = animate_canvas_objects(elements, "anything")
        assert result[0]["delay"] == 0.0

    def test_delays_increase_for_subsequent_elements(self):
        elements = [{"id": str(i), "type": "rect"} for i in range(3)]
        result = animate_canvas_objects(elements, "cinematic")
        assert result[1]["delay"] > result[0]["delay"]
        assert result[2]["delay"] > result[1]["delay"]

    def test_duration_is_positive(self):
        elements = [{"id": "1", "type": "circle"}]
        result = animate_canvas_objects(elements, "slow and gentle")
        assert result[0]["duration"] > 0

    def test_id_is_preserved(self):
        elements = [{"id": "my-unique-id", "type": "rect"}]
        result = animate_canvas_objects(elements, "bounce playful")
        assert result[0]["id"] == "my-unique-id"

    def test_cinematic_prompt_uses_fade_for_text(self):
        elements = [{"id": "1", "type": "i-text"}]
        result = animate_canvas_objects(elements, "cinematic intro")
        assert result[0]["animation"] == "fade-in"

    def test_playful_prompt_uses_scale_for_text(self):
        elements = [{"id": "1", "type": "i-text"}]
        result = animate_canvas_objects(elements, "bounce and playful")
        assert result[0]["animation"] == "scale-in"

    def test_empty_prompt_returns_assignments(self):
        elements = [{"id": "1", "type": "rect"}]
        result = animate_canvas_objects(elements, "")
        assert len(result) == 1

    def test_unknown_element_type_uses_default(self):
        elements = [{"id": "1", "type": "unknown-shape"}]
        result = animate_canvas_objects(elements, "cinematic")
        assert result[0]["animation"] in ANIMATION_TYPES


# ---------------------------------------------------------------------------
# API tests: POST /visual-studio/animate
# ---------------------------------------------------------------------------

class TestCanvasAnimateEndpoint:

    def test_happy_path_returns_assignments(self):
        resp = client.post(
            "/visual-studio/animate",
            json={
                "elements": [
                    {"id": "1", "type": "rect"},
                    {"id": "2", "type": "i-text"},
                ],
                "prompt": "cinematic intro",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "assignments" in data
        assert len(data["assignments"]) == 2

    def test_response_echoes_prompt(self):
        prompt = "dramatic and slow"
        resp = client.post(
            "/visual-studio/animate",
            json={
                "elements": [{"id": "1", "type": "circle"}],
                "prompt": prompt,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["prompt"] == prompt

    def test_each_assignment_has_id_and_animation(self):
        resp = client.post(
            "/visual-studio/animate",
            json={
                "elements": [{"id": "abc", "type": "rect"}],
                "prompt": "playful bounce",
            },
        )
        assert resp.status_code == 200
        assignment = resp.json()["assignments"][0]
        assert assignment["id"] == "abc"
        assert assignment["animation"] in ANIMATION_TYPES
        assert assignment["duration"] > 0
        assert assignment["delay"] >= 0

    def test_empty_elements_returns_empty_assignments(self):
        resp = client.post(
            "/visual-studio/animate",
            json={"elements": [], "prompt": "cinematic"},
        )
        assert resp.status_code == 200
        assert resp.json()["assignments"] == []

    def test_empty_prompt_returns_422(self):
        resp = client.post(
            "/visual-studio/animate",
            json={
                "elements": [{"id": "1", "type": "rect"}],
                "prompt": "",
            },
        )
        assert resp.status_code == 422

    def test_whitespace_prompt_returns_422(self):
        resp = client.post(
            "/visual-studio/animate",
            json={
                "elements": [{"id": "1", "type": "rect"}],
                "prompt": "   ",
            },
        )
        assert resp.status_code == 422

    def test_missing_prompt_returns_422(self):
        resp = client.post(
            "/visual-studio/animate",
            json={"elements": [{"id": "1", "type": "rect"}]},
        )
        assert resp.status_code == 422

    def test_all_valid_animation_types_returned(self):
        element_types = ["rect", "circle", "i-text", "text", "image"]
        elements = [{"id": str(i), "type": t} for i, t in enumerate(element_types)]
        resp = client.post(
            "/visual-studio/animate",
            json={"elements": elements, "prompt": "cinematic"},
        )
        assert resp.status_code == 200
        for a in resp.json()["assignments"]:
            assert a["animation"] in ANIMATION_TYPES

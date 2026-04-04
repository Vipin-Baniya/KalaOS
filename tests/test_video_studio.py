"""
Tests for the Video Studio module and endpoint:

  Unit tests:
    - generate_video_script() – happy paths, validation errors, scene structure
    - build_scene()           – valid/invalid inputs
    - apply_video_effect()    – effects, intensity validation
    - apply_ai_video_tool()   – all tools, validation

  API tests:
    POST /video-studio/generate-script
    POST /video-studio/apply-effect
    POST /video-studio/ai-tool
"""

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit imports
# ---------------------------------------------------------------------------
from kalacore.kalavideo import (
    generate_video_script,
    build_scene,
    apply_video_effect,
    apply_ai_video_tool,
    _VALID_STYLES,
    _VALID_ANIMATIONS,
    _DEFAULT_SCENE_DURATION,
    _VALID_EFFECTS,
    _VALID_AI_TOOLS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


# ════════════════════════════════════════════════════════════════════════════
# Unit tests: build_scene
# ════════════════════════════════════════════════════════════════════════════

class TestBuildScene:
    def test_basic_scene(self):
        s = build_scene(1, "Dream big and never stop.")
        assert s["index"] == 1
        assert s["text"] == "Dream big and never stop."
        assert s["animation"] in _VALID_ANIMATIONS
        assert s["duration"] == _DEFAULT_SCENE_DURATION
        assert s["voice_text"] == "Dream big and never stop."

    def test_voice_text_defaults_to_text(self):
        s = build_scene(2, "Hello world")
        assert s["voice_text"] == "Hello world"

    def test_voice_text_override(self):
        s = build_scene(1, "Short caption", voice_text="Longer narration text here.")
        assert s["voice_text"] == "Longer narration text here."

    def test_animation_defaults_to_fade_when_invalid(self):
        s = build_scene(1, "Test", animation="INVALID")
        assert s["animation"] == "fade"

    def test_all_valid_animations(self):
        for anim in _VALID_ANIMATIONS:
            s = build_scene(1, "Text", animation=anim)
            assert s["animation"] == anim

    def test_duration_clamped_min(self):
        s = build_scene(1, "Text", duration=0)
        assert s["duration"] >= 1

    def test_duration_clamped_max(self):
        s = build_scene(1, "Text", duration=999)
        assert s["duration"] <= 30

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="text must not be empty"):
            build_scene(1, "")

    def test_whitespace_text_raises(self):
        with pytest.raises(ValueError, match="text must not be empty"):
            build_scene(1, "   ")

    def test_invalid_index_raises(self):
        with pytest.raises(ValueError, match="index must be a positive integer"):
            build_scene(0, "Text")

    def test_negative_index_raises(self):
        with pytest.raises(ValueError, match="index must be a positive integer"):
            build_scene(-1, "Text")

    def test_image_concept_stored(self):
        s = build_scene(1, "Caption", image_concept="Sunset over mountains")
        assert s["image_concept"] == "Sunset over mountains"

    def test_bg_music_stored(self):
        s = build_scene(1, "Caption", bg_music="Epic orchestral")
        assert s["bg_music"] == "Epic orchestral"

    def test_scene_keys_present(self):
        s = build_scene(1, "Text")
        expected_keys = {"index", "text", "image_concept", "animation", "duration", "voice_text", "bg_music"}
        assert expected_keys.issubset(s.keys())


# ════════════════════════════════════════════════════════════════════════════
# Unit tests: generate_video_script
# ════════════════════════════════════════════════════════════════════════════

class TestGenerateVideoScript:
    def test_basic_prompt(self):
        result = generate_video_script("Rise and shine. Every day is a new beginning.")
        assert "scenes" in result
        assert len(result["scenes"]) >= 1

    def test_result_keys(self):
        result = generate_video_script("A hero's journey begins with a single step.")
        expected_keys = {"prompt", "style", "scenes", "total_duration", "bg_music_hint", "creative_score"}
        assert expected_keys.issubset(result.keys())

    def test_scene_count_respected(self):
        result = generate_video_script(
            "Line one. Line two. Line three. Line four. Line five. Line six. Line seven.",
            scene_count=3,
        )
        assert len(result["scenes"]) == 3

    def test_scene_count_single(self):
        result = generate_video_script("Just one scene here.", scene_count=1)
        assert len(result["scenes"]) == 1

    def test_all_valid_styles(self):
        for style in _VALID_STYLES:
            result = generate_video_script("Test prompt for style.", style=style)
            assert result["style"] == style
            assert len(result["scenes"]) >= 1

    def test_default_style_cinematic(self):
        result = generate_video_script("A cinematic journey begins.")
        assert result["style"] == "cinematic"

    def test_empty_prompt_raises(self):
        with pytest.raises(ValueError, match="prompt must not be empty"):
            generate_video_script("")

    def test_whitespace_prompt_raises(self):
        with pytest.raises(ValueError, match="prompt must not be empty"):
            generate_video_script("   ")

    def test_invalid_style_raises(self):
        with pytest.raises(ValueError, match="Invalid style"):
            generate_video_script("Valid prompt", style="invalid_style")

    def test_total_duration_matches_sum(self):
        result = generate_video_script("Scene text here.", scene_count=3)
        total = sum(s["duration"] for s in result["scenes"])
        assert result["total_duration"] == total

    def test_scenes_have_required_keys(self):
        result = generate_video_script("Dream. Create. Inspire.")
        for scene in result["scenes"]:
            assert "index" in scene
            assert "text" in scene
            assert "image_concept" in scene
            assert "animation" in scene
            assert "duration" in scene
            assert "voice_text" in scene
            assert "bg_music" in scene

    def test_scene_indices_are_sequential(self):
        result = generate_video_script("A. B. C. D. E.", scene_count=5)
        indices = [s["index"] for s in result["scenes"]]
        assert indices == list(range(1, len(result["scenes"]) + 1))

    def test_scene_animations_are_valid(self):
        result = generate_video_script("Motion and light fill the scene.", scene_count=4)
        for scene in result["scenes"]:
            assert scene["animation"] in _VALID_ANIMATIONS

    def test_creative_score_range(self):
        result = generate_video_script("A creative prompt with several descriptive words that paint a vivid picture.")
        assert 0 <= result["creative_score"] <= 1.0

    def test_bg_music_hint_present(self):
        result = generate_video_script("Motivational poem.", style="motivational")
        assert result["bg_music_hint"]

    def test_scene_count_max_clamped(self):
        result = generate_video_script("Short.", scene_count=100)
        assert len(result["scenes"]) <= 20

    def test_scene_count_min_clamped(self):
        result = generate_video_script("Short.", scene_count=0)
        assert len(result["scenes"]) >= 1

    def test_long_prompt_multiple_scenes(self):
        long_prompt = " ".join([f"Sentence number {i} is full of meaning." for i in range(10)])
        result = generate_video_script(long_prompt, scene_count=5)
        assert len(result["scenes"]) == 5

    def test_prompt_preserved_in_result(self):
        prompt = "Keep this text exactly."
        result = generate_video_script(prompt)
        assert result["prompt"] == prompt


# ════════════════════════════════════════════════════════════════════════════
# API tests: POST /video-studio/generate-script
# ════════════════════════════════════════════════════════════════════════════

class TestVideoGenerateScriptEndpoint:
    def test_happy_path(self, client):
        resp = client.post(
            "/video-studio/generate-script",
            json={"prompt": "Dream big, work hard, stay humble.", "style": "motivational", "scene_count": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "scenes" in data
        assert len(data["scenes"]) == 3

    def test_default_style(self, client):
        resp = client.post(
            "/video-studio/generate-script",
            json={"prompt": "A journey through the stars."},
        )
        assert resp.status_code == 200
        assert resp.json()["style"] == "cinematic"

    def test_all_styles_accepted(self, client):
        for style in _VALID_STYLES:
            resp = client.post(
                "/video-studio/generate-script",
                json={"prompt": "Testing style.", "style": style},
            )
            assert resp.status_code == 200, f"Style '{style}' failed: {resp.text}"

    def test_empty_prompt_returns_422(self, client):
        resp = client.post(
            "/video-studio/generate-script",
            json={"prompt": ""},
        )
        assert resp.status_code == 422

    def test_missing_prompt_returns_422(self, client):
        resp = client.post("/video-studio/generate-script", json={})
        assert resp.status_code == 422

    def test_invalid_style_returns_422(self, client):
        resp = client.post(
            "/video-studio/generate-script",
            json={"prompt": "Valid prompt", "style": "NOTAREAL"},
        )
        assert resp.status_code == 422

    def test_scene_count_boundaries(self, client):
        for count in [1, 5, 10, 20]:
            resp = client.post(
                "/video-studio/generate-script",
                json={"prompt": "One two three four five six seven eight nine ten.", "scene_count": count},
            )
            assert resp.status_code == 200
            assert len(resp.json()["scenes"]) == count

    def test_scene_count_out_of_range_returns_422(self, client):
        resp = client.post(
            "/video-studio/generate-script",
            json={"prompt": "Prompt", "scene_count": 0},
        )
        assert resp.status_code == 422

    def test_response_has_total_duration(self, client):
        resp = client.post(
            "/video-studio/generate-script",
            json={"prompt": "Short test.", "scene_count": 2},
        )
        assert resp.status_code == 200
        assert "total_duration" in resp.json()

    def test_response_has_creative_score(self, client):
        resp = client.post(
            "/video-studio/generate-script",
            json={"prompt": "Creative score test."},
        )
        assert resp.status_code == 200
        assert "creative_score" in resp.json()

    def test_scene_structure(self, client):
        resp = client.post(
            "/video-studio/generate-script",
            json={"prompt": "Rise. Shine. Conquer.", "scene_count": 3},
        )
        assert resp.status_code == 200
        scenes = resp.json()["scenes"]
        for scene in scenes:
            assert "index" in scene
            assert "text" in scene
            assert "image_concept" in scene
            assert "animation" in scene
            assert "duration" in scene
            assert "voice_text" in scene
            assert "bg_music" in scene

    def test_whitespace_prompt_returns_422(self, client):
        resp = client.post(
            "/video-studio/generate-script",
            json={"prompt": "   "},
        )
        assert resp.status_code == 422


# ════════════════════════════════════════════════════════════════════════════
# Unit tests: apply_video_effect
# ════════════════════════════════════════════════════════════════════════════

_SAMPLE_SCENES = [{"text": "Scene one"}, {"text": "Scene two"}]


class TestApplyVideoEffect:
    def test_all_valid_effects(self):
        for effect in _VALID_EFFECTS:
            result = apply_video_effect(_SAMPLE_SCENES, effect)
            assert result["effect"] == effect

    def test_scenes_processed_count(self):
        result = apply_video_effect(_SAMPLE_SCENES, "bw")
        assert result["scenes_processed"] == len(_SAMPLE_SCENES)

    def test_result_keys_present(self):
        result = apply_video_effect(_SAMPLE_SCENES, "cinematic")
        for key in ("effect", "intensity", "scenes_processed", "filter_css", "preview_url", "applied_at"):
            assert key in result

    def test_default_intensity(self):
        result = apply_video_effect(_SAMPLE_SCENES, "vintage")
        assert result["intensity"] == 1.0

    def test_custom_intensity(self):
        result = apply_video_effect(_SAMPLE_SCENES, "blur", intensity=0.5)
        assert result["intensity"] == 0.5

    def test_blur_filter_css_uses_intensity(self):
        result = apply_video_effect(_SAMPLE_SCENES, "blur", intensity=2.0)
        assert "blur(" in result["filter_css"]
        assert "px" in result["filter_css"]

    def test_bw_filter_css(self):
        result = apply_video_effect(_SAMPLE_SCENES, "bw")
        assert result["filter_css"] == "grayscale(1)"

    def test_cinematic_filter_css(self):
        result = apply_video_effect(_SAMPLE_SCENES, "cinematic")
        assert "contrast" in result["filter_css"]

    def test_preview_url_contains_effect(self):
        result = apply_video_effect(_SAMPLE_SCENES, "glitch")
        assert "glitch" in result["preview_url"]

    def test_applied_at_is_string(self):
        result = apply_video_effect(_SAMPLE_SCENES, "sharpen")
        assert isinstance(result["applied_at"], str)

    def test_invalid_effect_raises(self):
        with pytest.raises(ValueError, match="Invalid effect"):
            apply_video_effect(_SAMPLE_SCENES, "nonexistent")

    def test_intensity_too_high_raises(self):
        with pytest.raises(ValueError, match="intensity"):
            apply_video_effect(_SAMPLE_SCENES, "blur", intensity=5.0)

    def test_intensity_negative_raises(self):
        with pytest.raises(ValueError, match="intensity"):
            apply_video_effect(_SAMPLE_SCENES, "blur", intensity=-0.1)

    def test_intensity_boundary_zero(self):
        result = apply_video_effect(_SAMPLE_SCENES, "blur", intensity=0.0)
        assert result["intensity"] == 0.0

    def test_intensity_boundary_two(self):
        result = apply_video_effect(_SAMPLE_SCENES, "blur", intensity=2.0)
        assert result["intensity"] == 2.0

    def test_empty_scenes_returns_zero_processed(self):
        result = apply_video_effect([], "bw")
        assert result["scenes_processed"] == 0


# ════════════════════════════════════════════════════════════════════════════
# Unit tests: apply_ai_video_tool
# ════════════════════════════════════════════════════════════════════════════

class TestApplyAiVideoTool:
    def test_invalid_tool_raises(self):
        with pytest.raises(ValueError, match="Invalid tool"):
            apply_ai_video_tool(_SAMPLE_SCENES, "unknown_tool")

    def test_auto_caption_has_captions(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "auto_caption")
        assert "captions" in result
        assert isinstance(result["captions"], list)
        assert len(result["captions"]) == len(_SAMPLE_SCENES)

    def test_auto_caption_structure(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "auto_caption")
        for cap in result["captions"]:
            assert "scene" in cap
            assert "text" in cap
            assert "timestamp" in cap

    def test_auto_caption_scenes_processed(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "auto_caption")
        assert result["scenes_processed"] == len(_SAMPLE_SCENES)

    def test_stabilize_has_stabilization_strength(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "stabilize")
        assert "stabilization_strength" in result

    def test_stabilize_default_strength(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "stabilize")
        assert result["stabilization_strength"] == 0.8

    def test_stabilize_custom_strength(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "stabilize", options={"strength": 0.5})
        assert result["stabilization_strength"] == 0.5

    def test_stabilize_status(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "stabilize")
        assert result["status"] == "stabilized"

    def test_color_grade_has_adjustments(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "color_grade")
        assert "adjustments" in result

    def test_color_grade_default_preset(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "color_grade")
        assert result["grade_preset"] == "cinematic"

    def test_color_grade_custom_preset(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "color_grade", options={"preset": "warm"})
        assert result["grade_preset"] == "warm"

    def test_color_grade_lut_applied(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "color_grade")
        assert result["lut_applied"] is True

    def test_slow_mo_has_speed_factor(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "slow_mo")
        assert "speed_factor" in result

    def test_slow_mo_default_speed(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "slow_mo")
        assert result["speed_factor"] == 0.5

    def test_slow_mo_custom_speed(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "slow_mo", options={"speed": 0.25})
        assert result["speed_factor"] == 0.25

    def test_slow_mo_duration_multiplier(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "slow_mo", options={"speed": 0.5})
        assert result["duration_multiplier"] == pytest.approx(2.0)

    def test_slow_mo_fps_output(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "slow_mo")
        assert result["fps_output"] == 60

    def test_all_tools_return_scenes_processed(self):
        for tool in _VALID_AI_TOOLS:
            result = apply_ai_video_tool(_SAMPLE_SCENES, tool)
            assert result["scenes_processed"] == len(_SAMPLE_SCENES)

    def test_options_none_default(self):
        result = apply_ai_video_tool(_SAMPLE_SCENES, "stabilize", options=None)
        assert result["stabilization_strength"] == 0.8


# ════════════════════════════════════════════════════════════════════════════
# API tests: POST /video-studio/apply-effect
# ════════════════════════════════════════════════════════════════════════════

_API_SCENES = [{"text": "Hello world"}, {"text": "Second scene"}]


class TestApplyEffectEndpoint:
    def test_all_effects_accepted(self, client):
        for effect in _VALID_EFFECTS:
            resp = client.post(
                "/video-studio/apply-effect",
                json={"scenes": _API_SCENES, "effect": effect},
            )
            assert resp.status_code == 200, f"Effect '{effect}' failed: {resp.text}"

    def test_result_structure(self, client):
        resp = client.post(
            "/video-studio/apply-effect",
            json={"scenes": _API_SCENES, "effect": "cinematic"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["effect"] == "cinematic"
        assert data["scenes_processed"] == len(_API_SCENES)
        assert "filter_css" in data

    def test_invalid_effect_returns_422(self, client):
        resp = client.post(
            "/video-studio/apply-effect",
            json={"scenes": _API_SCENES, "effect": "notreal"},
        )
        assert resp.status_code == 422

    def test_empty_scenes_returns_422(self, client):
        resp = client.post(
            "/video-studio/apply-effect",
            json={"scenes": [], "effect": "bw"},
        )
        assert resp.status_code == 422

    def test_intensity_out_of_range_returns_422(self, client):
        resp = client.post(
            "/video-studio/apply-effect",
            json={"scenes": _API_SCENES, "effect": "blur", "intensity": 5.0},
        )
        assert resp.status_code == 422

    def test_default_intensity(self, client):
        resp = client.post(
            "/video-studio/apply-effect",
            json={"scenes": _API_SCENES, "effect": "vintage"},
        )
        assert resp.status_code == 200
        assert resp.json()["intensity"] == 1.0

    def test_custom_intensity(self, client):
        resp = client.post(
            "/video-studio/apply-effect",
            json={"scenes": _API_SCENES, "effect": "blur", "intensity": 1.5},
        )
        assert resp.status_code == 200
        assert resp.json()["intensity"] == 1.5

    def test_blur_filter_css(self, client):
        resp = client.post(
            "/video-studio/apply-effect",
            json={"scenes": _API_SCENES, "effect": "blur", "intensity": 1.0},
        )
        assert resp.status_code == 200
        assert "blur(" in resp.json()["filter_css"]

    def test_missing_effect_returns_422(self, client):
        resp = client.post(
            "/video-studio/apply-effect",
            json={"scenes": _API_SCENES},
        )
        assert resp.status_code == 422

    def test_intensity_zero_accepted(self, client):
        resp = client.post(
            "/video-studio/apply-effect",
            json={"scenes": _API_SCENES, "effect": "blur", "intensity": 0.0},
        )
        assert resp.status_code == 200

    def test_intensity_two_accepted(self, client):
        resp = client.post(
            "/video-studio/apply-effect",
            json={"scenes": _API_SCENES, "effect": "glitch", "intensity": 2.0},
        )
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════════════════════
# API tests: POST /video-studio/ai-tool
# ════════════════════════════════════════════════════════════════════════════

class TestAiToolEndpoint:
    def test_all_tools_accepted(self, client):
        for tool in _VALID_AI_TOOLS:
            resp = client.post(
                "/video-studio/ai-tool",
                json={"scenes": _API_SCENES, "tool": tool},
            )
            assert resp.status_code == 200, f"Tool '{tool}' failed: {resp.text}"

    def test_invalid_tool_returns_422(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": _API_SCENES, "tool": "nonexistent"},
        )
        assert resp.status_code == 422

    def test_empty_scenes_returns_422(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": [], "tool": "stabilize"},
        )
        assert resp.status_code == 422

    def test_auto_caption_has_captions(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": _API_SCENES, "tool": "auto_caption"},
        )
        assert resp.status_code == 200
        assert "captions" in resp.json()
        assert isinstance(resp.json()["captions"], list)

    def test_stabilize_has_stabilization_strength(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": _API_SCENES, "tool": "stabilize"},
        )
        assert resp.status_code == 200
        assert "stabilization_strength" in resp.json()

    def test_color_grade_has_adjustments(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": _API_SCENES, "tool": "color_grade"},
        )
        assert resp.status_code == 200
        assert "adjustments" in resp.json()

    def test_slow_mo_has_speed_factor(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": _API_SCENES, "tool": "slow_mo"},
        )
        assert resp.status_code == 200
        assert "speed_factor" in resp.json()

    def test_auto_caption_count_matches_scenes(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": _API_SCENES, "tool": "auto_caption"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["captions"]) == len(_API_SCENES)

    def test_stabilize_with_options(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": _API_SCENES, "tool": "stabilize", "options": {"strength": 0.6}},
        )
        assert resp.status_code == 200
        assert resp.json()["stabilization_strength"] == 0.6

    def test_color_grade_with_preset(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": _API_SCENES, "tool": "color_grade", "options": {"preset": "warm"}},
        )
        assert resp.status_code == 200
        assert resp.json()["grade_preset"] == "warm"

    def test_slow_mo_duration_multiplier(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": _API_SCENES, "tool": "slow_mo", "options": {"speed": 0.5}},
        )
        assert resp.status_code == 200
        assert resp.json()["duration_multiplier"] == pytest.approx(2.0)

    def test_missing_tool_returns_422(self, client):
        resp = client.post(
            "/video-studio/ai-tool",
            json={"scenes": _API_SCENES},
        )
        assert resp.status_code == 422

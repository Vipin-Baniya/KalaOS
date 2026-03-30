"""
Tests for the Video Studio module and endpoint:

  Unit tests:
    - generate_video_script() – happy paths, validation errors, scene structure
    - build_scene()           – valid/invalid inputs

  API tests:
    POST /video-studio/generate-script
"""

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit imports
# ---------------------------------------------------------------------------
from kalacore.kalavideo import (
    generate_video_script,
    build_scene,
    _VALID_STYLES,
    _VALID_ANIMATIONS,
    _DEFAULT_SCENE_DURATION,
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

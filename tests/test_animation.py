"""
Tests for the Animation Generator module and endpoint:

  Unit tests:
    - generate_animation_plan() – happy paths, validation errors
    - parse_storyboard()        – scene splitting

  API tests:
    POST /animation/generate
"""

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit imports
# ---------------------------------------------------------------------------
from kalacore.kalaanimation import generate_animation_plan, parse_storyboard


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


# ════════════════════════════════════════════════════════════════════════════
# Unit tests: parse_storyboard
# ════════════════════════════════════════════════════════════════════════════

class TestParseStoryboard:
    def test_single_paragraph(self):
        text = "A lone wolf stands on a hill at dusk. The wind carries a distant howl."
        scenes = parse_storyboard(text)
        assert len(scenes) == 1
        assert scenes[0]["index"] == 1
        assert "wolf" in scenes[0]["text"].lower()

    def test_multiple_scenes_with_dashes(self):
        text = (
            "The city sleeps beneath a blanket of stars.\n"
            "---\n"
            "A young artist opens her studio window.\n"
            "---\n"
            "Paint and light fill the canvas with life."
        )
        scenes = parse_storyboard(text)
        assert len(scenes) == 3
        for i, s in enumerate(scenes, start=1):
            assert s["index"] == i

    def test_scene_has_summary(self):
        text = "The rain falls softly on the cobblestones. Petals drift past the lamp-post."
        scenes = parse_storyboard(text)
        assert "summary" in scenes[0]
        assert len(scenes[0]["summary"]) > 0

    def test_empty_prompt_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            parse_storyboard("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            parse_storyboard("   \n  ")

    def test_scene_splitter_ignores_blank_chunks(self):
        text = (
            "---\n"
            "Scene one begins here.\n"
            "---\n"
            "   \n"
            "---\n"
            "Scene three has content."
        )
        scenes = parse_storyboard(text)
        # Blank chunks must be skipped
        assert all(s["text"].strip() for s in scenes)

    def test_long_story(self):
        parts = [f"Chapter {i}: The journey continues and the hero faces new trials." for i in range(1, 12)]
        text = "\n---\n".join(parts)
        scenes = parse_storyboard(text)
        assert len(scenes) == 11


# ════════════════════════════════════════════════════════════════════════════
# Unit tests: generate_animation_plan
# ════════════════════════════════════════════════════════════════════════════

class TestGenerateAnimationPlan:
    def test_text_to_animation_returns_plan(self):
        plan = generate_animation_plan(
            "A sunrise over a misty mountain range",
            mode="text_to_animation",
            style="cinematic",
            duration_sec=10,
        )
        assert plan["mode"] == "text_to_animation"
        assert plan["style"] == "cinematic"
        assert plan["duration_sec"] == 10
        assert isinstance(plan["scenes"], list)
        assert len(plan["scenes"]) >= 1
        assert isinstance(plan["keyframes"], list)
        assert len(plan["keyframes"]) >= 1

    def test_image_to_animation_mode(self):
        plan = generate_animation_plan(
            "A photograph of a child chasing butterflies in a meadow",
            mode="image_to_animation",
            style="cartoon",
            duration_sec=8,
        )
        assert plan["mode"] == "image_to_animation"
        assert plan["style"] == "cartoon"

    def test_story_to_storyboard_mode(self):
        story = (
            "The dragon flew over the frozen lake.\n---\n"
            "The knight raised her shield, eyes blazing.\n---\n"
            "In the silence that followed, snowflakes fell like ash."
        )
        plan = generate_animation_plan(story, mode="story_to_storyboard")
        assert plan["mode"] == "story_to_storyboard"
        assert len(plan["scenes"]) == 3
        assert len(plan["keyframes"]) == 3

    def test_all_valid_styles(self):
        styles = ["realistic", "cartoon", "anime", "cinematic", "abstract", "lofi"]
        for style in styles:
            plan = generate_animation_plan("A simple animation prompt", style=style)
            assert plan["style"] == style

    def test_keyframe_fields(self):
        plan = generate_animation_plan("A leaf falls from a tree", duration_sec=6)
        kf = plan["keyframes"][0]
        assert "scene_index" in kf
        assert "start_time_sec" in kf
        assert "duration_sec" in kf
        assert "description" in kf
        assert "camera_move" in kf
        assert "transition" in kf
        assert "style_note" in kf

    def test_audio_hint_present(self):
        plan = generate_animation_plan("A music video concept", style="lofi")
        assert "audio_hint" in plan
        assert "lo-fi" in plan["audio_hint"].lower()

    def test_export_formats_present(self):
        plan = generate_animation_plan("Test prompt")
        assert "export_formats" in plan
        assert "mp4" in plan["export_formats"]

    def test_creative_score_range(self):
        plan = generate_animation_plan("A brief idea")
        score = plan["creative_score"]
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_character_notes_extracted(self):
        plan = generate_animation_plan(
            "Alice runs through the forest while Bob watches from the cliff."
        )
        names = [n["name"] for n in plan["character_notes"]]
        assert "Alice" in names
        assert "Bob" in names

    def test_duration_clamped_min(self):
        plan = generate_animation_plan("Short clip", duration_sec=0)
        assert plan["duration_sec"] >= 2

    def test_duration_clamped_max(self):
        plan = generate_animation_plan("Epic saga", duration_sec=9999)
        assert plan["duration_sec"] <= 300

    def test_empty_prompt_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            generate_animation_plan("")

    def test_whitespace_prompt_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            generate_animation_plan("   ")

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="Invalid mode"):
            generate_animation_plan("A prompt", mode="flying_mode")

    def test_invalid_style_raises(self):
        with pytest.raises(ValueError, match="Invalid style"):
            generate_animation_plan("A prompt", style="watercolour")

    def test_default_mode_is_text_to_animation(self):
        plan = generate_animation_plan("Default mode test")
        assert plan["mode"] == "text_to_animation"

    def test_default_style_is_cinematic(self):
        plan = generate_animation_plan("Default style test")
        assert plan["style"] == "cinematic"

    def test_default_duration_is_10(self):
        plan = generate_animation_plan("Default duration test")
        assert plan["duration_sec"] == 10

    def test_long_story_many_scenes(self):
        chapters = "\n---\n".join(
            f"Chapter {i}: The hero faces challenge number {i}." for i in range(1, 9)
        )
        plan = generate_animation_plan(chapters, mode="story_to_storyboard", duration_sec=60)
        assert len(plan["scenes"]) == 8
        assert len(plan["keyframes"]) == 8


# ════════════════════════════════════════════════════════════════════════════
# API tests: POST /animation/generate
# ════════════════════════════════════════════════════════════════════════════

class TestAnimationGenerateEndpoint:
    def test_happy_path_text(self, client):
        resp = client.post(
            "/animation/generate",
            json={
                "prompt": "A comet streaks across the night sky",
                "mode": "text_to_animation",
                "style": "cinematic",
                "duration_sec": 12,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "text_to_animation"
        assert data["style"] == "cinematic"
        assert data["duration_sec"] == 12
        assert len(data["scenes"]) >= 1
        assert len(data["keyframes"]) >= 1
        assert "audio_hint" in data
        assert "creative_score" in data

    def test_happy_path_image(self, client):
        resp = client.post(
            "/animation/generate",
            json={
                "prompt": "A vintage photograph of Paris in 1920",
                "mode": "image_to_animation",
                "style": "realistic",
                "duration_sec": 8,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["mode"] == "image_to_animation"

    def test_happy_path_storyboard(self, client):
        story = (
            "The sun rises over the sea.\n---\n"
            "Fishermen pull their nets in.\n---\n"
            "The village wakes to the smell of bread."
        )
        resp = client.post(
            "/animation/generate",
            json={"prompt": story, "mode": "story_to_storyboard"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["scenes"]) == 3

    def test_all_styles_accepted(self, client):
        for style in ["realistic", "cartoon", "anime", "cinematic", "abstract", "lofi"]:
            resp = client.post(
                "/animation/generate",
                json={"prompt": "Test style", "style": style},
            )
            assert resp.status_code == 200, f"Failed for style={style}"

    def test_missing_prompt_422(self, client):
        resp = client.post("/animation/generate", json={"mode": "text_to_animation"})
        assert resp.status_code == 422

    def test_empty_prompt_422(self, client):
        resp = client.post(
            "/animation/generate",
            json={"prompt": "", "mode": "text_to_animation"},
        )
        assert resp.status_code == 422

    def test_invalid_mode_422(self, client):
        resp = client.post(
            "/animation/generate",
            json={"prompt": "A scene", "mode": "invalid_mode"},
        )
        assert resp.status_code == 422

    def test_invalid_style_422(self, client):
        resp = client.post(
            "/animation/generate",
            json={"prompt": "A scene", "style": "watercolour"},
        )
        assert resp.status_code == 422

    def test_duration_too_short_422(self, client):
        resp = client.post(
            "/animation/generate",
            json={"prompt": "A scene", "duration_sec": 1},
        )
        assert resp.status_code == 422

    def test_duration_too_long_422(self, client):
        resp = client.post(
            "/animation/generate",
            json={"prompt": "A scene", "duration_sec": 301},
        )
        assert resp.status_code == 422

    def test_defaults_applied(self, client):
        resp = client.post(
            "/animation/generate",
            json={"prompt": "A scene with default settings"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "text_to_animation"
        assert data["style"] == "cinematic"
        assert data["duration_sec"] == 10

    def test_response_has_export_formats(self, client):
        resp = client.post(
            "/animation/generate",
            json={"prompt": "A cinematic scene"},
        )
        assert resp.status_code == 200
        assert "export_formats" in resp.json()

    def test_response_keyframes_have_required_fields(self, client):
        resp = client.post(
            "/animation/generate",
            json={"prompt": "A detailed scene description with camera movement"},
        )
        assert resp.status_code == 200
        kf = resp.json()["keyframes"][0]
        for field in ("scene_index", "start_time_sec", "duration_sec",
                      "description", "camera_move", "transition", "style_note"):
            assert field in kf, f"Missing field: {field}"

    def test_large_prompt(self, client):
        prompt = " ".join(["The story unfolds"] * 100)
        resp = client.post(
            "/animation/generate",
            json={"prompt": prompt},
        )
        assert resp.status_code == 200

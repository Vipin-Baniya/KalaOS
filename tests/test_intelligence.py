"""
Tests for Phase 16 — Creative Intelligence Engine, AI Assistant,
Comments, Follows, and Notifications.

Unit tests:
  - kalaintelligence.transform()  — all four transform pairs
  - kalaintelligence.ai_assist()  — universal assistant

API tests:
  POST  /ai/transform
  POST  /ai/assistant
  POST  /posts/{post_id}/comments
  GET   /posts/{post_id}/comments
  DELETE /comments/{comment_id}
  POST  /users/{target}/follow
  GET   /users/{email}/followers
  GET   /users/{email}/following
  GET   /notifications
  POST  /notifications/{id}/read
  POST  /notifications/read-all
"""

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit imports
# ---------------------------------------------------------------------------
from kalacore.kalaintelligence import (
    transform,
    ai_assist,
    VALID_INPUT_TYPES,
    VALID_OUTPUT_TYPES,
    _SUPPORTED_PAIRS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_state():
    """Clear auth and platform state before/after every test."""
    import main as _main
    import services.platform_service as _plat

    auth_svc = _main.auth_service
    auth_svc._USERS.clear()
    auth_svc._RESET_TOKENS.clear()

    def _clear_tables(conn):
        for tbl in ("projects", "posts", "messages", "likes",
                    "comments", "follows", "notifications"):
            conn.execute(f"DELETE FROM {tbl}")

    with _plat._db_lock:
        with _plat._get_db() as conn:
            _clear_tables(conn)

    yield

    auth_svc._USERS.clear()
    auth_svc._RESET_TOKENS.clear()

    with _plat._db_lock:
        with _plat._get_db() as conn:
            _clear_tables(conn)


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def _reg(client, email, password="Pass1234!", name="User"):
    client.post("/auth/register", json={"email": email, "password": password, "name": name})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["token"]


def _make_post(client, token):
    """Create a project and publish it; return (project_id, post_id)."""
    proj = client.post("/projects", json={
        "token": token, "title": "Test Project", "type": "text", "data": "{}",
    })
    assert proj.status_code == 200, proj.text
    pid = proj.json()["project"]["id"]
    post = client.post("/posts", json={"token": token, "project_id": pid})
    assert post.status_code == 200, post.text
    return pid, post.json()["post"]["id"]


# ════════════════════════════════════════════════════════════════════════════
# Unit tests: kalaintelligence.transform
# ════════════════════════════════════════════════════════════════════════════

class TestTransformTextToVideo:
    def test_basic(self):
        r = transform("text", "video", "A lonely astronaut drifts through space")
        assert r["scenes"]
        assert "mood" in r
        assert "color_palette" in r
        assert isinstance(r["color_palette"], list)

    def test_scene_count_respected(self):
        r = transform("text", "video", "Joy and light", options={"scene_count": 3})
        assert len(r["scenes"]) == 3

    def test_style_options(self):
        r = transform("text", "video", "Dark city rain", options={"style": "lofi"})
        assert r["scenes"]

    def test_mood_joyful(self):
        r = transform("text", "video", "happy smile bright celebrate joy")
        assert r["mood"] == "joyful"

    def test_mood_melancholic(self):
        r = transform("text", "video", "sad lonely rain cold tears grey")
        assert r["mood"] == "melancholic"

    def test_invalid_style_falls_back(self):
        r = transform("text", "video", "Any text", options={"style": "nonexistent"})
        assert r["scenes"]


class TestTransformTextToSong:
    def test_basic(self):
        r = transform("text", "song", "Rise and shine, a brand new day")
        assert "bpm" in r
        assert "structure" in r
        assert isinstance(r["structure"], list)
        assert "sections" in r
        assert "drums" in r
        assert "melody" in r

    def test_genre_field_present(self):
        r = transform("text", "song", "lofi chill beat study music")
        assert "genre" in r

    def test_chords_present(self):
        r = transform("text", "song", "Peaceful river flows gently")
        assert isinstance(r["chords"], list)
        assert len(r["chords"]) > 0

    def test_sections_match_structure(self):
        r = transform("text", "song", "Verse and chorus repeat")
        assert len(r["sections"]) == len(r["structure"])


class TestTransformDesignToAnimation:
    def test_basic(self):
        r = transform("design", "animation", "A bold geometric design with red rectangles")
        assert "animation" in r
        assert "mood" in r
        assert "color_palette" in r

    def test_duration_option(self):
        r = transform("design", "animation", "Dark background circles", options={"duration": 15})
        assert r["duration_seconds"] == 15

    def test_output_type_field(self):
        r = transform("design", "animation", "Bright blue star shapes")
        assert r["output_type"] == "animation"


class TestTransformMusicToVideo:
    def test_basic(self):
        r = transform("music", "video", "lofi chill hip hop 85bpm")
        assert "scenes" in r
        assert "bpm" in r
        assert "color_palette" in r

    def test_bpm_extraction(self):
        r = transform("music", "video", "dark trap beat 140bpm aggressive")
        assert r["bpm"] == 140

    def test_beat_sync_interval(self):
        r = transform("music", "video", "120bpm electronic dance")
        assert abs(r["beat_sync_interval"] - 0.5) < 0.01

    def test_scene_count_option(self):
        r = transform("music", "video", "ambient space drone 60bpm", options={"scene_count": 6})
        assert len(r["scenes"]) == 6

    def test_genre_detection_electronic(self):
        r = transform("music", "video", "fast EDM house techno 130bpm")
        assert r["genre"] == "electronic"

    def test_genre_detection_rock(self):
        r = transform("music", "video", "rock guitar metal distortion 120bpm")
        assert r["genre"] == "rock"


class TestTransformValidation:
    def test_invalid_input_type(self):
        with pytest.raises(ValueError, match="input_type"):
            transform("image", "video", "some text")

    def test_invalid_output_type(self):
        with pytest.raises(ValueError, match="output_type"):
            transform("text", "audio", "some text")

    def test_unsupported_pair(self):
        with pytest.raises(ValueError, match="not supported"):
            transform("music", "song", "beat description")

    def test_empty_data(self):
        with pytest.raises(ValueError, match="empty"):
            transform("text", "video", "")

    def test_whitespace_only_data(self):
        with pytest.raises(ValueError, match="empty"):
            transform("text", "video", "   ")


# ════════════════════════════════════════════════════════════════════════════
# Unit tests: kalaintelligence.ai_assist
# ════════════════════════════════════════════════════════════════════════════

class TestAiAssist:
    def test_basic(self):
        r = ai_assist("Hello world poem", "make this more emotional", "text")
        assert "action" in r
        assert "response" in r
        assert "suggestions" in r
        assert isinstance(r["suggestions"], list)
        assert len(r["suggestions"]) > 0

    def test_reel_action(self):
        r = ai_assist("My video", "turn this into a reel", "video")
        assert r["action"] == "reel"

    def test_lofi_action(self):
        r = ai_assist("My track", "convert to lofi track", "music")
        assert r["action"] == "lofi"

    def test_transform_hint_for_video(self):
        r = ai_assist("My poem text", "make a video from this", "text")
        assert "transform" in r
        assert r["transform"]["output_type"] == "video"

    def test_transform_hint_for_song(self):
        r = ai_assist("My text", "create a song from this", "text")
        assert "transform" in r
        assert r["transform"]["output_type"] == "song"

    def test_transform_hint_for_animation(self):
        r = ai_assist("Canvas design", "animate this", "visual")
        assert "transform" in r
        assert r["transform"]["output_type"] == "animation"

    def test_unknown_studio_falls_back(self):
        r = ai_assist("context", "help me", "unknown_studio")
        assert len(r["suggestions"]) > 0

    def test_empty_prompt_raises(self):
        with pytest.raises(ValueError):
            ai_assist("context", "")

    def test_suggestions_per_studio(self):
        for studio in ("text", "visual", "music", "animation", "video"):
            r = ai_assist("test context", "improve this", studio)
            assert len(r["suggestions"]) > 0


# ════════════════════════════════════════════════════════════════════════════
# API tests: POST /ai/transform
# ════════════════════════════════════════════════════════════════════════════

class TestAiTransformEndpoint:
    def test_text_to_video(self, client):
        r = client.post("/ai/transform", json={
            "input_type": "text",
            "output_type": "video",
            "data": "A journey through stars and dreams",
        })
        assert r.status_code == 200
        assert "scenes" in r.json()

    def test_text_to_song(self, client):
        r = client.post("/ai/transform", json={
            "input_type": "text",
            "output_type": "song",
            "data": "Rise up and shine like the morning sun",
        })
        assert r.status_code == 200
        body = r.json()
        assert "bpm" in body
        assert "structure" in body

    def test_design_to_animation(self, client):
        r = client.post("/ai/transform", json={
            "input_type": "design",
            "output_type": "animation",
            "data": "Bold circles and triangles on a dark canvas",
        })
        assert r.status_code == 200
        assert "animation" in r.json()

    def test_music_to_video(self, client):
        r = client.post("/ai/transform", json={
            "input_type": "music",
            "output_type": "video",
            "data": "90bpm lofi hip hop chill beat",
        })
        assert r.status_code == 200
        body = r.json()
        assert "scenes" in body
        assert body["bpm"] == 90

    def test_with_options(self, client):
        r = client.post("/ai/transform", json={
            "input_type": "text",
            "output_type": "video",
            "data": "Dark cinematic journey",
            "options": {"style": "cinematic", "scene_count": 3},
        })
        assert r.status_code == 200
        assert len(r.json()["scenes"]) == 3

    def test_invalid_input_type_422(self, client):
        r = client.post("/ai/transform", json={
            "input_type": "image",
            "output_type": "video",
            "data": "some text",
        })
        assert r.status_code == 422

    def test_empty_data_422(self, client):
        r = client.post("/ai/transform", json={
            "input_type": "text",
            "output_type": "video",
            "data": "  ",
        })
        assert r.status_code == 422

    def test_unsupported_pair_400(self, client):
        r = client.post("/ai/transform", json={
            "input_type": "music",
            "output_type": "song",
            "data": "a beat description",
        })
        assert r.status_code == 400


# ════════════════════════════════════════════════════════════════════════════
# API tests: POST /ai/assistant
# ════════════════════════════════════════════════════════════════════════════

class TestAiAssistantEndpoint:
    def test_basic(self, client):
        r = client.post("/ai/assistant", json={
            "prompt": "make this more emotional",
            "studio": "text",
            "context": "A simple poem",
        })
        assert r.status_code == 200
        body = r.json()
        assert "action" in body
        assert "response" in body
        assert "suggestions" in body

    def test_no_context_ok(self, client):
        r = client.post("/ai/assistant", json={"prompt": "help me create a reel"})
        assert r.status_code == 200
        assert r.json()["action"] == "reel"

    def test_empty_prompt_422(self, client):
        r = client.post("/ai/assistant", json={"prompt": ""})
        assert r.status_code == 422

    def test_cinematic_action(self, client):
        r = client.post("/ai/assistant", json={
            "prompt": "add cinematic feel",
            "studio": "video",
        })
        assert r.status_code == 200
        assert r.json()["action"] == "cinematic"

    def test_all_studios(self, client):
        for studio in ("text", "visual", "music", "animation", "video", "general"):
            r = client.post("/ai/assistant", json={
                "prompt": "improve this",
                "studio": studio,
                "context": "test",
            })
            assert r.status_code == 200


# ════════════════════════════════════════════════════════════════════════════
# API tests: Comments
# ════════════════════════════════════════════════════════════════════════════

class TestComments:
    def test_add_comment(self, client):
        tok1 = _reg(client, "author1@kala.io")
        tok2 = _reg(client, "commenter1@kala.io")
        _, post_id = _make_post(client, tok1)
        r = client.post(f"/posts/{post_id}/comments", json={
            "token": tok2, "content": "Amazing work!",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["content"] == "Amazing work!"
        assert body["post_id"] == post_id

    def test_get_comments(self, client):
        tok1 = _reg(client, "author2@kala.io")
        tok2 = _reg(client, "commenter2@kala.io")
        _, post_id = _make_post(client, tok1)
        client.post(f"/posts/{post_id}/comments", json={"token": tok2, "content": "Nice!"})
        r = client.get(f"/posts/{post_id}/comments")
        assert r.status_code == 200
        body = r.json()
        assert "comments" in body
        assert body["count"] == 1

    def test_add_multiple_comments(self, client):
        tok = _reg(client, "multi_author@kala.io")
        _, post_id = _make_post(client, tok)
        for i in range(3):
            r = client.post(f"/posts/{post_id}/comments", json={
                "token": tok, "content": f"Comment {i}",
            })
            assert r.status_code == 200
        r = client.get(f"/posts/{post_id}/comments")
        assert r.json()["count"] == 3

    def test_delete_own_comment(self, client):
        tok = _reg(client, "del_author@kala.io")
        _, post_id = _make_post(client, tok)
        add = client.post(f"/posts/{post_id}/comments", json={
            "token": tok, "content": "to be deleted",
        })
        cid = add.json()["id"]
        del_r = client.delete(f"/comments/{cid}", params={"token": tok})
        assert del_r.status_code == 200
        assert del_r.json()["deleted"] == cid

    def test_delete_other_users_comment_fails(self, client):
        tok1 = _reg(client, "owner_comment@kala.io")
        tok2 = _reg(client, "thief_comment@kala.io")
        _, post_id = _make_post(client, tok1)
        add = client.post(f"/posts/{post_id}/comments", json={
            "token": tok1, "content": "my comment",
        })
        cid = add.json()["id"]
        del_r = client.delete(f"/comments/{cid}", params={"token": tok2})
        assert del_r.status_code == 400

    def test_add_empty_comment_fails(self, client):
        tok = _reg(client, "empty_comment_user@kala.io")
        _, post_id = _make_post(client, tok)
        r = client.post(f"/posts/{post_id}/comments", json={
            "token": tok, "content": "   ",
        })
        assert r.status_code == 422

    def test_comment_nonexistent_post(self, client):
        tok = _reg(client, "nopost_user@kala.io")
        r = client.post("/posts/nonexistent-post-id/comments", json={
            "token": tok, "content": "hello",
        })
        assert r.status_code == 400

    def test_get_comments_empty_post(self, client):
        r = client.get("/posts/nonexistent-post-xyz/comments")
        assert r.status_code == 200
        assert r.json()["count"] == 0


# ════════════════════════════════════════════════════════════════════════════
# API tests: Follows
# ════════════════════════════════════════════════════════════════════════════

class TestFollows:
    def test_follow_user(self, client):
        tok1 = _reg(client, "follower_a@kala.io")
        email2 = "target_a@kala.io"
        _reg(client, email2)
        r = client.post(f"/users/{email2}/follow", json={"token": tok1})
        assert r.status_code == 200
        body = r.json()
        assert body["following"] is True
        assert body["follower_count"] >= 1

    def test_unfollow_user(self, client):
        tok1 = _reg(client, "follower_b@kala.io")
        email2 = "target_b@kala.io"
        _reg(client, email2)
        # Follow
        client.post(f"/users/{email2}/follow", json={"token": tok1})
        # Unfollow
        r = client.post(f"/users/{email2}/follow", json={"token": tok1})
        assert r.status_code == 200
        assert r.json()["following"] is False
        assert r.json()["follower_count"] == 0

    def test_get_followers(self, client):
        tok1 = _reg(client, "follower_c@kala.io")
        email2 = "target_c@kala.io"
        _reg(client, email2)
        client.post(f"/users/{email2}/follow", json={"token": tok1})
        r = client.get(f"/users/{email2}/followers")
        assert r.status_code == 200
        body = r.json()
        assert "follower_c@kala.io" in body["followers"]
        assert body["count"] >= 1

    def test_get_following(self, client):
        email1 = "follower_d@kala.io"
        tok1 = _reg(client, email1)
        email2 = "target_d@kala.io"
        _reg(client, email2)
        client.post(f"/users/{email2}/follow", json={"token": tok1})
        r = client.get(f"/users/{email1}/following")
        assert r.status_code == 200
        body = r.json()
        assert email2 in body["following"]
        assert body["count"] >= 1

    def test_follow_self_fails(self, client):
        email1 = "selffollow@kala.io"
        tok1 = _reg(client, email1)
        r = client.post(f"/users/{email1}/follow", json={"token": tok1})
        assert r.status_code == 400

    def test_invalid_token_follow_fails(self, client):
        email2 = "target_e@kala.io"
        _reg(client, email2)
        r = client.post(f"/users/{email2}/follow", json={"token": "bad-token"})
        assert r.status_code == 400

    def test_get_followers_empty(self, client):
        r = client.get("/users/nobody@kala.io/followers")
        assert r.status_code == 200
        assert r.json()["count"] == 0

    def test_get_following_empty(self, client):
        r = client.get("/users/nobody@kala.io/following")
        assert r.status_code == 200
        assert r.json()["count"] == 0


# ════════════════════════════════════════════════════════════════════════════
# API tests: Notifications
# ════════════════════════════════════════════════════════════════════════════

class TestNotifications:
    def test_get_notifications_initially_empty(self, client):
        tok = _reg(client, "notif_user1@kala.io")
        r = client.get("/notifications", params={"token": tok})
        assert r.status_code == 200
        body = r.json()
        assert "notifications" in body
        assert body["count"] == 0

    def test_comment_creates_notification(self, client):
        """Commenting on user1's post should create a notif for user1."""
        tok1 = _reg(client, "notif_author@kala.io")
        tok2 = _reg(client, "notif_commenter@kala.io")
        _, post_id = _make_post(client, tok1)
        client.post(f"/posts/{post_id}/comments", json={
            "token": tok2, "content": "Great post!",
        })
        r = client.get("/notifications", params={"token": tok1})
        assert r.status_code == 200
        notifs = r.json()["notifications"]
        comment_notifs = [n for n in notifs if n["type"] == "comment"]
        assert len(comment_notifs) == 1

    def test_follow_creates_notification(self, client):
        email_target = "notif_target@kala.io"
        tok_follower = _reg(client, "notif_follower@kala.io")
        tok_target   = _reg(client, email_target)
        client.post(f"/users/{email_target}/follow", json={"token": tok_follower})
        r = client.get("/notifications", params={"token": tok_target})
        assert r.status_code == 200
        notifs = r.json()["notifications"]
        follow_notifs = [n for n in notifs if n["type"] == "follow"]
        assert len(follow_notifs) == 1

    def test_mark_notification_read(self, client):
        tok1 = _reg(client, "notif_mark_author@kala.io")
        tok2 = _reg(client, "notif_mark_commenter@kala.io")
        _, post_id = _make_post(client, tok1)
        client.post(f"/posts/{post_id}/comments", json={"token": tok2, "content": "hi"})
        r = client.get("/notifications", params={"token": tok1})
        notifs = r.json()["notifications"]
        assert len(notifs) >= 1
        nid = notifs[0]["id"]
        read_r = client.post(f"/notifications/{nid}/read", json={"token": tok1})
        assert read_r.status_code == 200
        assert read_r.json()["read"] == nid
        # Verify it's marked read
        r2 = client.get("/notifications", params={"token": tok1})
        marked = [n for n in r2.json()["notifications"] if n["id"] == nid]
        assert marked[0]["read"] is True

    def test_mark_all_read(self, client):
        tok = _reg(client, "notif_readall@kala.io")
        r = client.post("/notifications/read-all", json={"token": tok})
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_notifications_invalid_token(self, client):
        r = client.get("/notifications", params={"token": "invalid"})
        assert r.status_code == 400

    def test_notification_has_expected_fields(self, client):
        tok1 = _reg(client, "notif_fields_author@kala.io")
        tok2 = _reg(client, "notif_fields_commenter@kala.io")
        _, post_id = _make_post(client, tok1)
        client.post(f"/posts/{post_id}/comments", json={"token": tok2, "content": "check fields"})
        r = client.get("/notifications", params={"token": tok1})
        assert r.status_code == 200
        for n in r.json()["notifications"]:
            assert "id" in n
            assert "type" in n
            assert "actor" in n
            assert "content" in n
            assert "read" in n
            assert "created_at" in n

    def test_self_comment_no_notification(self, client):
        """Commenting on your own post should NOT create a notification."""
        tok = _reg(client, "notif_self@kala.io")
        _, post_id = _make_post(client, tok)
        client.post(f"/posts/{post_id}/comments", json={"token": tok, "content": "own comment"})
        r = client.get("/notifications", params={"token": tok})
        assert r.json()["count"] == 0

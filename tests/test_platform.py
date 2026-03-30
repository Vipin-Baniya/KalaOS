"""
Tests for the KalaOS Platform Layer:
  - Projects CRUD
  - Feed (publish, get_feed)
  - Chat (send_message, get_conversation, list_conversations)
  - User profile GET /user/{id}
  - Update profile with avatar_url and bio
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_state():
    """Clear auth and platform state before and after every test."""
    import main as _main
    import services.platform_service as _plat

    auth_svc = _main.auth_service
    auth_svc._USERS.clear()
    auth_svc._RESET_TOKENS.clear()

    with _plat._db_lock:
        with _plat._get_db() as conn:
            conn.execute("DELETE FROM projects")
            conn.execute("DELETE FROM posts")
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM likes")

    yield

    auth_svc._USERS.clear()
    auth_svc._RESET_TOKENS.clear()

    with _plat._db_lock:
        with _plat._get_db() as conn:
            conn.execute("DELETE FROM projects")
            conn.execute("DELETE FROM posts")
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM likes")


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def _register_and_login(client, email="user@example.com", password="password123", name="User"):
    client.post("/auth/register", json={"email": email, "password": password, "name": name})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["token"]


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------

class TestUserProfile:
    def test_get_profile_not_found(self, client):
        resp = client.get("/user/nobody@example.com")
        assert resp.status_code == 404

    def test_get_profile_success(self, client):
        token = _register_and_login(client, name="Alice")
        resp = client.get("/user/user@example.com")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "user@example.com"
        assert data["name"] == "Alice"
        assert "avatar_url" in data
        assert "bio" in data
        assert "created_at" in data

    def test_get_profile_case_insensitive(self, client):
        _register_and_login(client)
        resp = client.get("/user/USER@EXAMPLE.COM")
        assert resp.status_code == 200
        assert resp.json()["email"] == "user@example.com"


# ---------------------------------------------------------------------------
# Update Profile (avatar_url + bio)
# ---------------------------------------------------------------------------

class TestUpdateProfileExtended:
    def test_update_avatar_and_bio(self, client):
        token = _register_and_login(client)
        resp = client.post("/auth/update-profile", json={
            "token": token,
            "name": "Updated",
            "avatar_url": "https://example.com/avatar.png",
            "bio": "I make music",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["user"]["avatar_url"] == "https://example.com/avatar.png"
        assert data["user"]["bio"] == "I make music"

    def test_update_avatar_only(self, client):
        token = _register_and_login(client)
        resp = client.post("/auth/update-profile", json={
            "token": token,
            "name": "Alice",
            "avatar_url": "https://example.com/pic.jpg",
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["avatar_url"] == "https://example.com/pic.jpg"

    def test_profile_reflected_in_me(self, client):
        token = _register_and_login(client)
        client.post("/auth/update-profile", json={
            "token": token,
            "name": "Alice",
            "bio": "Artist",
        })
        resp = client.get(f"/auth/me?token={token}")
        assert resp.json()["bio"] == "Artist"

    def test_profile_reflected_in_user_endpoint(self, client):
        token = _register_and_login(client)
        client.post("/auth/update-profile", json={
            "token": token,
            "name": "Alice",
            "bio": "Poet",
            "avatar_url": "https://example.com/a.png",
        })
        resp = client.get("/user/user@example.com")
        assert resp.json()["bio"] == "Poet"
        assert resp.json()["avatar_url"] == "https://example.com/a.png"


# ---------------------------------------------------------------------------
# Projects CRUD
# ---------------------------------------------------------------------------

class TestProjectsCRUD:
    def test_create_project_success(self, client):
        token = _register_and_login(client)
        resp = client.post("/projects", json={
            "token": token,
            "title": "My Song",
            "type": "music",
            "data": '{"bpm": 120}',
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        p = data["project"]
        assert p["title"] == "My Song"
        assert p["type"] == "music"
        assert p["data"] == '{"bpm": 120}'
        assert "id" in p

    def test_create_invalid_type(self, client):
        token = _register_and_login(client)
        resp = client.post("/projects", json={
            "token": token, "title": "X", "type": "invalid",
        })
        assert resp.status_code == 400
        assert "Invalid project type" in resp.json()["detail"]

    def test_create_empty_title_rejected(self, client):
        token = _register_and_login(client)
        resp = client.post("/projects", json={
            "token": token, "title": "   ", "type": "text",
        })
        assert resp.status_code == 400

    def test_create_unauthenticated(self, client):
        resp = client.post("/projects", json={
            "token": "bogus", "title": "X", "type": "text",
        })
        assert resp.status_code == 400

    def test_list_projects_empty(self, client):
        token = _register_and_login(client)
        resp = client.get(f"/projects?token={token}")
        assert resp.status_code == 200
        assert resp.json()["projects"] == []

    def test_list_projects_returns_own(self, client):
        token = _register_and_login(client)
        client.post("/projects", json={"token": token, "title": "P1", "type": "text"})
        client.post("/projects", json={"token": token, "title": "P2", "type": "visual"})
        resp = client.get(f"/projects?token={token}")
        assert len(resp.json()["projects"]) == 2

    def test_list_projects_isolated_per_user(self, client):
        t1 = _register_and_login(client, "a@example.com")
        t2 = _register_and_login(client, "b@example.com")
        client.post("/projects", json={"token": t1, "title": "A's project", "type": "text"})
        resp = client.get(f"/projects?token={t2}")
        assert resp.json()["projects"] == []

    def test_get_project_success(self, client):
        token = _register_and_login(client)
        create_resp = client.post("/projects", json={"token": token, "title": "P", "type": "video"})
        pid = create_resp.json()["project"]["id"]
        resp = client.get(f"/projects/{pid}?token={token}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_get_project_not_found(self, client):
        token = _register_and_login(client)
        resp = client.get(f"/projects/nonexistent-id?token={token}")
        assert resp.status_code == 404

    def test_get_project_other_user_denied(self, client):
        t1 = _register_and_login(client, "a@example.com")
        t2 = _register_and_login(client, "b@example.com")
        create_resp = client.post("/projects", json={"token": t1, "title": "A", "type": "text"})
        pid = create_resp.json()["project"]["id"]
        resp = client.get(f"/projects/{pid}?token={t2}")
        assert resp.status_code == 404

    def test_update_project_title(self, client):
        token = _register_and_login(client)
        create_resp = client.post("/projects", json={"token": token, "title": "Old", "type": "text"})
        pid = create_resp.json()["project"]["id"]
        resp = client.put(f"/projects/{pid}", json={"token": token, "title": "New"})
        assert resp.status_code == 200
        assert resp.json()["project"]["title"] == "New"

    def test_update_project_data(self, client):
        token = _register_and_login(client)
        create_resp = client.post("/projects", json={"token": token, "title": "T", "type": "music"})
        pid = create_resp.json()["project"]["id"]
        resp = client.put(f"/projects/{pid}", json={"token": token, "data": '{"bpm": 90}'})
        assert resp.status_code == 200
        assert resp.json()["project"]["data"] == '{"bpm": 90}'

    def test_update_project_not_found(self, client):
        token = _register_and_login(client)
        resp = client.put("/projects/ghost", json={"token": token, "title": "X"})
        assert resp.status_code == 400

    def test_delete_project_success(self, client):
        token = _register_and_login(client)
        create_resp = client.post("/projects", json={"token": token, "title": "Del", "type": "text"})
        pid = create_resp.json()["project"]["id"]
        resp = client.delete(f"/projects/{pid}?token={token}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_delete_project_gone_after(self, client):
        token = _register_and_login(client)
        create_resp = client.post("/projects", json={"token": token, "title": "Del", "type": "text"})
        pid = create_resp.json()["project"]["id"]
        client.delete(f"/projects/{pid}?token={token}")
        resp = client.get(f"/projects/{pid}?token={token}")
        assert resp.status_code == 404

    def test_delete_project_not_found(self, client):
        token = _register_and_login(client)
        resp = client.delete(f"/projects/ghost?token={token}")
        assert resp.status_code == 404

    def test_all_project_types_valid(self, client):
        token = _register_and_login(client)
        for ptype in ("text", "visual", "music", "video", "animation"):
            resp = client.post("/projects", json={"token": token, "title": ptype, "type": ptype})
            assert resp.status_code == 200, f"type {ptype!r} should be valid"


# ---------------------------------------------------------------------------
# Feed / Posts
# ---------------------------------------------------------------------------

class TestFeed:
    def test_publish_project_success(self, client):
        token = _register_and_login(client)
        p = client.post("/projects", json={"token": token, "title": "Song", "type": "music"})
        pid = p.json()["project"]["id"]
        resp = client.post("/posts", json={"token": token, "project_id": pid})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["post"]["project_id"] == pid

    def test_publish_already_published_fails(self, client):
        token = _register_and_login(client)
        p = client.post("/projects", json={"token": token, "title": "S", "type": "music"})
        pid = p.json()["project"]["id"]
        client.post("/posts", json={"token": token, "project_id": pid})
        resp = client.post("/posts", json={"token": token, "project_id": pid})
        assert resp.status_code == 400
        assert "already published" in resp.json()["detail"]

    def test_publish_nonexistent_project_fails(self, client):
        token = _register_and_login(client)
        resp = client.post("/posts", json={"token": token, "project_id": "ghost"})
        assert resp.status_code == 400

    def test_publish_other_users_project_fails(self, client):
        t1 = _register_and_login(client, "a@example.com")
        t2 = _register_and_login(client, "b@example.com")
        p = client.post("/projects", json={"token": t1, "title": "A", "type": "text"})
        pid = p.json()["project"]["id"]
        resp = client.post("/posts", json={"token": t2, "project_id": pid})
        assert resp.status_code == 400

    def test_get_feed_empty(self, client):
        resp = client.get("/feed")
        assert resp.status_code == 200
        assert resp.json()["posts"] == []

    def test_get_feed_returns_published(self, client):
        token = _register_and_login(client)
        p = client.post("/projects", json={"token": token, "title": "T", "type": "text"})
        pid = p.json()["project"]["id"]
        client.post("/posts", json={"token": token, "project_id": pid})
        resp = client.get("/feed")
        posts = resp.json()["posts"]
        assert len(posts) == 1
        assert posts[0]["project_id"] == pid
        assert posts[0]["title"] == "T"
        assert "author_name" in posts[0]
        assert "avatar_url" in posts[0]

    def test_get_feed_pagination(self, client):
        token = _register_and_login(client)
        ids = []
        for i in range(5):
            p = client.post("/projects", json={"token": token, "title": f"P{i}", "type": "text"})
            ids.append(p.json()["project"]["id"])
        for pid in ids:
            client.post("/posts", json={"token": token, "project_id": pid})
        resp1 = client.get("/feed?limit=3&offset=0")
        resp2 = client.get("/feed?limit=3&offset=3")
        assert len(resp1.json()["posts"]) == 3
        assert len(resp2.json()["posts"]) == 2

    def test_feed_ordered_newest_first(self, client):
        token = _register_and_login(client)
        for i in range(3):
            p = client.post("/projects", json={"token": token, "title": f"P{i}", "type": "text"})
            pid = p.json()["project"]["id"]
            client.post("/posts", json={"token": token, "project_id": pid})
        posts = client.get("/feed").json()["posts"]
        timestamps = [p["created_at"] for p in posts]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_feed_unauthenticated_access(self, client):
        """Feed is public — no token required."""
        resp = client.get("/feed")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Chat / Messages
# ---------------------------------------------------------------------------

class TestChat:
    def test_send_message_success(self, client):
        t1 = _register_and_login(client, "a@example.com")
        _register_and_login(client, "b@example.com")
        resp = client.post("/messages", json={
            "token": t1,
            "receiver_id": "b@example.com",
            "content": "Hello!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        msg = data["message"]
        assert msg["sender_id"] == "a@example.com"
        assert msg["receiver_id"] == "b@example.com"
        assert msg["content"] == "Hello!"

    def test_send_empty_content_rejected(self, client):
        t1 = _register_and_login(client, "a@example.com")
        resp = client.post("/messages", json={
            "token": t1, "receiver_id": "b@example.com", "content": "   ",
        })
        assert resp.status_code == 400

    def test_send_to_self_rejected(self, client):
        t1 = _register_and_login(client, "a@example.com")
        resp = client.post("/messages", json={
            "token": t1, "receiver_id": "a@example.com", "content": "Hi me",
        })
        assert resp.status_code == 400
        assert "yourself" in resp.json()["detail"]

    def test_send_unauthenticated(self, client):
        resp = client.post("/messages", json={
            "token": "bogus", "receiver_id": "b@example.com", "content": "Hi",
        })
        assert resp.status_code == 400

    def test_get_conversation_empty(self, client):
        t1 = _register_and_login(client, "a@example.com")
        resp = client.get(f"/messages/b@example.com?token={t1}")
        assert resp.status_code == 200
        assert resp.json()["messages"] == []

    def test_get_conversation_returns_messages(self, client):
        t1 = _register_and_login(client, "a@example.com")
        t2 = _register_and_login(client, "b@example.com")
        client.post("/messages", json={"token": t1, "receiver_id": "b@example.com", "content": "Hi"})
        client.post("/messages", json={"token": t2, "receiver_id": "a@example.com", "content": "Hey"})
        resp = client.get(f"/messages/b@example.com?token={t1}")
        msgs = resp.json()["messages"]
        assert len(msgs) == 2

    def test_get_conversation_ordered_asc(self, client):
        t1 = _register_and_login(client, "a@example.com")
        _register_and_login(client, "b@example.com")
        for i in range(3):
            client.post("/messages", json={
                "token": t1, "receiver_id": "b@example.com", "content": f"msg{i}",
            })
        msgs = client.get(f"/messages/b@example.com?token={t1}").json()["messages"]
        ts = [m["created_at"] for m in msgs]
        assert ts == sorted(ts)

    def test_get_conversation_unauthenticated(self, client):
        resp = client.get("/messages/b@example.com?token=bogus")
        assert resp.status_code == 401

    def test_get_conversation_pagination(self, client):
        t1 = _register_and_login(client, "a@example.com")
        _register_and_login(client, "b@example.com")
        for i in range(5):
            client.post("/messages", json={
                "token": t1, "receiver_id": "b@example.com", "content": f"m{i}",
            })
        r1 = client.get(f"/messages/b@example.com?token={t1}&limit=3&offset=0").json()["messages"]
        r2 = client.get(f"/messages/b@example.com?token={t1}&limit=3&offset=3").json()["messages"]
        assert len(r1) == 3
        assert len(r2) == 2

    def test_list_conversations_empty(self, client):
        t1 = _register_and_login(client, "a@example.com")
        resp = client.get(f"/conversations?token={t1}")
        assert resp.status_code == 200
        assert resp.json()["conversations"] == []

    def test_list_conversations_shows_peers(self, client):
        t1 = _register_and_login(client, "a@example.com")
        _register_and_login(client, "b@example.com")
        _register_and_login(client, "c@example.com")
        client.post("/messages", json={"token": t1, "receiver_id": "b@example.com", "content": "Hi B"})
        client.post("/messages", json={"token": t1, "receiver_id": "c@example.com", "content": "Hi C"})
        resp = client.get(f"/conversations?token={t1}")
        convs = resp.json()["conversations"]
        peers = {c["peer_id"] for c in convs}
        assert "b@example.com" in peers
        assert "c@example.com" in peers

    def test_list_conversations_shows_last_message(self, client):
        t1 = _register_and_login(client, "a@example.com")
        _register_and_login(client, "b@example.com")
        client.post("/messages", json={"token": t1, "receiver_id": "b@example.com", "content": "First"})
        client.post("/messages", json={"token": t1, "receiver_id": "b@example.com", "content": "Last"})
        convs = client.get(f"/conversations?token={t1}").json()["conversations"]
        assert convs[0]["last_message"] == "Last"

    def test_list_conversations_unauthenticated(self, client):
        resp = client.get("/conversations?token=bogus")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Like System
# ---------------------------------------------------------------------------

class TestLikeSystem:
    def test_toggle_like(self, client):
        token = _register_and_login(client)
        p = client.post("/projects", json={"token": token, "title": "Song", "type": "music"})
        pid = p.json()["project"]["id"]
        post_resp = client.post("/posts", json={"token": token, "project_id": pid})
        post_id = post_resp.json()["post"]["id"]

        resp = client.post(f"/posts/{post_id}/like", json={"token": token})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["liked"] is True
        assert data["like_count"] == 1

    def test_toggle_like_twice(self, client):
        token = _register_and_login(client)
        p = client.post("/projects", json={"token": token, "title": "Song", "type": "music"})
        pid = p.json()["project"]["id"]
        post_resp = client.post("/posts", json={"token": token, "project_id": pid})
        post_id = post_resp.json()["post"]["id"]

        client.post(f"/posts/{post_id}/like", json={"token": token})
        resp = client.post(f"/posts/{post_id}/like", json={"token": token})
        assert resp.status_code == 200
        data = resp.json()
        assert data["liked"] is False
        assert data["like_count"] == 0

    def test_like_count_in_feed(self, client):
        token = _register_and_login(client)
        p = client.post("/projects", json={"token": token, "title": "Track", "type": "music"})
        pid = p.json()["project"]["id"]
        post_resp = client.post("/posts", json={"token": token, "project_id": pid})
        post_id = post_resp.json()["post"]["id"]

        client.post(f"/posts/{post_id}/like", json={"token": token})
        feed = client.get("/feed").json()["posts"]
        assert len(feed) == 1
        assert feed[0]["like_count"] == 1

    def test_like_nonexistent_post(self, client):
        token = _register_and_login(client)
        resp = client.post("/posts/nonexistent/like", json={"token": token})
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()

    def test_like_unauthenticated(self, client):
        resp = client.post("/posts/any-id/like", json={"token": "bogus"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# User Posts (Creations)
# ---------------------------------------------------------------------------

class TestGetUserPosts:
    def test_get_user_posts_empty(self, client):
        _register_and_login(client)
        resp = client.get("/user/user@example.com/posts")
        assert resp.status_code == 200
        assert resp.json()["posts"] == []

    def test_get_user_posts(self, client):
        token = _register_and_login(client)
        p = client.post("/projects", json={"token": token, "title": "My Poem", "type": "text"})
        pid = p.json()["project"]["id"]
        client.post("/posts", json={"token": token, "project_id": pid})

        resp = client.get("/user/user@example.com/posts")
        assert resp.status_code == 200
        posts = resp.json()["posts"]
        assert len(posts) == 1
        assert posts[0]["title"] == "My Poem"
        assert posts[0]["type"] == "text"
        assert "like_count" in posts[0]

    def test_get_user_posts_with_likes(self, client):
        token = _register_and_login(client)
        p = client.post("/projects", json={"token": token, "title": "Track", "type": "music"})
        pid = p.json()["project"]["id"]
        post_resp = client.post("/posts", json={"token": token, "project_id": pid})
        post_id = post_resp.json()["post"]["id"]
        client.post(f"/posts/{post_id}/like", json={"token": token})

        resp = client.get("/user/user@example.com/posts")
        posts = resp.json()["posts"]
        assert posts[0]["like_count"] == 1

"""
Platform Service — Projects, Feed, and Chat
---------------------------------------------
Manages:
  - Projects: user-owned creative work (text/visual/music/video)
  - Posts: published projects (public feed)
  - Messages: 1:1 chat between users

All data is persisted in the same SQLite database as auth_service (KALA_DB_PATH).

Public API
----------
Projects:
  create_project(token, title, type_, data)          → project dict
  list_projects(token)                               → list of project dicts
  get_project(token, project_id)                     → project dict or raises ValueError
  update_project(token, project_id, title, data)     → project dict or raises ValueError
  delete_project(token, project_id)                  → None or raises ValueError

Feed:
  publish_project(token, project_id)                 → post dict or raises ValueError
  get_feed(limit, offset)                            → list of post dicts

Chat:
  send_message(token, receiver_id, content)          → message dict or raises ValueError
  get_conversation(token, peer_id, limit, offset)    → list of message dicts
  list_conversations(token)                          → list of conversation summaries
"""

import os
import sqlite3
import threading
import time
import uuid
from typing import List, Optional

import services.auth_service as auth_service

_DB_PATH = os.environ.get("KALA_DB_PATH", "kalaos.db")
_db_lock = threading.Lock()


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _db_init() -> None:
    with _db_lock:
        with _get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id         TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    type       TEXT NOT NULL,
                    title      TEXT NOT NULL,
                    data       TEXT NOT NULL DEFAULT '{}',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id         TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    type       TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id          TEXT PRIMARY KEY,
                    sender_id   TEXT NOT NULL,
                    receiver_id TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    created_at  INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS likes (
                    id         TEXT PRIMARY KEY,
                    post_id    TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE (post_id, user_email)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_likes_post ON likes(post_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(sender_id, receiver_id)")


_db_init()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_auth(token: str) -> str:
    """Verify token and return email, or raise ValueError."""
    user = auth_service.get_user(token)
    if not user:
        raise ValueError("Invalid or expired session token.")
    return user["email"]


def _row_to_project(row) -> dict:
    return {
        "id":         row["id"],
        "user_email": row["user_email"],
        "type":       row["type"],
        "title":      row["title"],
        "data":       row["data"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_post(row) -> dict:
    return {
        "id":         row["id"],
        "user_email": row["user_email"],
        "project_id": row["project_id"],
        "type":       row["type"],
        "created_at": row["created_at"],
    }


def _row_to_message(row) -> dict:
    return {
        "id":          row["id"],
        "sender_id":   row["sender_id"],
        "receiver_id": row["receiver_id"],
        "content":     row["content"],
        "created_at":  row["created_at"],
    }


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

VALID_PROJECT_TYPES = {"text", "visual", "music", "video", "animation"}


def create_project(token: str, title: str, type_: str, data: str = "{}") -> dict:
    email = _require_auth(token)
    if type_ not in VALID_PROJECT_TYPES:
        raise ValueError(f"Invalid project type. Must be one of: {', '.join(sorted(VALID_PROJECT_TYPES))}")
    if not title.strip():
        raise ValueError("Title must not be empty.")
    now = int(time.time())
    pid = str(uuid.uuid4())
    with _db_lock:
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO projects (id, user_email, type, title, data, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, email, type_, title.strip(), data, now, now),
            )
    return {"id": pid, "user_email": email, "type": type_, "title": title.strip(),
            "data": data, "created_at": now, "updated_at": now}


def list_projects(token: str) -> List[dict]:
    email = _require_auth(token)
    with _db_lock:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM projects WHERE user_email = ? ORDER BY updated_at DESC",
                (email,),
            ).fetchall()
    return [_row_to_project(r) for r in rows]


def get_project(token: str, project_id: str) -> dict:
    email = _require_auth(token)
    with _db_lock:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ? AND user_email = ?",
                (project_id, email),
            ).fetchone()
    if not row:
        raise ValueError("Project not found.")
    return _row_to_project(row)


def update_project(token: str, project_id: str, title: Optional[str] = None,
                   data: Optional[str] = None) -> dict:
    email = _require_auth(token)
    with _db_lock:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ? AND user_email = ?",
                (project_id, email),
            ).fetchone()
            if not row:
                raise ValueError("Project not found.")
            new_title = title.strip() if title is not None else row["title"]
            new_data  = data if data is not None else row["data"]
            if not new_title:
                raise ValueError("Title must not be empty.")
            now = int(time.time())
            conn.execute(
                "UPDATE projects SET title=?, data=?, updated_at=? WHERE id=?",
                (new_title, new_data, now, project_id),
            )
    return {"id": project_id, "user_email": email, "type": row["type"],
            "title": new_title, "data": new_data,
            "created_at": row["created_at"], "updated_at": now}


def delete_project(token: str, project_id: str) -> None:
    email = _require_auth(token)
    with _db_lock:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT id FROM projects WHERE id = ? AND user_email = ?",
                (project_id, email),
            ).fetchone()
            if not row:
                raise ValueError("Project not found.")
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


# ---------------------------------------------------------------------------
# Feed / Posts
# ---------------------------------------------------------------------------

def publish_project(token: str, project_id: str) -> dict:
    email = _require_auth(token)
    with _db_lock:
        with _get_db() as conn:
            proj = conn.execute(
                "SELECT * FROM projects WHERE id = ? AND user_email = ?",
                (project_id, email),
            ).fetchone()
            if not proj:
                raise ValueError("Project not found.")
            existing = conn.execute(
                "SELECT id FROM posts WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            if existing:
                raise ValueError("Project is already published.")
            now  = int(time.time())
            pid  = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO posts (id, user_email, project_id, type, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (pid, email, project_id, proj["type"], now),
            )
    return {"id": pid, "user_email": email, "project_id": project_id,
            "type": proj["type"], "created_at": now}


def get_feed(limit: int = 20, offset: int = 0) -> List[dict]:
    limit  = min(max(1, limit),  100)
    offset = max(0, offset)
    with _db_lock:
        with _get_db() as conn:
            rows = conn.execute(
                """
                SELECT p.id, p.user_email, p.project_id, p.type, p.created_at,
                       pr.title, pr.data,
                       u.name AS author_name, u.avatar_url,
                       (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count
                FROM posts p
                JOIN projects pr ON pr.id = p.project_id
                JOIN users u     ON u.email = p.user_email
                ORDER BY p.created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
    result = []
    for r in rows:
        result.append({
            "id":          r["id"],
            "user_email":  r["user_email"],
            "author_name": r["author_name"],
            "avatar_url":  r["avatar_url"],
            "project_id":  r["project_id"],
            "type":        r["type"],
            "title":       r["title"],
            "data":        r["data"],
            "created_at":  r["created_at"],
            "like_count":  r["like_count"],
        })
    return result


# ---------------------------------------------------------------------------
# Chat / Messages
# ---------------------------------------------------------------------------

def send_message(token: str, receiver_id: str, content: str) -> dict:
    sender = _require_auth(token)
    if not content.strip():
        raise ValueError("Message content must not be empty.")
    if receiver_id == sender:
        raise ValueError("Cannot send message to yourself.")
    now = int(time.time())
    mid = str(uuid.uuid4())
    with _db_lock:
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO messages (id, sender_id, receiver_id, content, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (mid, sender, receiver_id, content.strip(), now),
            )
    return {"id": mid, "sender_id": sender, "receiver_id": receiver_id,
            "content": content.strip(), "created_at": now}


def get_conversation(token: str, peer_id: str,
                     limit: int = 50, offset: int = 0) -> List[dict]:
    me     = _require_auth(token)
    limit  = min(max(1, limit), 200)
    offset = max(0, offset)
    with _db_lock:
        with _get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE (sender_id = ? AND receiver_id = ?)
                   OR (sender_id = ? AND receiver_id = ?)
                ORDER BY created_at ASC
                LIMIT ? OFFSET ?
                """,
                (me, peer_id, peer_id, me, limit, offset),
            ).fetchall()
    return [_row_to_message(r) for r in rows]


def list_conversations(token: str) -> List[dict]:
    """Return one entry per unique peer, showing the last message."""
    me = _require_auth(token)
    with _db_lock:
        with _get_db() as conn:
            rows = conn.execute(
                """
                SELECT m.peer_id,
                       m.created_at  AS last_ts,
                       m.last_content
                FROM (
                    SELECT
                        CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS peer_id,
                        created_at,
                        content AS last_content,
                        rowid
                    FROM messages
                    WHERE sender_id = ? OR receiver_id = ?
                ) m
                INNER JOIN (
                    SELECT
                        CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS peer_id,
                        MAX(rowid) AS max_rowid
                    FROM messages
                    WHERE sender_id = ? OR receiver_id = ?
                    GROUP BY peer_id
                ) latest ON m.peer_id = latest.peer_id AND m.rowid = latest.max_rowid
                ORDER BY last_ts DESC
                """,
                (me, me, me, me, me, me),
            ).fetchall()
    return [
        {"peer_id": r["peer_id"], "last_message": r["last_content"], "last_ts": r["last_ts"]}
        for r in rows
    ]


def toggle_like(token: str, post_id: str) -> dict:
    """Toggle a like on a post. Returns {liked: bool, like_count: int}."""
    email = _require_auth(token)
    with _db_lock:
        with _get_db() as conn:
            post = conn.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
            if not post:
                raise ValueError("Post not found.")
            existing = conn.execute(
                "SELECT id FROM likes WHERE post_id = ? AND user_email = ?",
                (post_id, email),
            ).fetchone()
            if existing:
                conn.execute("DELETE FROM likes WHERE post_id = ? AND user_email = ?", (post_id, email))
                liked = False
            else:
                conn.execute(
                    "INSERT INTO likes (id, post_id, user_email, created_at) VALUES (?,?,?,?)",
                    (str(uuid.uuid4()), post_id, email, int(time.time())),
                )
                liked = True
            count = conn.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,)).fetchone()[0]
    return {"liked": liked, "like_count": count}


def get_user_posts(email: str) -> List[dict]:
    """Return published posts for a given user email (public, no token required)."""
    with _db_lock:
        with _get_db() as conn:
            rows = conn.execute(
                """
                SELECT po.id, po.project_id, po.type, po.created_at,
                       pr.title,
                       (SELECT COUNT(*) FROM likes l WHERE l.post_id = po.id) AS like_count
                FROM posts po
                JOIN projects pr ON pr.id = po.project_id
                WHERE po.user_email = ?
                ORDER BY po.created_at DESC
                """,
                (email,),
            ).fetchall()
    return [
        {
            "id":         r["id"],
            "project_id": r["project_id"],
            "type":       r["type"],
            "title":      r["title"],
            "like_count": r["like_count"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]

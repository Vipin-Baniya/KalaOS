"""Tests for kalacollab module and /collab/* endpoints."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient
from main import app
from kalacore.kalacollab import (
    create_collab_workspace,
    add_collaborator,
    get_collab_activity,
    generate_collab_suggestions,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# create_collab_workspace – unit tests
# ---------------------------------------------------------------------------

def test_create_collab_workspace_valid():
    ws = create_collab_workspace("My Band", "music", "alice@example.com", "Our collab")
    assert ws["name"] == "My Band"
    assert ws["project_type"] == "music"
    assert ws["owner"] == "alice@example.com"
    assert ws["status"] == "active"
    assert "workspace_id" in ws
    assert "created_at" in ws
    assert isinstance(ws["members"], list)
    assert len(ws["members"]) == 1


def test_create_collab_workspace_all_project_types():
    for pt in ("music", "visual", "video", "animation", "text", "mixed"):
        ws = create_collab_workspace("Test", pt, "owner@x.com")
        assert ws["project_type"] == pt


def test_create_collab_workspace_invalid_project_type():
    with pytest.raises(ValueError, match="project_type"):
        create_collab_workspace("Test", "podcast", "owner@x.com")


def test_create_collab_workspace_empty_name():
    with pytest.raises(ValueError, match="name"):
        create_collab_workspace("", "music", "owner@x.com")


def test_create_collab_workspace_whitespace_name():
    with pytest.raises(ValueError, match="name"):
        create_collab_workspace("   ", "music", "owner@x.com")


def test_create_collab_workspace_empty_owner():
    with pytest.raises(ValueError, match="owner"):
        create_collab_workspace("WS Name", "music", "")


def test_create_collab_workspace_no_description():
    ws = create_collab_workspace("WS", "text", "bob@x.com")
    assert ws["description"] == ""


def test_create_collab_workspace_unique_ids():
    ws1 = create_collab_workspace("WS", "music", "a@x.com")
    ws2 = create_collab_workspace("WS", "music", "a@x.com")
    assert ws1["workspace_id"] != ws2["workspace_id"]


# ---------------------------------------------------------------------------
# add_collaborator – unit tests
# ---------------------------------------------------------------------------

def test_add_collaborator_valid():
    collab = add_collaborator("ws-123", "bob@example.com", "editor")
    assert collab["workspace_id"] == "ws-123"
    assert collab["user_email"] == "bob@example.com"
    assert collab["role"] == "editor"
    assert "added_at" in collab
    assert "permissions" in collab
    assert "read" in collab["permissions"]
    assert "write" in collab["permissions"]


def test_add_collaborator_all_roles():
    for role in ("owner", "editor", "viewer", "commenter"):
        c = add_collaborator("ws-abc", "user@x.com", role)
        assert c["role"] == role
        assert isinstance(c["permissions"], list)


def test_add_collaborator_invalid_role():
    with pytest.raises(ValueError, match="role"):
        add_collaborator("ws-123", "user@x.com", "superadmin")


def test_add_collaborator_empty_workspace_id():
    with pytest.raises(ValueError, match="workspace_id"):
        add_collaborator("", "user@x.com", "viewer")


def test_add_collaborator_empty_email():
    with pytest.raises(ValueError, match="user_email"):
        add_collaborator("ws-123", "", "viewer")


# ---------------------------------------------------------------------------
# get_collab_activity – unit tests
# ---------------------------------------------------------------------------

def test_get_collab_activity_valid():
    acts = get_collab_activity("ws-abc")
    assert isinstance(acts, list)
    assert len(acts) > 0
    first = acts[0]
    assert "activity_id" in first
    assert "workspace_id" in first
    assert "user_email" in first
    assert "action" in first
    assert "timestamp" in first
    assert "details" in first


def test_get_collab_activity_with_email():
    acts = get_collab_activity("ws-abc", "carol@x.com")
    assert all(a["user_email"] == "carol@x.com" for a in acts)


def test_get_collab_activity_empty_workspace_id():
    with pytest.raises(ValueError, match="workspace_id"):
        get_collab_activity("")


# ---------------------------------------------------------------------------
# generate_collab_suggestions – unit tests
# ---------------------------------------------------------------------------

def test_generate_collab_suggestions_valid():
    s = generate_collab_suggestions("ws-999", "video", "short film")
    assert s["workspace_id"] == "ws-999"
    assert s["project_type"] == "video"
    assert isinstance(s["suggestions"], list)
    assert isinstance(s["workflow_tips"], list)
    assert isinstance(s["tools"], list)


def test_generate_collab_suggestions_context_appended():
    s = generate_collab_suggestions("ws-1", "music", "jazz fusion")
    assert any("jazz fusion" in sug for sug in s["suggestions"])


def test_generate_collab_suggestions_invalid_project_type():
    with pytest.raises(ValueError, match="project_type"):
        generate_collab_suggestions("ws-1", "podcast")


def test_generate_collab_suggestions_all_project_types():
    for pt in ("music", "visual", "video", "animation", "text", "mixed"):
        s = generate_collab_suggestions("ws-x", pt)
        assert s["project_type"] == pt


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

def test_api_create_workspace():
    resp = client.post("/collab/workspace", json={
        "name": "Art Project",
        "project_type": "visual",
        "owner": "diana@x.com",
        "description": "Collaborative mural",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Art Project"
    assert data["project_type"] == "visual"
    assert "workspace_id" in data


def test_api_create_workspace_invalid_type():
    resp = client.post("/collab/workspace", json={
        "name": "WS",
        "project_type": "podcast",
        "owner": "o@x.com",
    })
    assert resp.status_code == 422


def test_api_invite_collaborator():
    resp = client.post("/collab/workspace/ws-test-001/invite", json={
        "user_email": "eve@x.com",
        "role": "editor",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == "ws-test-001"
    assert data["user_email"] == "eve@x.com"


def test_api_invite_collaborator_invalid_role():
    resp = client.post("/collab/workspace/ws-test-001/invite", json={
        "user_email": "eve@x.com",
        "role": "godmode",
    })
    assert resp.status_code == 422


def test_api_get_workspace_activity():
    resp = client.get("/collab/workspace/ws-test-001/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert "activities" in data
    assert isinstance(data["activities"], list)


def test_api_get_workspace_activity_with_email():
    resp = client.get("/collab/workspace/ws-test-001/activity?user_email=frank@x.com")
    assert resp.status_code == 200
    data = resp.json()
    assert all(a["user_email"] == "frank@x.com" for a in data["activities"])


def test_api_collab_suggestions():
    resp = client.post("/collab/suggestions", json={
        "workspace_id": "ws-test-001",
        "project_type": "animation",
        "context": "fantasy world",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_type"] == "animation"
    assert "suggestions" in data


def test_api_collab_suggestions_invalid_type():
    resp = client.post("/collab/suggestions", json={
        "workspace_id": "ws-001",
        "project_type": "podcast",
    })
    assert resp.status_code == 422

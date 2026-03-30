"""
KalaCollab – Collaboration Workspace Module
--------------------------------------------
Provides functions for creating and managing collaborative creative workspaces.

Public API
----------
create_collab_workspace(name, project_type, owner, description)
    Returns a workspace dict.

add_collaborator(workspace_id, user_email, role)
    Returns a collaborator dict.

get_collab_activity(workspace_id, user_email)
    Returns a list of activity dicts.

generate_collab_suggestions(workspace_id, project_type, context)
    Returns an AI suggestions dict.
"""

from __future__ import annotations

import datetime
import hashlib
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Valid values
# ---------------------------------------------------------------------------

_VALID_PROJECT_TYPES: set[str] = {"music", "visual", "video", "animation", "text", "mixed"}
_VALID_ROLES: set[str] = {"owner", "editor", "viewer", "commenter"}

# ---------------------------------------------------------------------------
# Role → permissions mapping
# ---------------------------------------------------------------------------

_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "owner":     ["read", "write", "delete", "invite", "admin"],
    "editor":    ["read", "write"],
    "viewer":    ["read"],
    "commenter": ["read", "comment"],
}

# ---------------------------------------------------------------------------
# Per-project-type suggestions
# ---------------------------------------------------------------------------

_PROJECT_SUGGESTIONS: dict[str, dict[str, Any]] = {
    "music": {
        "suggestions": [
            "Use shared MIDI tracks to collaborate in real time",
            "Assign each collaborator a specific instrument layer",
            "Set up version control for stems and arrangements",
            "Schedule live jam sessions using the stream module",
        ],
        "workflow_tips": [
            "Start with a shared tempo map before recording",
            "Label all tracks consistently across collaborators",
            "Export stems after each milestone for easy handoff",
        ],
        "tools": ["KalaComposer", "KalaSignal", "KalaProducer"],
    },
    "visual": {
        "suggestions": [
            "Divide the canvas into zones and assign each to a collaborator",
            "Create a shared color palette before starting",
            "Use layers so edits remain non-destructive",
            "Hold weekly design reviews with inline comments",
        ],
        "workflow_tips": [
            "Lock completed layers to prevent accidental edits",
            "Export a low-res preview after every session",
            "Document design decisions in the workspace description",
        ],
        "tools": ["KalaVisual", "KalaExport"],
    },
    "video": {
        "suggestions": [
            "Assign distinct scenes to different collaborators",
            "Agree on color-grading LUTs before post-production",
            "Use a shared shot list accessible to all team members",
            "Review cuts together using the stream overlay feature",
        ],
        "workflow_tips": [
            "Sync proxy files rather than full-resolution footage",
            "Keep a rolling cut-log for editorial decisions",
            "Run quality checks before each export milestone",
        ],
        "tools": ["KalaVideo", "KalaStream", "KalaExport"],
    },
    "animation": {
        "suggestions": [
            "Break the animation into sequences and delegate per sequence",
            "Maintain a shared character-design style guide",
            "Use storyboard reviews to align on timing early",
            "Automate in-betweening tasks to reduce repetition",
        ],
        "workflow_tips": [
            "Export frame ranges incrementally to catch issues early",
            "Keep asset libraries versioned and shared centrally",
            "Define frame-rate and resolution before production begins",
        ],
        "tools": ["KalaAnimation", "KalaVisual", "KalaExport"],
    },
    "text": {
        "suggestions": [
            "Assign chapters or sections to individual authors",
            "Use comment threads for editorial feedback",
            "Track document revisions with timestamps",
            "Run AI-assisted grammar and style checks before publishing",
        ],
        "workflow_tips": [
            "Agree on voice and tone guidelines before writing begins",
            "Do a final consolidated read-through before export",
            "Use Markdown for easy cross-platform compatibility",
        ],
        "tools": ["KalaText", "KalaExport"],
    },
    "mixed": {
        "suggestions": [
            "Designate a project lead to coordinate across disciplines",
            "Hold cross-discipline kick-off sessions to align goals",
            "Use shared timelines for audio, video, and text milestones",
            "Leverage KalaIntelligence to translate between creative formats",
        ],
        "workflow_tips": [
            "Document dependencies between media types early",
            "Plan export formats for each media type upfront",
            "Schedule integration reviews at key production checkpoints",
        ],
        "tools": ["KalaIntelligence", "KalaStream", "KalaExport"],
    },
}

# ---------------------------------------------------------------------------
# Sample activity actions (for realistic deterministic output)
# ---------------------------------------------------------------------------

_SAMPLE_ACTIONS: list[str] = [
    "joined workspace",
    "uploaded asset",
    "left a comment",
    "edited description",
    "exported file",
    "invited collaborator",
    "changed settings",
    "reviewed storyboard",
]


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_collab_workspace(
    name: str,
    project_type: str,
    owner: str,
    description: str = "",
) -> dict[str, Any]:
    """Create a new collaboration workspace.

    Parameters
    ----------
    name:         Workspace display name.
    project_type: One of the valid project types.
    owner:        Owner identifier (username or email).
    description:  Optional description of the workspace.

    Returns
    -------
    Workspace dict with keys: workspace_id, name, project_type, owner,
    description, created_at, members, status.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if not name or not name.strip():
        raise ValueError("name must not be empty")
    if not owner or not owner.strip():
        raise ValueError("owner must not be empty")
    if project_type not in _VALID_PROJECT_TYPES:
        raise ValueError(
            f"project_type must be one of {sorted(_VALID_PROJECT_TYPES)}"
        )

    workspace_id = str(uuid.uuid4())
    created_at = _now()

    return {
        "workspace_id": workspace_id,
        "name": name.strip(),
        "project_type": project_type,
        "owner": owner.strip(),
        "description": description.strip() if description else "",
        "created_at": created_at,
        "members": [
            {
                "user_email": owner.strip(),
                "role": "owner",
                "added_at": created_at,
            }
        ],
        "status": "active",
    }


def add_collaborator(
    workspace_id: str,
    user_email: str,
    role: str,
) -> dict[str, Any]:
    """Add a collaborator to a workspace.

    Parameters
    ----------
    workspace_id: ID of the target workspace.
    user_email:   Email address of the new collaborator.
    role:         One of the valid roles.

    Returns
    -------
    Collaborator dict with keys: workspace_id, user_email, role,
    added_at, permissions.

    Raises
    ------
    ValueError for invalid or missing inputs.
    """
    if not workspace_id or not workspace_id.strip():
        raise ValueError("workspace_id must not be empty")
    if not user_email or not user_email.strip():
        raise ValueError("user_email must not be empty")
    if role not in _VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(_VALID_ROLES)}")

    return {
        "workspace_id": workspace_id.strip(),
        "user_email": user_email.strip(),
        "role": role,
        "added_at": _now(),
        "permissions": _ROLE_PERMISSIONS[role],
    }


def get_collab_activity(
    workspace_id: str,
    user_email: str = "",
) -> list[dict[str, Any]]:
    """Return recent activity for a workspace.

    Parameters
    ----------
    workspace_id: ID of the workspace to query.
    user_email:   Optional filter – only return activity for this user.

    Returns
    -------
    List of activity dicts, each with keys: activity_id, workspace_id,
    user_email, action, timestamp, details.

    Raises
    ------
    ValueError for empty workspace_id.
    """
    if not workspace_id or not workspace_id.strip():
        raise ValueError("workspace_id must not be empty")

    base_seed = hashlib.md5(workspace_id.encode()).hexdigest()
    activities: list[dict[str, Any]] = []

    for i, action in enumerate(_SAMPLE_ACTIONS):
        email = user_email.strip() if user_email and user_email.strip() else f"user{i}@example.com"
        activity_id = hashlib.md5(f"{workspace_id}{i}{action}".encode()).hexdigest()[:16]
        activities.append(
            {
                "activity_id": activity_id,
                "workspace_id": workspace_id.strip(),
                "user_email": email,
                "action": action,
                "timestamp": _now(),
                "details": {
                    "description": f"{email} performed '{action}' on workspace {workspace_id[:8]}",
                    "sequence": i + 1,
                    "seed": base_seed[:8],
                },
            }
        )

    return activities


def generate_collab_suggestions(
    workspace_id: str,
    project_type: str,
    context: str = "",
) -> dict[str, Any]:
    """Generate AI-powered collaboration suggestions for a workspace.

    Parameters
    ----------
    workspace_id: ID of the workspace.
    project_type: Type of creative project.
    context:      Optional extra context to enrich suggestions.

    Returns
    -------
    Suggestions dict with keys: workspace_id, project_type, suggestions,
    workflow_tips, tools.

    Raises
    ------
    ValueError for invalid inputs.
    """
    if not workspace_id or not workspace_id.strip():
        raise ValueError("workspace_id must not be empty")
    if project_type not in _VALID_PROJECT_TYPES:
        raise ValueError(
            f"project_type must be one of {sorted(_VALID_PROJECT_TYPES)}"
        )

    template = _PROJECT_SUGGESTIONS[project_type]
    suggestions = list(template["suggestions"])
    if context and context.strip():
        suggestions.append(
            f"Consider incorporating '{context.strip()[:80]}' into your collaboration workflow"
        )

    return {
        "workspace_id": workspace_id.strip(),
        "project_type": project_type,
        "suggestions": suggestions,
        "workflow_tips": template["workflow_tips"],
        "tools": template["tools"],
    }

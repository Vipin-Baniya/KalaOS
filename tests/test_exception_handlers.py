"""
Tests for global FastAPI exception handlers.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.fixture
def client():
    from main import app
    return TestClient(app, raise_server_exceptions=False)


def test_register_validation_error_response_format(client):
    resp = client.post("/auth/register", json={})

    assert resp.status_code == 422

    data = resp.json()

    assert data["success"] is False
    assert data["detail"] == "Invalid request"

    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "Invalid request"
    assert isinstance(data["error"]["details"], list)

    assert len(data["error"]["details"]) >= 2

    missing_fields = {
        tuple(error["loc"])
        for error in data["error"]["details"]
    }

    assert ("body", "email") in missing_fields
    assert ("body", "password") in missing_fields

    assert "request_id" in data
    assert isinstance(data["request_id"], (str, type(None)))


def test_register_http_error_response_format(client):
    resp = client.post("/auth/register", json={
        "email": "",
        "password": "securepassword",
        "name": "Test Artist",
    })

    assert resp.status_code == 400

    data = resp.json()

    assert data["success"] is False
    assert data["detail"] == "Invalid email address."

    assert data["error"]["code"] == "HTTP_ERROR"
    assert data["error"]["message"] == "Invalid email address."
    assert data["error"]["details"] == "Invalid email address."

    assert "request_id" in data
    assert isinstance(data["request_id"], (str, type(None)))


def test_login_validation_error_response_format(client):
    resp = client.post("/auth/login", json={})

    assert resp.status_code == 422

    data = resp.json()

    assert data["success"] is False
    assert data["detail"] == "Invalid request"

    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "Invalid request"
    assert isinstance(data["error"]["details"], list)

    missing_fields = {
        tuple(error["loc"])
        for error in data["error"]["details"]
    }

    assert ("body", "email") in missing_fields
    assert ("body", "password") in missing_fields

    assert "request_id" in data
    assert isinstance(data["request_id"], (str, type(None)))

def test_login_http_error_response_format(client):
    resp = client.post("/auth/login", json={
        "email": "unknown@example.com",
        "password": "password123",
    })

    assert resp.status_code == 401

    data = resp.json()

    assert data["success"] is False
    assert data["detail"] == "Invalid email or password."

    assert data["error"]["code"] == "HTTP_ERROR"
    assert data["error"]["message"] == "Invalid email or password."
    assert data["error"]["details"] == "Invalid email or password."

    assert "request_id" in data
    assert isinstance(data["request_id"], (str, type(None)))

def test_unhandled_exception_response_format(client):
    from main import app

    @app.get("/test-unhandled-error")
    async def test_unhandled_error():
        raise RuntimeError("database crashed")

    response = client.get(
        "/test-unhandled-error"
    )

    assert response.status_code == 500

    body = response.json()

    assert body["success"] is False
    assert body["detail"] == "An unexpected error occurred."
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert body["error"]["details"] == []
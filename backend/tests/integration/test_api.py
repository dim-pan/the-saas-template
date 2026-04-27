"""Integration tests for FastAPI endpoints."""

from uuid import uuid4

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_root() -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == 'Hello world!'


def test_users_endpoint_requires_auth() -> None:
    response = client.get(f'/api/v1/org/{uuid4()}/users/{uuid4()}')
    assert response.status_code == 401


def test_organizations_endpoint_requires_auth() -> None:
    response = client.get('/api/v1/org')
    assert response.status_code == 401


def test_memberships_endpoint_requires_auth() -> None:
    response = client.get(f'/api/v1/org/{uuid4()}/memberships')
    assert response.status_code == 401

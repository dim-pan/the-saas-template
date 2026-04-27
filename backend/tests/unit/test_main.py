"""Unit tests for app.main."""

from app.main import app
from fastapi.testclient import TestClient


def test_root_returns_hello_world() -> None:
    client = TestClient(app)
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == 'Hello world!'

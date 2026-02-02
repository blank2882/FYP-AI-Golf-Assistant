from fastapi.testclient import TestClient

from app.main import app


def test_index_route():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "AI Golf Assistant" in resp.text

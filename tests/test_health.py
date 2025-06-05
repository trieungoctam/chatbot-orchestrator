from fastapi.testclient import TestClient

from app.main import app


def test_health_check():
    """Test the health check endpoint returns status 'ok'."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"} 
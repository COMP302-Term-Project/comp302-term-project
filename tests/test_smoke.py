from app.main import app


def test_app_exists():
    assert app is not None


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["ok"] is True
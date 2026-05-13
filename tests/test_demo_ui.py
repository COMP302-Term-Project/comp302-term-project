from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FORBIDDEN_FRONTEND_TOKENS = [
    "SUPABASE_SERVICE_ROLE_KEY",
    "DATABASE_URL",
    "OPENROUTER_API_KEY",
    "eyJhbGci",
    "sk-or-",
    "postgres://",
]


def test_fastapi_app_imports_successfully():
    from app.main import app

    assert app is not None


def test_get_ui_returns_html():
    from app.main import app

    client = TestClient(app)
    response = client.get("/ui")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "InClass Platform Demo UI" in response.text


def test_frontend_files_exist():
    assert (FRONTEND_DIR / "index.html").exists()
    assert (FRONTEND_DIR / "styles.css").exists()
    assert (FRONTEND_DIR / "app.js").exists()


def test_frontend_files_do_not_contain_obvious_secrets():
    combined = "\n".join(
        (FRONTEND_DIR / filename).read_text(encoding="utf-8")
        for filename in ["index.html", "styles.css", "app.js"]
    )

    for token in FORBIDDEN_FRONTEND_TOKENS:
        assert token not in combined


def test_frontend_html_mentions_key_demo_sections():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    for section in ["Instructor Panel", "Student Panel", "Demo Flow", "Negative Tests"]:
        assert section in html

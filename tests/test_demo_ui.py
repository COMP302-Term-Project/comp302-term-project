from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FORBIDDEN_FRONTEND_TOKENS = [
    "SUPABASE" + "_SERVICE" + "_ROLE" + "_KEY",
    "DATABASE" + "_URL",
    "OPENROUTER" + "_API" + "_KEY",
    "eyJ" + "hbGci",
    "sk" + "-or" + "-",
    "postgres" + "://",
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
    assert "InClass Platform" in response.text


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

    for section in [
        "Instructor Dashboard",
        "AI Tutor",
        "Student support",
        "Demo Flow",
        "Auth Tests",
        "Evidence Log",
        "Seed demo data",
        "Reset demo data",
    ]:
        assert section in html


def test_demo_flow_uses_deterministic_tutoring_answer():
    app_js = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")

    assert "demoSubmitTutoringAnswer" in app_js
    assert "/student/submit-tutoring-answer" in app_js
    assert "Can you guide me through this activity one question at a time?" in app_js
    assert "Active retrieval practice is better than rereading" in app_js
    assert "Initialize tutoring flow" in app_js
    assert "Submit scoring answer" in app_js
    assert "tutoringScore" in app_js


def test_demo_flow_exports_after_manual_grade():
    app_js = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")

    assert app_js.index('"Manual grade"') < app_js.index('"Export scores"')

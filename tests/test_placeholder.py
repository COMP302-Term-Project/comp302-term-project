def test_import_main_app():
    """Smoke test so `tests/` is tracked and pytest has a baseline."""
    from app.main import app

    assert app is not None

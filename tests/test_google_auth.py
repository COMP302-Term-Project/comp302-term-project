from unittest.mock import patch

from app import services
from tests.fake_supabase import FakeDB


def _student_row(email="student@test.com"):
    return {
        "id": 9,
        "email": email,
        "full_name": "Test Student",
        "password": "secure123",
    }


def _instructor_row(email="instructor@test.com"):
    return {
        "id": 7,
        "email": email,
        "full_name": "Test Instructor",
        "password": "secure123",
    }


def _course_row():
    return {"id": 101, "course_id": "CS101", "course_name": "Intro CS"}


def _activity_row():
    return {
        "id": 33,
        "course_id": 101,
        "activity_no": 1,
        "activity_text": "Solve the warmup problem",
        "learning_objectives": ["Hidden instructor objective"],
        "status": "ACTIVE",
    }


def _mock_google_token(email):
    return {"ok": True, "email": email, "token_info": {"email": email, "email_verified": True}}


def test_google_login_route_accepts_id_token_json(client, monkeypatch):
    expected = {
        "ok": True,
        "role": "student",
        "email": "student@test.com",
        "user": {"email": "student@test.com"},
        "session_token": "google_session.fake.signature",
    }

    def fake_google_login(id_token=None, role=None):
        assert id_token == "google-id-token"
        assert role == "student"
        return expected

    monkeypatch.setattr(services, "googleLogin", fake_google_login)

    response = client.post(
        "/auth/google-login",
        json={"id_token": "google-id-token", "role": "student"},
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_google_login_route_accepts_google_gis_credential(client, monkeypatch):
    expected = {"ok": False, "error": "Invalid Google ID token"}

    def fake_google_login(id_token=None, role=None):
        assert id_token == "google-gis-credential"
        assert role is None
        return expected

    monkeypatch.setattr(services, "googleLogin", fake_google_login)

    response = client.post(
        "/auth/google-login",
        json={"credential": "google-gis-credential"},
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_google_login_returns_student_session_for_mapped_email(monkeypatch):
    fake_db = FakeDB(students=[_student_row()])
    monkeypatch.setenv("GOOGLE_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setattr(services, "_verify_google_id_token", lambda token: _mock_google_token(" Student@Test.com "))
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.googleLogin("valid-token", role="student")

    assert response["ok"] is True
    assert response["role"] == "student"
    assert response["email"] == "student@test.com"
    assert response["user"] == {
        "id": 9,
        "email": "student@test.com",
        "full_name": "Test Student",
    }
    assert response["session_token"].startswith("google_session.")


def test_google_login_returns_instructor_session_for_mapped_email(monkeypatch):
    fake_db = FakeDB(instructors=[_instructor_row()])
    monkeypatch.setenv("GOOGLE_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setattr(services, "_verify_google_id_token", lambda token: _mock_google_token("instructor@test.com"))
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.googleLogin("valid-token", role="instructor")

    assert response["ok"] is True
    assert response["role"] == "instructor"
    assert response["email"] == "instructor@test.com"
    assert response["user"] == {
        "id": 7,
        "email": "instructor@test.com",
        "full_name": "Test Instructor",
    }
    assert response["session_token"].startswith("google_session.")


def test_google_login_rejects_unmapped_email(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setenv("GOOGLE_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setattr(services, "_verify_google_id_token", lambda token: _mock_google_token("missing@test.com"))
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.googleLogin("valid-token")

    assert response == {"ok": False, "error": "Google identity is not mapped to a user account"}


def test_google_login_rejects_invalid_google_token(monkeypatch):
    monkeypatch.setattr(
        services,
        "_verify_google_id_token",
        lambda token: {"ok": False, "error": "Invalid Google ID token"},
    )

    response = services.googleLogin("invalid-token")

    assert response == {"ok": False, "error": "Invalid Google ID token"}


def test_google_login_requires_role_for_ambiguous_email(monkeypatch):
    fake_db = FakeDB(
        students=[_student_row(email="shared@test.com")],
        instructors=[_instructor_row(email="shared@test.com")],
    )
    monkeypatch.setenv("GOOGLE_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setattr(services, "_verify_google_id_token", lambda token: _mock_google_token("shared@test.com"))
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.googleLogin("valid-token")

    assert response == {"ok": False, "error": "Google identity maps to multiple roles; role is required"}


def test_google_login_rejects_requested_role_mismatch(monkeypatch):
    fake_db = FakeDB(students=[_student_row(email="student@test.com")])
    monkeypatch.setenv("GOOGLE_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setattr(services, "_verify_google_id_token", lambda token: _mock_google_token("student@test.com"))
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.googleLogin("valid-token", role="instructor")

    assert response == {"ok": False, "error": "Google identity is not mapped to an instructor account"}


def test_student_google_session_can_access_existing_student_endpoint(monkeypatch):
    fake_db = FakeDB(
        students=[_student_row()],
        courses=[_course_row()],
        student_courses=[{"id": 1, "student_id": 9, "course_id": 101}],
        activities=[_activity_row()],
    )
    monkeypatch.setenv("GOOGLE_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setattr(services, "_verify_google_id_token", lambda token: _mock_google_token("student@test.com"))
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    login = services.googleLogin("valid-token", role="student")
    response = services.getActivity("student@test.com", login["session_token"], "CS101", 1)

    assert response == {
        "ok": True,
        "activity": {
            "course_id": 101,
            "activity_no": 1,
            "activity_text": "Solve the warmup problem",
        },
    }


def test_instructor_google_session_can_access_existing_instructor_endpoint(monkeypatch):
    fake_db = FakeDB(
        instructors=[_instructor_row()],
        courses=[_course_row()],
        instructor_courses=[{"id": 1, "instructor_id": 7, "course_id": 101}],
    )
    monkeypatch.setenv("GOOGLE_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setattr(services, "_verify_google_id_token", lambda token: _mock_google_token("instructor@test.com"))
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    login = services.googleLogin("valid-token", role="instructor")
    response = services.listMyCourses("instructor@test.com", login["session_token"])

    assert response == {
        "ok": True,
        "courses": [{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
    }


def test_student_google_session_cannot_authorize_instructor_endpoint(monkeypatch):
    fake_db = FakeDB(
        students=[_student_row(email="shared@test.com")],
        instructors=[_instructor_row(email="shared@test.com")],
    )
    monkeypatch.setenv("GOOGLE_AUTH_SESSION_SECRET", "test-secret")
    token = services._issue_google_session_token("shared@test.com", "student")

    with patch("app.services.get_db", return_value=fake_db):
        response = services.listMyCourses("shared@test.com", token)

    assert response == {"ok": False, "error": "Invalid credentials"}


def test_instructor_google_session_cannot_authorize_student_endpoint(monkeypatch):
    fake_db = FakeDB(
        students=[_student_row(email="shared@test.com")],
        instructors=[_instructor_row(email="shared@test.com")],
    )
    monkeypatch.setenv("GOOGLE_AUTH_SESSION_SECRET", "test-secret")
    token = services._issue_google_session_token("shared@test.com", "instructor")

    with patch("app.services.get_db", return_value=fake_db):
        response = services.getActivity("shared@test.com", token, "CS101", 1)

    assert response == {"ok": False, "error": "Invalid credentials"}

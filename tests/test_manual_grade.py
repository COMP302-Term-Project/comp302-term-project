from unittest.mock import patch

from tests.fake_supabase import FakeDB


def make_db(activity_rows=None, mappings=None):
    return FakeDB(
        instructors=[{
            "id": 7,
            "email": "test@test.com",
            "full_name": "Test Instructor",
            "password": "secure123",
        }],
        courses=[{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
        instructor_courses=mappings if mappings is not None else [{"id": 1, "instructor_id": 7, "course_id": 101}],
        activities=activity_rows or [],
    )


def test_manual_grade_success(client):
    fake_db = make_db(activity_rows=[{
        "id": 55,
        "course_id": 101,
        "activity_no": 1,
        "status": "ACTIVE",
    }])

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/manual-grade",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "student_id": 42,
                "activity_no": 1,
                "score": 5.0,
                "reason": "Great answer",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "Manual grade logged successfully"}
    assert fake_db.rpc_calls == [{
        "fn": "log_manual_grade",
        "params": {
            "p_student_id": 42,
            "p_activity_id": 55,
            "p_instructor_id": 7,
            "p_score": 5.0,
            "p_reason": "Great answer",
        }
    }]


def test_manual_grade_activity_not_active(client):
    fake_db = make_db(activity_rows=[{
        "id": 55, "course_id": 101, "activity_no": 1, "status": "NOT_STARTED"
    }])

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/manual-grade",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "student_id": 42,
                "activity_no": 1,
                "score": 5.0,
                "reason": "Great answer",
            },
        )

    assert response.json() == {"ok": False, "error": "Activity is not active"}


def test_manual_grade_activity_not_found(client):
    fake_db = make_db(activity_rows=[])

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/manual-grade",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "student_id": 42,
                "activity_no": 999,
                "score": 5.0,
                "reason": "Great answer",
            },
        )

    assert response.json() == {"ok": False, "error": "Activity does not exist"}


def test_manual_grade_invalid_score(client):
    fake_db = make_db(activity_rows=[{
        "id": 55, "course_id": 101, "activity_no": 1, "status": "ACTIVE"
    }])

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/manual-grade",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "student_id": 42,
                "activity_no": 1,
                "score": -1.0,
                "reason": "Great answer",
            },
        )

    assert response.json() == {"ok": False, "error": "Score must be positive"}


def test_manual_grade_missing_reason(client):
    fake_db = make_db(activity_rows=[{
        "id": 55, "course_id": 101, "activity_no": 1, "status": "ACTIVE"
    }])

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/manual-grade",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "student_id": 42,
                "activity_no": 1,
                "score": 5.0,
                "reason": "",
            },
        )

    assert response.json() == {"ok": False, "error": "reason is required"}


def test_manual_grade_unauthorized(client):
    fake_db = make_db(mappings=[])

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/manual-grade",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "student_id": 42,
                "activity_no": 1,
                "score": 5.0,
                "reason": "Great answer",
            },
        )

    assert response.json() == {"ok": False, "error": "Unauthorized"}
    
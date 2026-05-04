from unittest.mock import patch

from app.services import getActivity
from tests.fake_supabase import FakeDB


def _student_row():
    return {
        "id": 9,
        "email": "student@test.com",
        "full_name": "Test Student",
        "password": "secure123",
    }


def _course_row():
    return {"id": 101, "course_id": "CS101", "course_name": "Intro CS"}


def _activity_row(status="ACTIVE", activity_no=1):
    return {
        "id": 33,
        "course_id": 101,
        "activity_no": activity_no,
        "activity_text": "Solve the warmup problem",
        "learning_objectives": ["Hidden instructor objective"],
        "status": status,
    }


def _authorized_student_db(activity_rows=None):
    return FakeDB(
        students=[_student_row()],
        courses=[_course_row()],
        student_courses=[{"id": 1, "student_id": 9, "course_id": 101}],
        activities=activity_rows or [],
    )


def test_get_activity_active_returns_only_student_visible_payload():
    fake_db = _authorized_student_db(activity_rows=[_activity_row(status="ACTIVE")])

    with patch("app.services.get_db", return_value=fake_db):
        response = getActivity("student@test.com", "secure123", "CS101", 1)

    assert response == {
        "ok": True,
        "activity": {
            "course_id": 101,
            "activity_no": 1,
            "activity_text": "Solve the warmup problem",
        },
    }
    assert set(response["activity"]) == {"course_id", "activity_no", "activity_text"}
    assert "learning_objectives" not in response["activity"]
    assert "id" not in response["activity"]
    assert "status" not in response["activity"]


def test_get_activity_rejects_non_active_statuses():
    for status in ["NOT_STARTED", "ENDED"]:
        fake_db = _authorized_student_db(activity_rows=[_activity_row(status=status)])

        with patch("app.services.get_db", return_value=fake_db):
            response = getActivity("student@test.com", "secure123", "CS101", 1)

        assert response == {"ok": False, "error": "Activity is not active"}


def test_get_activity_rejects_non_enrolled_student():
    fake_db = FakeDB(
        students=[_student_row()],
        courses=[_course_row()],
        student_courses=[],
        activities=[_activity_row(status="ACTIVE")],
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = getActivity("student@test.com", "secure123", "CS101", 1)

    assert response == {"ok": False, "error": "Unauthorized"}


def test_get_activity_rejects_missing_activity():
    fake_db = _authorized_student_db(activity_rows=[_activity_row(status="ACTIVE", activity_no=2)])

    with patch("app.services.get_db", return_value=fake_db):
        response = getActivity("student@test.com", "secure123", "CS101", 1)

    assert response == {"ok": False, "error": "Activity does not exist"}

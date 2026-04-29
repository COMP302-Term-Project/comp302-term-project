from unittest.mock import patch

from app.services import listActivities
from tests.fake_supabase import FakeDB


def test_list_activities_course_scoping_unauthorized():
    fake_db = FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "test@test.com",
                "full_name": "Test Instructor",
                "password": "password123",
            }
        ],
        courses=[{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
        instructor_courses=[{"id": 1, "instructor_id": 8, "course_id": 101}],
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = listActivities("test@test.com", "password123", "CS101")

    assert response == {"ok": False, "error": "Unauthorized"}


def test_list_activities_ordering_uses_internal_course_id():
    fake_db = FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "test@test.com",
                "full_name": "Test Instructor",
                "password": "password123",
            }
        ],
        courses=[{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
        instructor_courses=[{"id": 1, "instructor_id": 7, "course_id": 101}],
        activities=[
            {"id": 3, "activity_no": 3, "course_id": 101, "activity_text": "Task 3", "status": "NOT_STARTED"},
            {"id": 1, "activity_no": 1, "course_id": 101, "activity_text": "Task 1", "status": "NOT_STARTED"},
            {"id": 2, "activity_no": 2, "course_id": 101, "activity_text": "Task 2", "status": "NOT_STARTED"},
            {"id": 4, "activity_no": 1, "course_id": 202, "activity_text": "Other course", "status": "ACTIVE"},
        ],
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = listActivities("test@test.com", "password123", "CS101")

    assert response["ok"] is True
    activities = response["activities"]
    assert [activity["activity_no"] for activity in activities] == [1, 2, 3]
    assert [activity["status"] for activity in activities] == ["NOT_STARTED", "NOT_STARTED", "NOT_STARTED"]
    assert all(activity["course_id"] == 101 for activity in activities)


def test_list_activities_course_not_found():
    fake_db = FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "test@test.com",
                "full_name": "Test Instructor",
                "password": "password123",
            }
        ],
        courses=[],
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = listActivities("test@test.com", "password123", "CS101")

    assert response == {"ok": False, "error": "Course not found"}

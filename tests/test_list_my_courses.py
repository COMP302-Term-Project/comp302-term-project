from unittest.mock import patch

from app.services import listMyCourses
from tests.fake_supabase import FakeDB


def test_list_my_courses_success():
    fake_db = FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "test@test.com",
                "full_name": "Test Instructor",
                "password": "secure123",
            }
        ],
        courses=[
            {"id": 101, "course_id": "CS101", "course_name": "Intro CS"},
            {"id": 202, "course_id": "MATH202", "course_name": "Math"},
        ],
        instructor_courses=[{"id": 1, "instructor_id": 7, "course_id": 101}],
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = listMyCourses(" Test@Test.com ", "secure123")

    assert response == {
        "ok": True,
        "courses": [{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
    }


def test_list_my_courses_invalid_password():
    fake_db = FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "test@test.com",
                "full_name": "Test Instructor",
                "password": "secure123",
            }
        ],
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = listMyCourses("test@test.com", "wrongpassword")

    assert response == {"ok": False, "error": "Invalid credentials"}


def test_list_my_courses_user_not_found():
    fake_db = FakeDB(instructors=[])

    with patch("app.services.get_db", return_value=fake_db):
        response = listMyCourses("unknown@test.com", "password")

    assert response == {"ok": False, "error": "Invalid credentials"}

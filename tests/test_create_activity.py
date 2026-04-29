from unittest.mock import patch

from app.services import createActivity
from tests.fake_supabase import FakeDB


def test_create_activity_success_auto_increment_uses_internal_course_id():
    fake_db = FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "test@test.com",
                "full_name": "Test Instructor",
                "password": "secure123",
            }
        ],
        courses=[{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
        instructor_courses=[{"id": 1, "instructor_id": 7, "course_id": 101}],
        activities=[
            {"id": 1, "course_id": 101, "activity_no": 1, "activity_text": "Old Activity", "status": "ENDED"},
            {"id": 2, "course_id": 202, "activity_no": 5, "activity_text": "Other Course", "status": "ACTIVE"},
        ],
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = createActivity(
            email="test@test.com",
            password="secure123",
            course_id="CS101",
            activity_text="New Activity",
            learning_objectives=["Obj 1"],
        )

    assert response["ok"] is True
    assert response["activity"] == {
        "course_id": 101,
        "activity_no": 2,
        "activity_text": "New Activity",
        "learning_objectives": ["Obj 1"],
    }
    assert fake_db.inserts == [{"table": "activities", "data": response["activity"]}]


def test_create_activity_success_uses_optional_activity_no():
    fake_db = FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "test@test.com",
                "full_name": "Test Instructor",
                "password": "secure123",
            }
        ],
        courses=[{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
        instructor_courses=[{"id": 1, "instructor_id": 7, "course_id": 101}],
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = createActivity(
            email="test@test.com",
            password="secure123",
            course_id="CS101",
            activity_text="New Activity",
            learning_objectives=["Obj 1"],
            activity_no_optional=9,
        )

    assert response["ok"] is True
    assert response["activity"]["course_id"] == 101
    assert response["activity"]["activity_no"] == 9


def test_create_activity_invalid_credentials():
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
        response = createActivity(
            email="test@test.com",
            password="wrong",
            course_id="CS101",
            activity_text="text",
            learning_objectives=["Obj 1"],
        )

    assert response == {"ok": False, "error": "Invalid credentials"}


def test_create_activity_unauthorized_course():
    fake_db = FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "test@test.com",
                "full_name": "Test Instructor",
                "password": "secure123",
            }
        ],
        courses=[{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
        instructor_courses=[],
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = createActivity(
            email="test@test.com",
            password="secure123",
            course_id="CS101",
            activity_text="text",
            learning_objectives=["Obj 1"],
        )

    assert response == {"ok": False, "error": "Unauthorized"}


def test_create_activity_rejects_blank_activity_text():
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
        response = createActivity(
            email="test@test.com",
            password="secure123",
            course_id="CS101",
            activity_text=" ",
            learning_objectives=["Obj 1"],
        )

    assert response == {"ok": False, "error": "activity_text is required"}


def test_create_activity_rejects_empty_learning_objectives():
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
        response = createActivity(
            email="test@test.com",
            password="secure123",
            course_id="CS101",
            activity_text="text",
            learning_objectives=[],
        )

    assert response == {"ok": False, "error": "learning_objectives must be a non-empty list"}


def test_create_activity_rejects_blank_learning_objective():
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
        response = createActivity(
            email="test@test.com",
            password="secure123",
            course_id="CS101",
            activity_text="text",
            learning_objectives=["Obj 1", ""],
        )

    assert response == {"ok": False, "error": "learning_objectives must be a non-empty list"}


def test_create_activity_rejects_duplicate_activity_number():
    fake_db = FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "test@test.com",
                "full_name": "Test Instructor",
                "password": "secure123",
            }
        ],
        courses=[{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
        instructor_courses=[{"id": 1, "instructor_id": 7, "course_id": 101}],
        activities=[{"id": 1, "course_id": 101, "activity_no": 3, "activity_text": "Old", "status": "NOT_STARTED"}],
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = createActivity(
            email="test@test.com",
            password="secure123",
            course_id="CS101",
            activity_text="text",
            learning_objectives=["Obj 1"],
            activity_no_optional=3,
        )

    assert response == {"ok": False, "error": "Activity number already exists"}
    assert fake_db.inserts == []


def test_create_activity_rejects_invalid_optional_activity_number():
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
        response = createActivity(
            email="test@test.com",
            password="secure123",
            course_id="CS101",
            activity_text="text",
            learning_objectives=["Obj 1"],
            activity_no_optional=0,
        )

    assert response == {"ok": False, "error": "activity_no_optional must be a positive integer"}

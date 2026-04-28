from unittest.mock import patch

from tests.fake_supabase import FakeDB


def make_instructor_activity_db(activity_rows=None, mappings=None):
    return FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "test@test.com",
                "full_name": "Test Instructor",
                "password": "secure123",
            }
        ],
        courses=[{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
        instructor_courses=mappings if mappings is not None else [{"id": 1, "instructor_id": 7, "course_id": 101}],
        activities=activity_rows or [],
    )


def test_update_activity_success(client):
    fake_db = make_instructor_activity_db(
        activity_rows=[
            {
                "id": 1,
                "course_id": 101,
                "activity_no": 1,
                "activity_text": "Original text",
                "learning_objectives": ["Old"],
                "status": "NOT_STARTED",
            }
        ]
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/update-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
            },
            json={"activity_text": "Updated text"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "Activity updated"}
    assert fake_db.tables["activities"][0]["activity_text"] == "Updated text"
    assert fake_db.updates == [
        {
            "table": "activities",
            "filters": {"course_id": 101, "activity_no": 1},
            "data": {"activity_text": "Updated text"},
        }
    ]


def test_update_activity_already_started(client):
    fake_db = make_instructor_activity_db(
        activity_rows=[{"id": 1, "course_id": 101, "activity_no": 1, "status": "ACTIVE"}]
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/update-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
            },
            json={"activity_text": "Updated text"},
        )

    assert response.json() == {
        "ok": False,
        "error": "Cannot update activity that has started or ended",
    }
    assert fake_db.updates == []


def test_update_activity_empty_patch(client):
    fake_db = make_instructor_activity_db()

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/update-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
            },
            json={},
        )

    assert response.json() == {"ok": False, "error": "Empty patch rejected"}


def test_update_activity_unauthorized_course(client):
    fake_db = make_instructor_activity_db(mappings=[])

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/update-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
            },
            json={"activity_text": "text"},
        )

    assert response.json() == {"ok": False, "error": "Unauthorized"}


def test_update_activity_not_found(client):
    fake_db = make_instructor_activity_db(activity_rows=[])

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/update-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 999,
            },
            json={"activity_text": "text"},
        )

    assert response.json() == {"ok": False, "error": "Activity does not exist"}


def test_update_activity_unallowed_fields(client):
    fake_db = make_instructor_activity_db(
        activity_rows=[{"id": 1, "course_id": 101, "activity_no": 1, "status": "NOT_STARTED"}]
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/update-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
            },
            json={"status": "ACTIVE"},
        )

    assert response.json() == {"ok": False, "error": "No allowed fields in patch"}

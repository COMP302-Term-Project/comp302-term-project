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


def test_start_activity_success(client):
    fake_db = make_instructor_activity_db(
        activity_rows=[{"id": 1, "course_id": 101, "activity_no": 1, "status": "NOT_STARTED"}]
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/start-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "Activity state changed to ACTIVE"}
    assert fake_db.tables["activities"][0]["status"] == "ACTIVE"
    assert fake_db.updates == [
        {
            "table": "activities",
            "filters": {"course_id": 101, "activity_no": 1},
            "data": {"status": "ACTIVE"},
        }
    ]


def test_start_activity_invalid_status(client):
    fake_db = make_instructor_activity_db(
        activity_rows=[{"id": 1, "course_id": 101, "activity_no": 1, "status": "ACTIVE"}]
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/start-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "error": "Invalid state transition from ACTIVE to ACTIVE",
    }
    assert fake_db.updates == []


def test_end_activity_success(client):
    fake_db = make_instructor_activity_db(
        activity_rows=[{"id": 1, "course_id": 101, "activity_no": 1, "status": "ACTIVE"}]
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/end-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "Activity state changed to ENDED"}
    assert fake_db.tables["activities"][0]["status"] == "ENDED"
    assert fake_db.updates == [
        {
            "table": "activities",
            "filters": {"course_id": 101, "activity_no": 1},
            "data": {"status": "ENDED"},
        }
    ]


def test_end_activity_invalid_status(client):
    fake_db = make_instructor_activity_db(
        activity_rows=[{"id": 1, "course_id": 101, "activity_no": 1, "status": "NOT_STARTED"}]
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/end-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "error": "Invalid state transition from NOT_STARTED to ENDED",
    }
    assert fake_db.updates == []


def test_start_activity_not_found(client):
    fake_db = make_instructor_activity_db(activity_rows=[])

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/start-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 999,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "Activity does not exist"}


def test_start_activity_unauthorized(client):
    fake_db = make_instructor_activity_db(mappings=[])

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post(
            "/instructor/start-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "Unauthorized"}

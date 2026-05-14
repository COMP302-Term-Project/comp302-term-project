from unittest.mock import patch

from app.services import logScore
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
        score_logs=[]
    )


def test_log_score_success():
    fake_db = _authorized_student_db(activity_rows=[_activity_row(status="ACTIVE")])

    with patch("app.services.get_db", return_value=fake_db):
        response = logScore(
            email="student@test.com", 
            password="secure123", 
            course_id="CS101", 
            activity_no=1, 
            score=1.0, 
            meta="Hidden instructor objective"
        )

    assert response["ok"] is True
    assert "score_log" in response
    assert response["score_log"]["student_id"] == 9
    assert response["score_log"]["course_id"] == 101
    assert response["score_log"]["activity_no"] == 1
    assert response["score_log"]["score"] == 1.0
    assert response["score_log"]["meta"] == "Hidden instructor objective"
    
    # Verify it was inserted in fake_db
    assert len(fake_db.tables["score_logs"]) == 1
    saved_score = fake_db.tables["score_logs"][0]
    assert saved_score["score"] == 1.0
    assert saved_score["meta"] == "Hidden instructor objective"


def test_log_score_duplicate_meta_returns_existing_score_without_insert():
    fake_db = _authorized_student_db(activity_rows=[_activity_row(status="ACTIVE")])
    fake_db.tables["score_logs"] = [{
        "id": 1,
        "student_id": 9,
        "course_id": 101,
        "activity_no": 1,
        "score": 1.0,
        "meta": "Hidden Instructor Objective",
    }]

    with patch("app.services.get_db", return_value=fake_db):
        response = logScore(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            score=1.0,
            meta=" hidden   instructor  objective ",
        )

    assert response == {"ok": True, "score_log": fake_db.tables["score_logs"][0], "duplicate": True}
    assert len(fake_db.tables["score_logs"]) == 1


def test_log_score_invalid_score():
    fake_db = _authorized_student_db(activity_rows=[_activity_row(status="ACTIVE")])

    with patch("app.services.get_db", return_value=fake_db):
        response = logScore(
            email="student@test.com", 
            password="secure123", 
            course_id="CS101", 
            activity_no=1, 
            score=-1.0, 
            meta="Hidden instructor objective"
        )

    assert response == {"ok": False, "error": "Score must be positive"}
    assert len(fake_db.tables["score_logs"]) == 0


def test_log_score_rejects_non_objective_increment():
    fake_db = _authorized_student_db(activity_rows=[_activity_row(status="ACTIVE")])

    with patch("app.services.get_db", return_value=fake_db):
        response = logScore(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            score=2.0,
            meta="Hidden instructor objective"
        )

    assert response == {"ok": False, "error": "Objective score must be exactly 1"}
    assert len(fake_db.tables["score_logs"]) == 0


def test_log_score_requires_meta():
    fake_db = _authorized_student_db(activity_rows=[_activity_row(status="ACTIVE")])

    with patch("app.services.get_db", return_value=fake_db):
        response = logScore(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            score=1.0,
            meta=""
        )

    assert response == {"ok": False, "error": "meta is required"}
    assert len(fake_db.tables["score_logs"]) == 0


def test_log_score_rejects_meta_outside_activity_objectives():
    fake_db = _authorized_student_db(activity_rows=[_activity_row(status="ACTIVE")])

    with patch("app.services.get_db", return_value=fake_db):
        response = logScore(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            score=1.0,
            meta="Unrelated extra concept",
        )

    assert response == {"ok": False, "error": "meta must match an activity learning objective"}
    assert len(fake_db.tables["score_logs"]) == 0


def test_log_score_returns_duplicate_after_objective_is_already_scored():
    fake_db = _authorized_student_db(
        activity_rows=[
            {
                **_activity_row(status="ACTIVE"),
                "learning_objectives": ["First objective"],
            }
        ]
    )
    fake_db.tables["score_logs"] = [
        {
            "id": 1,
            "student_id": 9,
            "course_id": 101,
            "activity_no": 1,
            "score": 1.0,
            "meta": "First objective",
        }
    ]

    with patch("app.services.get_db", return_value=fake_db):
        response = logScore(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            score=1.0,
            meta="First objective",
        )

    assert response == {"ok": True, "score_log": fake_db.tables["score_logs"][0], "duplicate": True}
    assert len(fake_db.tables["score_logs"]) == 1


def test_log_score_inactive_activity():
    fake_db = _authorized_student_db(activity_rows=[_activity_row(status="NOT_STARTED")])

    with patch("app.services.get_db", return_value=fake_db):
        response = logScore(
            email="student@test.com", 
            password="secure123", 
            course_id="CS101", 
            activity_no=1, 
            score=1.0, 
            meta="learned_objective"
        )

    assert response == {"ok": False, "error": "Activity is not active"}
    assert len(fake_db.tables["score_logs"]) == 0


def test_log_score_unauthorized_student():
    fake_db = FakeDB(
        students=[_student_row()],
        courses=[_course_row()],
        student_courses=[], # Not enrolled
        activities=[_activity_row(status="ACTIVE")],
        score_logs=[]
    )

    with patch("app.services.get_db", return_value=fake_db):
        response = logScore(
            email="student@test.com", 
            password="secure123", 
            course_id="CS101", 
            activity_no=1, 
            score=1.0, 
            meta="learned_objective"
        )

    assert response == {"ok": False, "error": "Unauthorized"}
    assert len(fake_db.tables["score_logs"]) == 0

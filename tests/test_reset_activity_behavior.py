from app import services
from tests.fake_supabase import FakeDB


def _reset_params(activity_no=1):
    return {
        "email": "instructor@test.com",
        "password": "secure123",
        "course_id": "CS101",
        "activity_no": activity_no,
    }


def _runtime_rows(activity_no=1):
    score_logs = [
        {"id": 1, "student_id": 11, "course_id": 101, "activity_no": activity_no, "score": 1.0, "meta": "target"},
        {"id": 2, "student_id": 12, "course_id": 101, "activity_no": activity_no + 1, "score": 1.0, "meta": "other activity"},
        {"id": 3, "student_id": 13, "course_id": 202, "activity_no": activity_no, "score": 1.0, "meta": "other course"},
    ]
    conversation_state = [
        {
            "id": 1,
            "student_id": 11,
            "course_id": 101,
            "activity_no": activity_no,
            "conversation_history": [{"role": "assistant", "content": "target"}],
        },
        {
            "id": 2,
            "student_id": 12,
            "course_id": 101,
            "activity_no": activity_no + 1,
            "conversation_history": [{"role": "assistant", "content": "other activity"}],
        },
        {
            "id": 3,
            "student_id": 13,
            "course_id": 202,
            "activity_no": activity_no,
            "conversation_history": [{"role": "assistant", "content": "other course"}],
        },
    ]
    return score_logs, conversation_state


def _base_reset_db(activity_status="ACTIVE", mappings=None, activity_no=1):
    score_logs, conversation_state = _runtime_rows(activity_no=activity_no)
    return FakeDB(
        instructors=[
            {
                "id": 7,
                "email": "instructor@test.com",
                "full_name": "Test Instructor",
                "password": "secure123",
            }
        ],
        students=[
            {
                "id": 11,
                "email": "student@test.com",
                "full_name": "Test Student",
                "password": "studentpass",
            }
        ],
        courses=[
            {"id": 101, "course_id": "CS101", "course_name": "Intro CS"},
            {"id": 202, "course_id": "CS202", "course_name": "Data Structures"},
        ],
        instructor_courses=mappings if mappings is not None else [{"id": 1, "instructor_id": 7, "course_id": 101}],
        student_courses=[{"id": 1, "student_id": 11, "course_id": 101}],
        activities=[
            {
                "id": 1,
                "course_id": 101,
                "activity_no": activity_no,
                "activity_text": "Target activity",
                "learning_objectives": ["Objective"],
                "status": activity_status,
            }
        ],
        score_logs=score_logs,
        conversation_state=conversation_state,
    )


def test_reset_endpoint_performs_full_reset_behavior(client, monkeypatch):
    fake_db = _base_reset_db(activity_status="ACTIVE")
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = client.post("/instructor/reset-activity", params=_reset_params())

    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "Activity reset"}
    assert fake_db.tables["activities"][0]["status"] == "ENDED"
    assert fake_db.tables["score_logs"] == [
        {"id": 2, "student_id": 12, "course_id": 101, "activity_no": 2, "score": 1.0, "meta": "other activity"},
        {"id": 3, "student_id": 13, "course_id": 202, "activity_no": 1, "score": 1.0, "meta": "other course"},
    ]
    assert fake_db.tables["conversation_state"] == [
        {
            "id": 2,
            "student_id": 12,
            "course_id": 101,
            "activity_no": 2,
            "conversation_history": [{"role": "assistant", "content": "other activity"}],
        },
        {
            "id": 3,
            "student_id": 13,
            "course_id": 202,
            "activity_no": 1,
            "conversation_history": [{"role": "assistant", "content": "other course"}],
        },
    ]


def test_log_score_is_rejected_after_reset(client, monkeypatch):
    fake_db = _base_reset_db(activity_status="ACTIVE")
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = client.post("/instructor/reset-activity", params=_reset_params())
    score_count_after_reset = len(fake_db.tables["score_logs"])
    result = services.logScore("student@test.com", "studentpass", "CS101", 1, 1.0, "after reset")

    assert response.json() == {"ok": True, "message": "Activity reset"}
    assert fake_db.tables["activities"][0]["status"] == "ENDED"
    assert result == {"ok": False, "error": "Activity is not active"}
    assert len(fake_db.tables["score_logs"]) == score_count_after_reset


def test_unauthorized_reset_does_not_clean_or_end_activity(client, monkeypatch):
    fake_db = _base_reset_db(activity_status="ACTIVE", mappings=[])
    original_score_logs = list(fake_db.tables["score_logs"])
    original_conversation_state = list(fake_db.tables["conversation_state"])
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = client.post("/instructor/reset-activity", params=_reset_params())

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "Unauthorized"}
    assert fake_db.tables["activities"][0]["status"] == "ACTIVE"
    assert fake_db.tables["score_logs"] == original_score_logs
    assert fake_db.tables["conversation_state"] == original_conversation_state


def test_missing_activity_reset_does_not_clean_unrelated_runtime_data(client, monkeypatch):
    fake_db = _base_reset_db(activity_status="ACTIVE")
    original_score_logs = list(fake_db.tables["score_logs"])
    original_conversation_state = list(fake_db.tables["conversation_state"])
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = client.post("/instructor/reset-activity", params=_reset_params(activity_no=999))

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "Activity does not exist"}
    assert fake_db.tables["activities"][0]["status"] == "ACTIVE"
    assert fake_db.tables["score_logs"] == original_score_logs
    assert fake_db.tables["conversation_state"] == original_conversation_state

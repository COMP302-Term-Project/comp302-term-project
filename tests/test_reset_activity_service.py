from app import services
from tests.fake_supabase import FakeDB


def make_reset_db(activity_status="ACTIVE", mappings=None, activity_no=1):
    return FakeDB(
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
            {"id": 202, "course_id": "CS202", "course_name": "Data Structures"},
        ],
        instructor_courses=mappings if mappings is not None else [{"id": 1, "instructor_id": 7, "course_id": 101}],
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
        score_logs=[
            {"id": 1, "student_id": 1, "course_id": 101, "activity_no": activity_no, "score": 1.0, "meta": "target"},
            {"id": 2, "student_id": 2, "course_id": 101, "activity_no": activity_no + 1, "score": 1.0, "meta": "other activity"},
            {"id": 3, "student_id": 3, "course_id": 202, "activity_no": activity_no, "score": 1.0, "meta": "other course"},
        ],
        conversation_state=[
            {
                "id": 1,
                "student_id": 1,
                "course_id": 101,
                "activity_no": activity_no,
                "conversation_history": [{"role": "assistant", "content": "target"}],
            },
            {
                "id": 2,
                "student_id": 2,
                "course_id": 101,
                "activity_no": activity_no + 1,
                "conversation_history": [{"role": "assistant", "content": "other activity"}],
            },
            {
                "id": 3,
                "student_id": 3,
                "course_id": 202,
                "activity_no": activity_no,
                "conversation_history": [{"role": "assistant", "content": "other course"}],
            },
        ],
    )


def test_authorized_instructor_can_reset_existing_active_activity(monkeypatch):
    fake_db = make_reset_db(activity_status="ACTIVE")
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.resetActivity("test@test.com", "secure123", "CS101", 1)

    assert result == {"ok": True, "message": "Activity reset"}
    assert fake_db.tables["activities"][0]["status"] == "ENDED"
    assert fake_db.tables["score_logs"] == [
        {"id": 2, "student_id": 2, "course_id": 101, "activity_no": 2, "score": 1.0, "meta": "other activity"},
        {"id": 3, "student_id": 3, "course_id": 202, "activity_no": 1, "score": 1.0, "meta": "other course"},
    ]
    assert fake_db.tables["conversation_state"] == [
        {
            "id": 2,
            "student_id": 2,
            "course_id": 101,
            "activity_no": 2,
            "conversation_history": [{"role": "assistant", "content": "other activity"}],
        },
        {
            "id": 3,
            "student_id": 3,
            "course_id": 202,
            "activity_no": 1,
            "conversation_history": [{"role": "assistant", "content": "other course"}],
        },
    ]


def test_reset_preserves_unrelated_score_logs_and_conversation_state(monkeypatch):
    fake_db = make_reset_db(activity_status="ACTIVE")
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    services.resetActivity("test@test.com", "secure123", "CS101", 1)

    assert all(row["id"] != 1 for row in fake_db.tables["score_logs"])
    assert {row["id"] for row in fake_db.tables["score_logs"]} == {2, 3}
    assert all(row["id"] != 1 for row in fake_db.tables["conversation_state"])
    assert {row["id"] for row in fake_db.tables["conversation_state"]} == {2, 3}


def test_unauthorized_instructor_cannot_reset(monkeypatch):
    fake_db = make_reset_db(activity_status="ACTIVE", mappings=[])
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.resetActivity("test@test.com", "secure123", "CS101", 1)

    assert result == {"ok": False, "error": "Unauthorized"}
    assert len(fake_db.tables["score_logs"]) == 3
    assert len(fake_db.tables["conversation_state"]) == 3
    assert fake_db.tables["activities"][0]["status"] == "ACTIVE"


def test_missing_activity_cannot_be_reset(monkeypatch):
    fake_db = make_reset_db(activity_status="ACTIVE")
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.resetActivity("test@test.com", "secure123", "CS101", 999)

    assert result == {"ok": False, "error": "Activity does not exist"}
    assert len(fake_db.tables["score_logs"]) == 3
    assert len(fake_db.tables["conversation_state"]) == 3
    assert fake_db.tables["activities"][0]["status"] == "ACTIVE"


def test_reset_works_for_not_started_activity(monkeypatch):
    fake_db = make_reset_db(activity_status="NOT_STARTED")
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.resetActivity("test@test.com", "secure123", "CS101", 1)

    assert result == {"ok": True, "message": "Activity reset"}
    assert fake_db.tables["activities"][0]["status"] == "ENDED"
    assert fake_db.tables["score_logs"] == [
        {"id": 2, "student_id": 2, "course_id": 101, "activity_no": 2, "score": 1.0, "meta": "other activity"},
        {"id": 3, "student_id": 3, "course_id": 202, "activity_no": 1, "score": 1.0, "meta": "other course"},
    ]


def test_reset_works_for_ended_activity(monkeypatch):
    fake_db = make_reset_db(activity_status="ENDED")
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.resetActivity("test@test.com", "secure123", "CS101", 1)

    assert result == {"ok": True, "message": "Activity reset"}
    assert fake_db.tables["activities"][0]["status"] == "ENDED"
    assert fake_db.tables["score_logs"] == [
        {"id": 2, "student_id": 2, "course_id": 101, "activity_no": 2, "score": 1.0, "meta": "other activity"},
        {"id": 3, "student_id": 3, "course_id": 202, "activity_no": 1, "score": 1.0, "meta": "other course"},
    ]

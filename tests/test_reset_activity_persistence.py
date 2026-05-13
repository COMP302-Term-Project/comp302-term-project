from app import services
from tests.fake_supabase import FakeDB


def test_cleanup_deletes_score_logs_for_selected_course_activity_only():
    fake_db = FakeDB(
        score_logs=[
            {"id": 1, "student_id": 1, "course_id": 10, "activity_no": 2, "score": 1.0, "meta": "target"},
            {"id": 2, "student_id": 2, "course_id": 10, "activity_no": 3, "score": 1.0, "meta": "other activity"},
            {"id": 3, "student_id": 3, "course_id": 11, "activity_no": 2, "score": 1.0, "meta": "other course"},
        ],
        conversation_state=[],
    )

    services._cleanup_activity_runtime_state(fake_db, course_db_id=10, activity_no=2)

    assert fake_db.tables["score_logs"] == [
        {"id": 2, "student_id": 2, "course_id": 10, "activity_no": 3, "score": 1.0, "meta": "other activity"},
        {"id": 3, "student_id": 3, "course_id": 11, "activity_no": 2, "score": 1.0, "meta": "other course"},
    ]


def test_cleanup_deletes_conversation_state_for_selected_course_activity_only():
    fake_db = FakeDB(
        score_logs=[],
        conversation_state=[
            {
                "id": 1,
                "student_id": 1,
                "course_id": 10,
                "activity_no": 2,
                "conversation_history": [{"role": "assistant", "content": "target"}],
            },
            {
                "id": 2,
                "student_id": 2,
                "course_id": 10,
                "activity_no": 3,
                "conversation_history": [{"role": "assistant", "content": "other activity"}],
            },
            {
                "id": 3,
                "student_id": 3,
                "course_id": 11,
                "activity_no": 2,
                "conversation_history": [{"role": "assistant", "content": "other course"}],
            },
        ],
    )

    services._cleanup_activity_runtime_state(fake_db, course_db_id=10, activity_no=2)

    assert fake_db.tables["conversation_state"] == [
        {
            "id": 2,
            "student_id": 2,
            "course_id": 10,
            "activity_no": 3,
            "conversation_history": [{"role": "assistant", "content": "other activity"}],
        },
        {
            "id": 3,
            "student_id": 3,
            "course_id": 11,
            "activity_no": 2,
            "conversation_history": [{"role": "assistant", "content": "other course"}],
        },
    ]


def test_cleanup_uses_only_score_logs_and_conversation_state_tables():
    fake_db = FakeDB(
        activities=[
            {
                "id": 1,
                "course_id": 10,
                "activity_no": 2,
                "activity_text": "Keep me",
                "learning_objectives": ["Objective"],
                "status": "ACTIVE",
            }
        ],
        score_logs=[
            {"id": 1, "student_id": 1, "course_id": 10, "activity_no": 2, "score": 1.0, "meta": "target"},
        ],
        conversation_state=[
            {
                "id": 1,
                "student_id": 1,
                "course_id": 10,
                "activity_no": 2,
                "conversation_history": [{"role": "assistant", "content": "target"}],
            },
        ],
    )

    services._cleanup_activity_runtime_state(fake_db, course_db_id=10, activity_no=2)

    assert fake_db.tables["activities"] == [
        {
            "id": 1,
            "course_id": 10,
            "activity_no": 2,
            "activity_text": "Keep me",
            "learning_objectives": ["Objective"],
            "status": "ACTIVE",
        }
    ]
    assert fake_db.tables["score_logs"] == []
    assert fake_db.tables["conversation_state"] == []

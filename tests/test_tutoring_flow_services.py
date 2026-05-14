from unittest.mock import patch

from app.services import submitTutoringAnswer
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


def _activity_row(status="ACTIVE"):
    return {
        "id": 33,
        "course_id": 101,
        "activity_no": 1,
        "activity_text": "Compare active recall with rereading.",
        "learning_objectives": [
            "Active retrieval practice improves long-term learning more than passive rereading.",
            "Feedback after retrieval helps identify and correct misunderstandings.",
        ],
        "status": status,
    }


def _authorized_student_db(activity_status="ACTIVE", conversation_state=None):
    return FakeDB(
        students=[_student_row()],
        courses=[_course_row()],
        student_courses=[{"id": 1, "student_id": 9, "course_id": 101}],
        activities=[_activity_row(status=activity_status)],
        conversation_state=conversation_state or [],
    )


def test_submit_tutoring_answer_initializes_conversation_state_with_one_question():
    fake_db = _authorized_student_db()

    with patch("app.services.get_db", return_value=fake_db):
        response = submitTutoringAnswer("student@test.com", "secure123", "CS101", 1)

    assert response["ok"] is True
    assert response["state"] == {"student_turns": 0, "assistant_turns": 1, "score": 0.0}
    assert response["response"].startswith("Activity: Compare active recall with rereading.")
    assert response["response"].count("?") == 1

    saved_state = fake_db.tables["conversation_state"][0]
    assert saved_state["student_id"] == 9
    assert saved_state["course_id"] == 101
    assert saved_state["activity_no"] == 1
    assert saved_state["conversation_history"] == [
        {"role": "assistant", "content": response["response"]},
    ]


def test_submit_tutoring_answer_stores_student_answer_and_returns_one_followup_question():
    initial_history = [
        {
            "role": "assistant",
            "content": "Activity: Compare active recall with rereading.\n\nWhat is your initial answer in your own words?",
        }
    ]
    fake_db = _authorized_student_db(
        conversation_state=[
            {
                "student_id": 9,
                "course_id": 101,
                "activity_no": 1,
                "conversation_history": initial_history,
            }
        ],
    )

    with patch("app.services.get_db", return_value=fake_db), patch(
        "app.services._call_tutoring_llm",
        return_value=(
            "Can you make your reasoning more specific using the important terms from the activity?",
            "",
        ),
    ):
        response = submitTutoringAnswer(
            "student@test.com",
            "secure123",
            "CS101",
            1,
            answer="Active recall is better because I try to remember before checking.",
        )

    assert response["ok"] is True
    assert response["state"] == {"student_turns": 1, "assistant_turns": 2, "score": 0.0}
    assert response["response"].count("?") == 1
    assert "learning objective" not in response["response"].lower()
    assert "feedback after retrieval" not in response["response"].lower()

    saved_history = fake_db.tables["conversation_state"][0]["conversation_history"]
    assert saved_history[1] == {
        "role": "user",
        "content": "Active recall is better because I try to remember before checking.",
    }
    assert saved_history[2] == {"role": "assistant", "content": response["response"]}


def test_submit_tutoring_answer_rejects_ended_activity_without_saving_state():
    fake_db = _authorized_student_db(activity_status="ENDED")

    with patch("app.services.get_db", return_value=fake_db):
        response = submitTutoringAnswer("student@test.com", "secure123", "CS101", 1)

    assert response == {"ok": False, "error": "Activity is not active"}
    assert fake_db.tables["conversation_state"] == []

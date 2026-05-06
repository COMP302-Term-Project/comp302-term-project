from unittest.mock import patch

from app.main import submitTutoringAnswer
from app.services import _build_tutoring_llm_messages
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


def _activity_row():
    return {
        "id": 33,
        "course_id": 101,
        "activity_no": 1,
        "activity_text": "Compare active recall with rereading.",
        "learning_objectives": [
            "Active retrieval practice improves long-term learning more than passive rereading.",
            "Feedback after retrieval helps identify and correct misunderstandings.",
        ],
        "status": "ACTIVE",
    }


def _authorized_student_db(conversation_history):
    return FakeDB(
        students=[_student_row()],
        courses=[_course_row()],
        student_courses=[{"id": 1, "student_id": 9, "course_id": 101}],
        activities=[_activity_row()],
        conversation_state=[
            {
                "student_id": 9,
                "course_id": 101,
                "activity_no": 1,
                "conversation_history": conversation_history,
            }
        ],
    )


def test_student_tutoring_route_uses_mock_llm_response_and_persists_history():
    initial_history = [
        {
            "role": "assistant",
            "content": "Activity: Compare active recall with rereading.\n\nWhat is your initial answer in your own words?",
        }
    ]
    fake_db = _authorized_student_db(initial_history)
    llm_response = "What part of the activity explains why remembering first helps long-term learning?"

    with patch("app.services.get_db", return_value=fake_db), patch(
        "app.services._call_tutoring_llm",
        return_value=llm_response,
    ) as call_tutoring_llm:
        response = submitTutoringAnswer(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            answer="Active recall is better because I try to remember before checking.",
        )

    assert response == {
        "ok": True,
        "response": llm_response,
        "state": {"student_turns": 1, "assistant_turns": 2},
    }
    assert response["response"].count("?") == 1
    assert "learning objective" not in response["response"].lower()
    assert "feedback after retrieval" not in response["response"].lower()

    call_tutoring_llm.assert_called_once()
    activity_arg, history_arg = call_tutoring_llm.call_args.args
    assert activity_arg["activity_text"] == "Compare active recall with rereading."
    assert activity_arg["learning_objectives"] == _activity_row()["learning_objectives"]
    assert history_arg[-1] == {
        "role": "user",
        "content": "Active recall is better because I try to remember before checking.",
    }

    saved_history = fake_db.tables["conversation_state"][0]["conversation_history"]
    assert saved_history == [
        initial_history[0],
        {
            "role": "user",
            "content": "Active recall is better because I try to remember before checking.",
        },
        {"role": "assistant", "content": llm_response},
    ]


def test_tutoring_llm_messages_keep_hidden_objectives_out_of_chat_history():
    activity = _activity_row()
    history = [
        {
            "role": "assistant",
            "content": "Activity: Compare active recall with rereading.\n\nWhat is your initial answer in your own words?",
        },
        {
            "role": "user",
            "content": "Active recall is better because I try to remember before checking.",
        },
    ]

    messages = _build_tutoring_llm_messages(activity, history)

    assert messages[0]["role"] == "system"
    assert "Hidden objectives for your reasoning only" in messages[0]["content"]
    assert "Feedback after retrieval" in messages[0]["content"]
    assert messages[1:] == history

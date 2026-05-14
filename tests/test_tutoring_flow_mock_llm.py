from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app, submitTutoringAnswer
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
        return_value=(llm_response, ""),
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
        "state": {"student_turns": 1, "assistant_turns": 2, "score": 0.0},
    }
    assert response["response"].count("?") == 1
    assert "learning objective" not in response["response"].lower()
    assert "feedback after retrieval" not in response["response"].lower()

    call_tutoring_llm.assert_called_once()
    activity_arg, history_arg, score_arg = call_tutoring_llm.call_args.args
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
    assert "LEARNING OBJECTIVES:" in messages[0]["content"]
    assert "NEVER present or mention about learning_objectives to the student" in messages[0]["content"]
    assert "Feedback after retrieval" in messages[0]["content"]
    assert messages[1:] == history


def test_student_tutoring_route_detects_objective_and_logs_score_idempotently():
    initial_history = [
        {"role": "assistant", "content": "Initial"}
    ]
    fake_db = _authorized_student_db(initial_history)
    
    llm_response = "You got it! Here is a mini-lesson."
    apicall = 'studentApi(action:"logScore") with parameters: score=1 and meta="Hidden instructor objective"'
    
    with patch("app.services.get_db", return_value=fake_db), patch(
        "app.services._call_tutoring_llm",
        return_value=(llm_response, apicall),
    ):
        # First call should log the score and return score = 1.0
        response1 = submitTutoringAnswer(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            answer="I understand the objective.",
        )
        assert response1["ok"] is True
        assert len(fake_db.tables.get("score_logs", [])) == 1
        assert fake_db.tables["score_logs"][0]["meta"] == "Hidden instructor objective"
        assert response1["state"]["score"] == 1.0
        
        # Second call with SAME objective should NOT log a new score (idempotent), score remains 1.0
        response2 = submitTutoringAnswer(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            answer="I still understand it.",
        )
        assert response2["ok"] is True
        assert len(fake_db.tables["score_logs"]) == 1
        assert response2["state"]["score"] == 1.0
        assert "no new point" in response2["response"]


def test_repeating_same_objective_returns_json_without_new_point():
    initial_history = [
        {"role": "assistant", "content": "Initial"}
    ]
    fake_db = _authorized_student_db(initial_history)
    objective = "Active retrieval practice improves long-term learning more than passive rereading."
    apicall = f'studentApi(action:"logScore") with parameters: score=1 and meta="{objective}"'

    with patch("app.services.get_db", return_value=fake_db), patch(
        "app.services._call_tutoring_llm",
        return_value=("Great! You earned 1 point.", apicall),
    ):
        first = TestClient(app).post(
            "/student/submit-tutoring-answer",
            params={
                "email": "student@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
                "answer": "Active retrieval is better than rereading because recall strengthens memory.",
            },
        )
        second = TestClient(app).post(
            "/student/submit-tutoring-answer",
            params={
                "email": "student@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1,
                "answer": "Active retrieval is better than rereading because the student recalls the idea from memory.",
            },
        )

    assert first.status_code == 200
    assert first.headers["content-type"].startswith("application/json")
    assert first.json()["ok"] is True
    assert first.json()["state"]["score"] == 1.0

    assert second.status_code == 200
    assert second.headers["content-type"].startswith("application/json")
    assert second.json()["ok"] is True
    assert second.json()["state"]["score"] == 1.0
    assert "no new point" in second.json()["response"]
    assert len(fake_db.tables["score_logs"]) == 1


def test_second_distinct_objective_can_earn_next_point_after_duplicate():
    initial_history = [
        {"role": "assistant", "content": "Initial"}
    ]
    fake_db = _authorized_student_db(initial_history)
    first_objective = "Active retrieval practice improves long-term learning more than passive rereading."
    second_objective = "Feedback after retrieval helps identify and correct misunderstandings."

    with patch("app.services.get_db", return_value=fake_db), patch(
        "app.services._call_tutoring_llm",
        side_effect=[
            ("Great! You earned 1 point.", f'studentApi(action:"logScore") with parameters: score=1 and meta="{first_objective}"'),
            ("You already covered this idea.", f'studentApi(action:"logScore") with parameters: score=1 and meta="{first_objective}"'),
            ("Great! You earned another point.", f'studentApi(action:"logScore") with parameters: score=1 and meta="{second_objective}"'),
        ],
    ):
        first = submitTutoringAnswer(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            answer="retrieval",
        )
        duplicate = submitTutoringAnswer(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            answer="retrieval again",
        )
        second = submitTutoringAnswer(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            answer="feedback",
        )

    assert first["ok"] is True
    assert first["state"]["score"] == 1.0
    assert duplicate["ok"] is True
    assert duplicate["state"]["score"] == 1.0
    assert second["ok"] is True
    assert second["state"]["score"] == 2.0
    assert len(fake_db.tables["score_logs"]) == 2
    assert [row["meta"] for row in fake_db.tables["score_logs"]] == [
        first_objective,
        second_objective,
    ]


def test_student_tutoring_route_handles_activity_completion_behavior():
    initial_history = [
        {"role": "assistant", "content": "Initial"}
    ]
    fake_db = _authorized_student_db(initial_history)
    
    # We simulate scoring the second (final) objective
    # Score becomes 2.0. The LLM should celebrate and not ask further questions.
    llm_response = "Congratulations! You have mastered all learning objectives. We are done!"
    apicall = 'studentApi(action:"logScore") with parameters: score=1 and meta="Second objective"'
    
    # Seed the DB with the first objective already achieved
    fake_db.tables["score_logs"] = [
        {
            "id": 999,
            "student_id": 9,
            "course_id": 101,
            "activity_no": 1,
            "score": 1.0,
            "meta": "First objective"
        }
    ]
    
    with patch("app.services.get_db", return_value=fake_db), patch(
        "app.services._call_tutoring_llm",
        return_value=(llm_response, apicall),
    ):
        response = submitTutoringAnswer(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            answer="I understand the second objective.",
        )
        assert response["ok"] is True
        assert len(fake_db.tables.get("score_logs", [])) == 2
        assert fake_db.tables["score_logs"][1]["meta"] == "Second objective"
        
        # Activity completion behavior: score should equal the total number of objectives (2)
        assert response["state"]["score"] == 2.0
        assert "Congratulations" in response["response"]

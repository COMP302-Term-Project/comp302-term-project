from unittest.mock import patch

from app.main import app, submitTutoringAnswer


def test_student_submit_tutoring_answer_route_is_registered():
    paths = {route.path for route in app.routes}

    assert "/student/submit-tutoring-answer" in paths


def test_student_submit_tutoring_answer_route_forwards_response_unchanged():
    service_response = {
        "ok": True,
        "response": "Can you make your reasoning more specific using the important terms from the activity?",
        "state": {"student_turns": 1, "assistant_turns": 2, "score": 0.0},
    }

    with patch("app.services.submitTutoringAnswer", return_value=service_response) as submit_tutoring_answer:
        response = submitTutoringAnswer(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
            answer="Active recall is better than rereading.",
        )

    assert response == service_response
    submit_tutoring_answer.assert_called_once_with(
        email="student@test.com",
        password="secure123",
        course_id="CS101",
        activity_no=1,
        answer="Active recall is better than rereading.",
    )


def test_student_submit_tutoring_answer_route_allows_initial_turn_without_answer():
    service_response = {
        "ok": True,
        "response": "Activity: Compare active recall with rereading.\n\nWhat is your initial answer in your own words?",
        "state": {"student_turns": 0, "assistant_turns": 1, "score": 0.0},
    }

    with patch("app.services.submitTutoringAnswer", return_value=service_response) as submit_tutoring_answer:
        response = submitTutoringAnswer(
            email="student@test.com",
            password="secure123",
            course_id="CS101",
            activity_no=1,
        )

    assert response == service_response
    submit_tutoring_answer.assert_called_once_with(
        email="student@test.com",
        password="secure123",
        course_id="CS101",
        activity_no=1,
        answer=None,
    )

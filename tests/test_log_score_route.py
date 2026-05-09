from unittest.mock import patch


def _get_log_score_params():
    return {
        "email": "student@test.com",
        "password": "secure123",
        "course_id": "CS101",
        "activity_no": 1,
        "score": 1.0,
        "meta": "learned_objective"
    }


def test_student_log_score_route_returns_success_response_unchanged(client):
    service_response = {
        "ok": True,
        "score_log": {
            "student_id": 9,
            "course_id": 101,
            "activity_no": 1,
            "score": 1.0,
            "meta": "learned_objective"
        },
    }

    with patch("app.services.logScore", return_value=service_response) as log_score:
        response = client.post("/student/log-score", params=_get_log_score_params())

    assert response.status_code == 200
    assert response.json() == service_response
    log_score.assert_called_once_with(
        email="student@test.com",
        password="secure123",
        course_id="CS101",
        activity_no=1,
        score=1.0,
        meta="learned_objective"
    )


def test_student_log_score_route_returns_error_response_unchanged(client):
    service_response = {"ok": False, "error": "Score must be positive"}

    with patch("app.services.logScore", return_value=service_response) as log_score:
        response = client.post("/student/log-score", params=_get_log_score_params())

    assert response.status_code == 200
    assert response.json() == service_response
    log_score.assert_called_once_with(
        email="student@test.com",
        password="secure123",
        course_id="CS101",
        activity_no=1,
        score=1.0,
        meta="learned_objective"
    )

from unittest.mock import patch


def _get_activity_params():
    return {
        "email": "student@test.com",
        "password": "secure123",
        "course_id": "CS101",
        "activity_no": 1,
    }


def test_student_get_activity_route_returns_success_response_unchanged(client):
    service_response = {
        "ok": True,
        "activity": {
            "course_id": 101,
            "activity_no": 1,
            "activity_text": "Solve the warmup problem",
        },
    }

    with patch("app.services.getActivity", return_value=service_response) as get_activity:
        response = client.post("/student/get-activity", params=_get_activity_params())

    assert response.status_code == 200
    assert response.json() == service_response
    get_activity.assert_called_once_with(
        email="student@test.com",
        password="secure123",
        course_id="CS101",
        activity_no=1,
    )


def test_student_get_activity_route_returns_error_response_unchanged(client):
    service_response = {"ok": False, "error": "Activity is not active"}

    with patch("app.services.getActivity", return_value=service_response) as get_activity:
        response = client.post("/student/get-activity", params=_get_activity_params())

    assert response.status_code == 200
    assert response.json() == service_response
    get_activity.assert_called_once_with(
        email="student@test.com",
        password="secure123",
        course_id="CS101",
        activity_no=1,
    )

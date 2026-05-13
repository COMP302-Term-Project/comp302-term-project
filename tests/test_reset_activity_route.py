from unittest.mock import patch


def _get_reset_activity_params():
    return {
        "email": "instructor@test.com",
        "password": "secure123",
        "course_id": "CS101",
        "activity_no": 1,
    }


def test_instructor_reset_activity_route_returns_success_response_unchanged(client):
    service_response = {"ok": True, "message": "Activity reset"}

    with patch("app.services.resetActivity", return_value=service_response) as reset_activity:
        response = client.post("/instructor/reset-activity", params=_get_reset_activity_params())

    assert response.status_code == 200
    assert response.json() == service_response
    reset_activity.assert_called_once_with(
        email="instructor@test.com",
        password="secure123",
        course_id="CS101",
        activity_no=1,
    )


def test_instructor_reset_activity_route_returns_error_response_unchanged(client):
    service_response = {"ok": False, "error": "Activity does not exist"}

    with patch("app.services.resetActivity", return_value=service_response) as reset_activity:
        response = client.post("/instructor/reset-activity", params=_get_reset_activity_params())

    assert response.status_code == 200
    assert response.json() == service_response
    reset_activity.assert_called_once_with(
        email="instructor@test.com",
        password="secure123",
        course_id="CS101",
        activity_no=1,
    )

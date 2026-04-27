import pytest
from unittest.mock import MagicMock, patch
import app.services as services

@patch('app.services.listMyCourses')
@patch('app.services.get_db')
def test_start_activity_success(mock_get_db, mock_list_courses):
    mock_list_courses.return_value = {"ok": True, "courses": [{"id": "COMP302"}]}

    mock_supabase = MagicMock()
    mock_get_db.return_value = mock_supabase

    mock_exist_query = MagicMock()
    mock_exist_query.eq.return_value.eq.return_value.execute.return_value.data = [{"course_id": "COMP302", "activity_no": 1, "state": "NOT_STARTED"}]
    mock_supabase.table.return_value.select.return_value = mock_exist_query

    res = services.startActivity("instructor1@mef.edu.tr", "pass", "COMP302", 1)
    assert res["ok"] is True
    assert "ACTIVE" in res["message"]
    mock_supabase.table().update.assert_called_with({"state": "ACTIVE"})

@patch('app.services.listMyCourses')
@patch('app.services.get_db')
def test_start_activity_invalid_state(mock_get_db, mock_list_courses):
    mock_list_courses.return_value = {"ok": True, "courses": [{"id": "COMP302"}]}

    mock_supabase = MagicMock()
    mock_get_db.return_value = mock_supabase

    mock_exist_query = MagicMock()
    mock_exist_query.eq.return_value.eq.return_value.execute.return_value.data = [{"course_id": "COMP302", "activity_no": 1, "state": "ACTIVE"}]
    mock_supabase.table.return_value.select.return_value = mock_exist_query

    res = services.startActivity("instructor1@mef.edu.tr", "pass", "COMP302", 1)
    assert res["ok"] is False
    assert "Invalid state transition" in res["error"]
    assert mock_supabase.table().update.called is False

@patch('app.services.listMyCourses')
@patch('app.services.get_db')
def test_end_activity_success(mock_get_db, mock_list_courses):
    mock_list_courses.return_value = {"ok": True, "courses": [{"id": "COMP302"}]}

    mock_supabase = MagicMock()
    mock_get_db.return_value = mock_supabase

    mock_exist_query = MagicMock()
    mock_exist_query.eq.return_value.eq.return_value.execute.return_value.data = [{"course_id": "COMP302", "activity_no": 1, "state": "ACTIVE"}]
    mock_supabase.table.return_value.select.return_value = mock_exist_query

    res = services.endActivity("instructor1@mef.edu.tr", "pass", "COMP302", 1)
    assert res["ok"] is True
    assert "ENDED" in res["message"]
    mock_supabase.table().update.assert_called_with({"state": "ENDED"})

@patch('app.services.listMyCourses')
@patch('app.services.get_db')
def test_end_activity_invalid_state(mock_get_db, mock_list_courses):
    mock_list_courses.return_value = {"ok": True, "courses": [{"id": "COMP302"}]}

    mock_supabase = MagicMock()
    mock_get_db.return_value = mock_supabase

    mock_exist_query = MagicMock()
    mock_exist_query.eq.return_value.eq.return_value.execute.return_value.data = [{"course_id": "COMP302", "activity_no": 1, "state": "NOT_STARTED"}]
    mock_supabase.table.return_value.select.return_value = mock_exist_query

    res = services.endActivity("instructor1@mef.edu.tr", "pass", "COMP302", 1)
    assert res["ok"] is False
    assert "Invalid state transition" in res["error"]
    assert mock_supabase.table().update.called is False

@patch('app.services.listMyCourses')
def test_start_activity_unauthorized(mock_list_courses):
    mock_list_courses.return_value = {"ok": True, "courses": [{"id": "COMP302"}]}

    res = services.startActivity("instructor1@mef.edu.tr", "pass", "COMP404", 1)
    assert res["ok"] is False
    assert "Unauthorized" in res["error"]
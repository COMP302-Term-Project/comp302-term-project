from unittest.mock import patch
from app.services import listMyCourses

class FakeResponse:
    def __init__(self, data):
        self.data = data

class FakeQueryBuilder:
    def __init__(self, table_name, auth_data, courses_data):
        self.table_name = table_name
        self.auth_data = auth_data
        self.courses_data = courses_data

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        # We can simulate filtering here if we wanted to
        # But since we provide pre-filtered data for the mock, we just store it
        self.filter_value = value
        return self

    def execute(self):
        if self.table_name == "instructors":
            return FakeResponse(self.auth_data)
        elif self.table_name == "courses":
            return FakeResponse(self.courses_data)
        return FakeResponse([])

class FakeDB:
    def __init__(self, auth_data=None, courses_data=None):
        self.auth_data = auth_data or []
        self.courses_data = courses_data or []

    def table(self, name):
        return FakeQueryBuilder(name, self.auth_data, self.courses_data)

def test_list_my_courses_success():
    auth_data = [{"password": "secure123"}]
    courses_data = [{"course_id": "CS101", "instructor_email": "test@test.com"}]
    
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data)
    
    with patch("app.services.get_db", return_value=fake_db):
        response = listMyCourses("test@test.com", "secure123")
        
        assert response["ok"] is True
        assert len(response["courses"]) == 1
        assert response["courses"][0]["course_id"] == "CS101"

def test_list_my_courses_invalid_password():
    auth_data = [{"password": "secure123"}]
    fake_db = FakeDB(auth_data=auth_data)
    
    with patch("app.services.get_db", return_value=fake_db):
        response = listMyCourses("test@test.com", "wrongpassword")
        
        assert response["ok"] is False
        assert "error" in response

def test_list_my_courses_user_not_found():
    fake_db = FakeDB(auth_data=[])
    
    with patch("app.services.get_db", return_value=fake_db):
        response = listMyCourses("unknown@test.com", "password")
        
        assert response["ok"] is False
        assert "error" in response

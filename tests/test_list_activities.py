from unittest.mock import patch
from app.services import listActivities

class FakeResponse:
    def __init__(self, data):
        self.data = data

class FakeQueryBuilder:
    def __init__(self, table_name, auth_data, courses_data, activities_data):
        self.table_name = table_name
        self.auth_data = auth_data
        self.courses_data = courses_data
        self.activities_data = activities_data

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        return self

    def order(self, column):
        if self.table_name == "activities":
            self.activities_data = sorted(self.activities_data, key=lambda x: x.get(column, 0))
        return self

    def execute(self):
        if self.table_name == "instructors":
            return FakeResponse(self.auth_data)
        elif self.table_name == "courses":
            return FakeResponse(self.courses_data)
        elif self.table_name == "activities":
            return FakeResponse(self.activities_data)
        return FakeResponse([])

class FakeDB:
    def __init__(self, auth_data=None, courses_data=None, activities_data=None):
        self.auth_data = auth_data or []
        self.courses_data = courses_data or []
        self.activities_data = activities_data or []

    def table(self, name):
        return FakeQueryBuilder(name, self.auth_data, self.courses_data, self.activities_data)


def test_list_activities_course_scoping_unauthorized():
    auth_data = [{"password": "password123"}]
    courses_data = [{"course_id": "CS101", "instructor_email": "other@test.com"}]
    
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data)
    
    with patch("app.services.get_db", return_value=fake_db):
        response = listActivities("test@test.com", "password123", "CS101")
        
        assert response["ok"] is False
        assert response["error"] == "Not authorized for this course"


def test_list_activities_ordering():
    auth_data = [{"password": "password123"}]
    courses_data = [{"course_id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [
        {"activity_no": 3, "course_id": "CS101", "activity_text": "Task 3"},
        {"activity_no": 1, "course_id": "CS101", "activity_text": "Task 1"},
        {"activity_no": 2, "course_id": "CS101", "activity_text": "Task 2"},
    ]
    
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)
    
    with patch("app.services.get_db", return_value=fake_db):
        response = listActivities("test@test.com", "password123", "CS101")
        
        assert response["ok"] is True
        activities = response["activities"]
        assert len(activities) == 3
        assert activities[0]["activity_no"] == 1
        assert activities[1]["activity_no"] == 2
        assert activities[2]["activity_no"] == 3

from unittest.mock import patch
from app.services import createActivity

class FakeResponse:
    def __init__(self, data):
        self.data = data

class FakeQueryBuilder:
    def __init__(self, table_name, auth_data, courses_data, activities_data):
        self.table_name = table_name
        self.auth_data = auth_data
        self.courses_data = courses_data
        self.activities_data = activities_data

    def select(self, *args, **kwargs): return self
    def eq(self, column, value): return self
    def order(self, *args, **kwargs): return self
    def limit(self, *args, **kwargs): return self

    def insert(self, data):
        self.activities_data.append(data)
        self.last_inserted = data
        return self

    def execute(self):
        if self.table_name == "instructors":
            return FakeResponse(self.auth_data)
        elif self.table_name == "courses":
            return FakeResponse(self.courses_data)
        elif self.table_name == "activities":
            if hasattr(self, "last_inserted"):
                return FakeResponse([self.last_inserted])
            return FakeResponse(self.activities_data)
        return FakeResponse([])

class FakeDB:
    def __init__(self, auth_data=None, courses_data=None, activities_data=None):
        self.auth_data = auth_data or []
        self.courses_data = courses_data or []
        self.activities_data = activities_data or []

    def table(self, name):
        return FakeQueryBuilder(name, self.auth_data, self.courses_data, self.activities_data)

def test_create_activity_success_auto_increment():
    auth_data = [{"password": "secure123", "email": "test@test.com"}]
    courses_data = [{"course_id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [{"course_id": "CS101", "activity_no": 1, "activity_text": "Old Activity"}]
    
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)
    
    with patch("app.services.get_db", return_value=fake_db):
        response = createActivity(
            email="test@test.com", 
            password="secure123", 
            course_id="CS101", 
            activity_text="New Activity", 
            learning_objectives=["Obj 1"]
        )
        
        assert response["ok"] is True
        assert response["activity"]["activity_no"] == 2
        assert response["activity"]["learning_objectives"] == ["Obj 1"]

def test_create_activity_invalid_credentials():
    auth_data = [{"password": "secure123", "email": "test@test.com"}]
    fake_db = FakeDB(auth_data=auth_data)
    
    with patch("app.services.get_db", return_value=fake_db):
        response = createActivity(
            email="test@test.com", password="wrong", course_id="CS101", 
            activity_text="text", learning_objectives=[]
        )
        assert response["ok"] is False
        assert response["error"] == "Invalid credentials"

def test_create_activity_unauthorized_course():
    auth_data = [{"password": "secure123", "email": "test@test.com"}]
    courses_data = [{"course_id": "CS101", "instructor_email": "test@test.com"}]
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data)
    
    with patch("app.services.get_db", return_value=fake_db):
        response = createActivity(
            email="test@test.com", password="secure123", course_id="MATH101", 
            activity_text="text", learning_objectives=[]
        )
        assert response["ok"] is False
        assert response["error"] == "Unauthorized course access"

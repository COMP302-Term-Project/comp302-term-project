from unittest.mock import patch

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
    def update(self, *args, **kwargs): return self
    def eq(self, column, value): return self

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

def test_update_activity_success(client):
    # 1. Arrange: Setup the fake database state
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [{"course_id": "CS101", "activity_no": 1, "state": "NOT_STARTED"}]
    
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)
    
    # 2. Act: Make a request to the FastAPI app via the test client
    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/update-activity", 
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1
            },
            json={"activity_text": "Updated text"}
        )
        
        # 3. Assert: Verify the behavior is correct
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert response.json()["message"] == "Activity updated"

def test_update_activity_already_started(client):
    # Arrange: Setup the activity to be in 'ACTIVE' state
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [{"course_id": "CS101", "activity_no": 1, "state": "ACTIVE"}]
    
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)
    
    # Act
    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/update-activity", 
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1
            },
            json={"activity_text": "Updated text"}
        )
        
        # Assert
        assert response.json()["ok"] is False
        assert "Cannot update activity that has started or ended" in response.json()["error"]

def test_update_activity_empty_patch(client):
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=[])
    
    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/update-activity", 
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1
            },
            json={} # Empty patch!
        )
        
        assert response.json()["ok"] is False
        assert response.json()["error"] == "Empty patch rejected"

def test_update_activity_unauthorized_course(client):
    # Arrange: The instructor owns CS101, but NOT MATH202
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data)
    
    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/update-activity", 
            params={
                "email": "test@test.com", 
                "password": "secure123",
                "course_id": "MATH202", 
                "activity_no": 1
            },
            json={"activity_text": "text"}
        )
        
        assert response.json()["ok"] is False
        assert response.json()["error"] == "Unauthorized course access"

def test_update_activity_not_found(client):
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [] # Activity does not exist
    
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)
    
    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/update-activity", 
            params={
                "email": "test@test.com", 
                "password": "secure123",
                "course_id": "CS101", 
                "activity_no": 999
            },
            json={"activity_text": "text"}
        )
        
        assert response.json()["ok"] is False
        assert response.json()["error"] == "Activity does not exist"

def test_update_activity_unallowed_fields(client):
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [{"course_id": "CS101", "activity_no": 1, "state": "NOT_STARTED"}]
    
    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)
    
    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/update-activity", 
            params={
                "email": "test@test.com", 
                "password": "secure123",
                "course_id": "CS101", 
                "activity_no": 1
            },
            json={"state": "ACTIVE"} # Unallowed field
        )
        
        assert response.json()["ok"] is False
        assert response.json()["error"] == "No allowed fields in patch"


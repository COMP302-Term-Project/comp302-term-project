import pytest
from unittest.mock import patch
import app.services

class FakeResponse:
    def __init__(self, data):
        self.data = data

class FakeQueryBuilder:
    def __init__(self, table_name, auth_data, courses_data, activities_data, db=None):
        self.table_name = table_name
        self.auth_data = auth_data
        self.courses_data = courses_data
        self.activities_data = activities_data
        self.db = db

    def select(self, *args, **kwargs): return self
    def update(self, *args, **kwargs):
        updated_data = args[0]
        if self.db is not None:
            self.db.updates.append({"table": self.table_name, "data": updated_data})
        return self
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
        self.updates = []

    def table(self, name):
        return FakeQueryBuilder(name, self.auth_data, self.courses_data, self.activities_data, db=self)

def test_start_activity_success(client):
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [{"course_id": "CS101", "activity_no": 1, "state": "NOT_STARTED"}]

    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/start-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1
            }
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert "ACTIVE" in response.json()["message"]
        # Verify the database was actually updated
        assert {"table": "activities", "data": {"state": "ACTIVE"}} in fake_db.updates

def test_start_activity_invalid_state(client):
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [{"course_id": "CS101", "activity_no": 1, "state": "ACTIVE"}]

    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/start-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1
            }
        )

        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "Invalid state transition" in response.json()["error"]
        # Ensure database was NOT updated
        assert len(fake_db.updates) == 0

def test_end_activity_success(client):
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [{"course_id": "CS101", "activity_no": 1, "state": "ACTIVE"}]

    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/end-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1
            }
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert "ENDED" in response.json()["message"]
        # Verify the database was actually updated
        assert {"table": "activities", "data": {"state": "ENDED"}} in fake_db.updates

def test_end_activity_invalid_state(client):
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [{"course_id": "CS101", "activity_no": 1, "state": "NOT_STARTED"}]

    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/end-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 1
            }
        )

        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "Invalid state transition" in response.json()["error"]
        assert len(fake_db.updates) == 0

def test_start_activity_not_found(client):
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]
    activities_data = [] # Activity does not exist

    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data, activities_data=activities_data)

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/start-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "CS101",
                "activity_no": 999
            }
        )

        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "Activity does not exist" in response.json()["error"]

def test_start_activity_unauthorized(client):
    auth_data = [{"password": "secure123"}]
    courses_data = [{"id": "CS101", "instructor_email": "test@test.com"}]

    fake_db = FakeDB(auth_data=auth_data, courses_data=courses_data)

    with patch("app.services.get_db", return_value=fake_db):
        response = client.post("/instructor/start-activity",
            params={
                "email": "test@test.com",
                "password": "secure123",
                "course_id": "MATH202",
                "activity_no": 1
            }
        )

        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "Unauthorized" in response.json()["error"]
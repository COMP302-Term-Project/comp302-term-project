from fastapi.testclient import TestClient

from app.main import app
from tests.fake_supabase import FakeDB


def test_demo_reset_data_route_returns_ok_and_deletes_application_rows(monkeypatch):
    from app import services

    fake_db = FakeDB(
        auto_ids=True,
        score_logs=[{"id": 1}],
        conversation_state=[{"id": 1}],
        activities=[{"id": 1}],
        student_courses=[{"id": 1}],
        instructor_courses=[{"id": 1}],
        students=[{"id": 1}],
        instructors=[{"id": 1}],
        courses=[{"id": 1}],
    )
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = TestClient(app).post("/demo/reset-data")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "Demo data reset"}
    for table_name in [
        "conversation_state",
        "score_logs",
        "activities",
        "student_courses",
        "instructor_courses",
        "students",
        "instructors",
        "courses",
    ]:
        assert fake_db.tables[table_name] == []


def test_demo_seed_data_route_returns_frontend_demo_fields(monkeypatch):
    from app import services

    fake_db = FakeDB(auto_ids=True)
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = TestClient(app).post("/demo/seed-data")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["message"] == "Demo data seeded"

    demo = payload["demo"]
    assert demo["instructorA"] == {
        "id": 302001,
        "email": "instructor1@mef.edu.tr",
        "password": "pass123",
    }
    assert demo["instructorB"] == {
        "id": 302002,
        "email": "instructor2@mef.edu.tr",
        "password": "pass123",
    }
    assert demo["student1"] == {
        "id": 302101,
        "email": "comp302.term.project@gmail.com",
        "password": "pass123",
    }
    assert demo["student2"] == {
        "id": 302102,
        "email": "student2@mef.edu.tr",
        "password": "pass123",
    }
    assert demo["course1"] == {"id": 302201, "course_id": "SE101"}
    assert demo["course2"] == {"id": 302202, "course_id": "SE102"}
    assert demo["activity1"] == {"activity_no": 1, "status": "NOT_STARTED"}
    assert demo["activity2"] == {"activity_no": 2, "status": "NOT_STARTED"}

    assert fake_db.tables["score_logs"] == []
    assert fake_db.tables["conversation_state"] == []
    assert len(fake_db.tables["instructors"]) == 2
    assert len(fake_db.tables["students"]) == 2
    assert len(fake_db.tables["courses"]) == 2
    assert len(fake_db.tables["instructor_courses"]) == 2
    assert len(fake_db.tables["student_courses"]) == 2
    assert len(fake_db.tables["activities"]) == 2
    assert fake_db.tables["students"][0]["email"] == "comp302.term.project@gmail.com"
    assert fake_db.tables["activities"][0]["activity_no"] == 1
    assert fake_db.tables["activities"][0]["status"] == "NOT_STARTED"
    assert len(fake_db.tables["activities"][0]["learning_objectives"]) == 2
    assert fake_db.tables["activities"][1]["activity_no"] == 2
    assert fake_db.tables["activities"][1]["status"] == "NOT_STARTED"


def test_seeded_demo_authorization_boundaries(monkeypatch):
    from app import services

    fake_db = FakeDB(auto_ids=True)
    monkeypatch.setattr(services, "get_db", lambda: fake_db)
    services.seedDemoData()

    instructor_one = services.listMyCourses("instructor1@mef.edu.tr", "pass123")
    instructor_two_se101 = services.listActivities("instructor2@mef.edu.tr", "pass123", "SE101")
    student_one = services.studentLogin("comp302.term.project@gmail.com", "pass123")
    student_two_se101 = services.getActivity("student2@mef.edu.tr", "pass123", "SE101", 1)

    assert instructor_one["ok"] is True
    assert [course["course_id"] for course in instructor_one["courses"]] == ["SE101"]
    assert instructor_two_se101 == {"ok": False, "error": "Unauthorized"}
    assert student_one["ok"] is True
    assert student_two_se101 == {"ok": False, "error": "Unauthorized"}

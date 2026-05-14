from fastapi.testclient import TestClient

from app.main import app
from tests.fake_supabase import FakeDB


def test_demo_seed_data_route_invokes_rpc_and_returns_frontend_demo_fields(monkeypatch):
    from app import services

    fake_db = FakeDB(auto_ids=True)
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = TestClient(app).post("/demo/seed-data")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["message"] == "Demo data seeded"

    assert any(call["fn"] == "seed_demo_data" for call in fake_db.rpc_calls)

    demo = payload["demo"]
    assert demo["instructorA"]["email"] == "instructor1@mef.edu.tr"
    assert demo["instructorA"]["password"] == "pass123"
    assert isinstance(demo["instructorA"]["id"], int)
    assert demo["instructorB"]["email"] == "instructor2@mef.edu.tr"
    assert demo["student1"]["email"] == "comp302.term.project@gmail.com"
    assert demo["student2"]["email"] == "student2@mef.edu.tr"
    assert demo["course1"]["course_id"] == "SE101"
    assert demo["course2"]["course_id"] == "SE102"
    assert demo["activity1"] == {"activity_no": 1, "status": "NOT_STARTED"}
    assert demo["activity2"] == {"activity_no": 2, "status": "NOT_STARTED"}

    assert len(fake_db.tables["instructors"]) == 2
    assert len(fake_db.tables["students"]) == 2
    assert len(fake_db.tables["courses"]) == 2
    assert len(fake_db.tables["instructor_courses"]) == 2
    assert len(fake_db.tables["student_courses"]) == 2
    assert len(fake_db.tables["activities"]) == 2
    assert fake_db.tables["students"][0]["email"] == "comp302.term.project@gmail.com"
    assert len(fake_db.tables["activities"][0]["learning_objectives"]) == 2


def test_demo_seed_is_idempotent(monkeypatch):
    from app import services

    fake_db = FakeDB(auto_ids=True)
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    first = TestClient(app).post("/demo/seed-data")
    second = TestClient(app).post("/demo/seed-data")

    assert first.status_code == 200 and second.status_code == 200
    assert len(fake_db.tables["instructors"]) == 2
    assert len(fake_db.tables["students"]) == 2
    assert len(fake_db.tables["courses"]) == 2
    assert len(fake_db.tables["instructor_courses"]) == 2
    assert len(fake_db.tables["student_courses"]) == 2
    assert len(fake_db.tables["activities"]) == 2


def test_demo_reset_data_route_invokes_rpc_and_clears_demo_rows_only(monkeypatch):
    from app import services

    fake_db = FakeDB(auto_ids=True)
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    fake_db.tables["instructors"].append(
        {"id": 999001, "email": "non-demo-instructor@example.com", "full_name": "Other I", "password": "x"}
    )
    fake_db.tables["students"].append(
        {"id": 999101, "email": "non-demo-student@example.com", "full_name": "Other S", "password": "x"}
    )
    fake_db.tables["courses"].append(
        {"id": 999201, "course_id": "CS999", "course_name": "Other Course"}
    )

    TestClient(app).post("/demo/seed-data")

    assert len(fake_db.tables["instructors"]) == 3
    assert len(fake_db.tables["students"]) == 3
    assert len(fake_db.tables["courses"]) == 3

    response = TestClient(app).post("/demo/reset-data")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "Demo data reset"}
    assert any(call["fn"] == "delete_demo_data" for call in fake_db.rpc_calls)

    assert all(r["email"] != "instructor1@mef.edu.tr" for r in fake_db.tables["instructors"])
    assert all(r["email"] != "comp302.term.project@gmail.com" for r in fake_db.tables["students"])
    assert all(r["course_id"] != "SE101" for r in fake_db.tables["courses"])
    assert fake_db.tables["activities"] == []
    assert fake_db.tables["instructor_courses"] == []
    assert fake_db.tables["student_courses"] == []

    assert any(r["email"] == "non-demo-instructor@example.com" for r in fake_db.tables["instructors"])
    assert any(r["email"] == "non-demo-student@example.com" for r in fake_db.tables["students"])
    assert any(r["course_id"] == "CS999" for r in fake_db.tables["courses"])


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

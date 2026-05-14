from app import services
from app.main import app
from tests.fake_supabase import FakeDB


def make_instructor_db(mappings=None, enrollments=None, activity_rows=None, score_logs=None):
    return FakeDB(
        instructors=[{
            "id": 7,
            "email": "instructor@test.com",
            "full_name": "Test Instructor",
            "password": "secure123",
        }],
        students=[
            {
                "id": 9,
                "email": "student@test.com",
                "full_name": "Test Student",
                "password": "oldpass",
            },
            {
                "id": 10,
                "email": "other@test.com",
                "full_name": "Other Student",
                "password": "oldpass",
            },
        ],
        courses=[{"id": 101, "course_id": "CS101", "course_name": "Intro CS"}],
        instructor_courses=mappings if mappings is not None else [{"id": 1, "instructor_id": 7, "course_id": 101}],
        student_courses=enrollments if enrollments is not None else [{"id": 1, "student_id": 9, "course_id": 101}],
        activities=activity_rows if activity_rows is not None else [{
            "id": 55,
            "course_id": 101,
            "activity_no": 1,
            "activity_text": "Solve the warmup",
            "learning_objectives": ["Objective"],
            "status": "ENDED",
        }],
        score_logs=score_logs if score_logs is not None else [],
    )


def test_export_scores_returns_csv_for_authorized_course_activity(monkeypatch):
    fake_db = make_instructor_db(score_logs=[
        {
            "id": 1,
            "student_id": 9,
            "course_id": 101,
            "activity_no": 1,
            "score": 2.0,
            "meta": "Objective achieved",
            "created_at": "2026-05-13T10:00:00Z",
        },
        {
            "id": 2,
            "student_id": 10,
            "course_id": 101,
            "activity_no": 2,
            "score": 99.0,
            "meta": "Wrong activity",
            "created_at": "2026-05-13T11:00:00Z",
        },
    ])
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.exportScores("instructor@test.com", "secure123", "CS101", 1)

    assert result == {
        "ok": True,
        "csv": (
            "student_id,student_email,student_full_name,course_id,activity_no,score,meta,created_at\n"
            "9,student@test.com,Test Student,CS101,1,2.0,Objective achieved,2026-05-13T10:00:00Z\n"
        ),
    }


def test_export_scores_rejects_missing_activity(monkeypatch):
    fake_db = make_instructor_db(activity_rows=[])
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.exportScores("instructor@test.com", "secure123", "CS101", 999)

    assert result == {"ok": False, "error": "Activity does not exist"}


def test_export_scores_rejects_unauthorized_instructor(monkeypatch):
    fake_db = make_instructor_db(mappings=[])
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.exportScores("instructor@test.com", "secure123", "CS101", 1)

    assert result == {"ok": False, "error": "Unauthorized"}


def test_reset_student_password_updates_enrolled_student(monkeypatch):
    fake_db = make_instructor_db()
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.resetStudentPassword(
        "instructor@test.com",
        "secure123",
        "CS101",
        "Student@Test.com",
        "newpass",
    )

    assert result == {"ok": True, "message": "Student password reset"}
    assert fake_db.tables["students"][0]["password"] == "newpass"
    assert fake_db.tables["students"][1]["password"] == "oldpass"


def test_reset_student_password_rejects_student_outside_course(monkeypatch):
    fake_db = make_instructor_db(enrollments=[])
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.resetStudentPassword(
        "instructor@test.com",
        "secure123",
        "CS101",
        "student@test.com",
        "newpass",
    )

    assert result == {"ok": False, "error": "Student is not enrolled in this course"}
    assert fake_db.tables["students"][0]["password"] == "oldpass"


def test_reset_student_password_validates_new_password(monkeypatch):
    fake_db = make_instructor_db()
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    result = services.resetStudentPassword(
        "instructor@test.com",
        "secure123",
        "CS101",
        "student@test.com",
        "",
    )

    assert result == {"ok": False, "error": "new_password is required"}
    assert fake_db.tables["students"][0]["password"] == "oldpass"


def test_phase1_missing_instructor_routes_are_registered():
    instructor_routes = {
        route.path
        for route in app.routes
        if route.path.startswith("/instructor/")
    }

    assert "/instructor/export-scores" in instructor_routes
    assert "/instructor/reset-student-password" in instructor_routes

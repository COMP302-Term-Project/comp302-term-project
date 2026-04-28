from app import services


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQueryBuilder:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self.filters = {}

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def execute(self):
        rows = self.db.tables.get(self.table_name, [])
        matched_rows = [
            row
            for row in rows
            if all(row.get(column) == value for column, value in self.filters.items())
        ]
        return FakeResponse(matched_rows)


class FakeDB:
    def __init__(self, courses=None, instructor_courses=None, student_courses=None):
        self.tables = {
            "courses": courses or [],
            "instructor_courses": instructor_courses or [],
            "student_courses": student_courses or [],
        }

    def table(self, name):
        return FakeQueryBuilder(self, name)


def test_authorize_instructor_course_access_rejects_unmapped_course():
    db = FakeDB(
        courses=[{"id": 101, "course_id": "SE101", "course_name": "Software Engineering"}],
        instructor_courses=[{"id": 1, "instructor_id": 7, "course_id": 202}],
    )
    identity = {
        "ok": True,
        "instructor": {"id": 7, "email": "instructor@test.com", "full_name": "Test Instructor"},
    }

    response = services._authorize_instructor_course_access(db, identity, "SE101")

    assert response == {"ok": False, "error": "Unauthorized"}


def test_authorize_student_course_access_rejects_unmapped_course():
    db = FakeDB(
        courses=[{"id": 101, "course_id": "SE101", "course_name": "Software Engineering"}],
        student_courses=[{"id": 1, "student_id": 9, "course_id": 202}],
    )
    identity = {
        "ok": True,
        "student": {"id": 9, "email": "student@test.com", "full_name": "Test Student"},
    }

    response = services._authorize_student_course_access(db, identity, "SE101")

    assert response == {"ok": False, "error": "Unauthorized"}


def test_authorize_instructor_course_access_rejects_student_identity():
    db = FakeDB(
        courses=[{"id": 101, "course_id": "SE101", "course_name": "Software Engineering"}],
        instructor_courses=[{"id": 1, "instructor_id": 7, "course_id": 101}],
    )
    identity = {
        "ok": True,
        "student": {"id": 9, "email": "student@test.com", "full_name": "Test Student"},
    }

    response = services._authorize_instructor_course_access(db, identity, "SE101")

    assert response == {"ok": False, "error": "Invalid credentials"}


def test_authorize_student_course_access_rejects_instructor_identity():
    db = FakeDB(
        courses=[{"id": 101, "course_id": "SE101", "course_name": "Software Engineering"}],
        student_courses=[{"id": 1, "student_id": 9, "course_id": 101}],
    )
    identity = {
        "ok": True,
        "instructor": {"id": 7, "email": "instructor@test.com", "full_name": "Test Instructor"},
    }

    response = services._authorize_student_course_access(db, identity, "SE101")

    assert response == {"ok": False, "error": "Invalid credentials"}


def test_authorize_instructor_course_access_returns_course_not_found_result():
    db = FakeDB(courses=[])
    identity = {
        "ok": True,
        "instructor": {"id": 7, "email": "instructor@test.com", "full_name": "Test Instructor"},
    }
    expected = services._resolve_course(db, "MISSING101")

    response = services._authorize_instructor_course_access(db, identity, "MISSING101")

    assert response == expected


def test_authorize_student_course_access_returns_course_not_found_result():
    db = FakeDB(courses=[])
    identity = {
        "ok": True,
        "student": {"id": 9, "email": "student@test.com", "full_name": "Test Student"},
    }
    expected = services._resolve_course(db, "MISSING101")

    response = services._authorize_student_course_access(db, identity, "MISSING101")

    assert response == expected

from app import services


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQueryBuilder:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self.filters = {}
        self.update_data = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def update(self, data):
        self.update_data = data
        return self

    def execute(self):
        rows = self.db.tables.get(self.table_name, [])
        matched_rows = [
            row for row in rows
            if all(row.get(column) == value for column, value in self.filters.items())
        ]

        if self.update_data is not None:
            for row in matched_rows:
                row.update(self.update_data)
            self.db.updates.append(
                {
                    "table": self.table_name,
                    "filters": dict(self.filters),
                    "data": dict(self.update_data),
                }
            )

        return FakeResponse(matched_rows)


class FakeDB:
    def __init__(self, students=None):
        self.tables = {"students": students or []}
        self.updates = []

    def table(self, name):
        return FakeQueryBuilder(self, name)


def test_student_login_success(monkeypatch):
    fake_db = FakeDB(
        students=[
            {
                "id": 1,
                "email": "student@test.com",
                "full_name": "Test Student",
                "password": "secure123",
            }
        ]
    )
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.studentLogin(" Student@Test.com ", "secure123")

    assert response == {
        "ok": True,
        "student": {
            "id": 1,
            "email": "student@test.com",
            "full_name": "Test Student",
        },
    }


def test_student_login_invalid_credentials(monkeypatch):
    fake_db = FakeDB(
        students=[
            {
                "id": 1,
                "email": "student@test.com",
                "full_name": "Test Student",
                "password": "secure123",
            }
        ]
    )
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.studentLogin("student@test.com", "wrong")

    assert response["ok"] is False
    assert "error" in response


def test_change_student_password_success(monkeypatch):
    fake_db = FakeDB(
        students=[
            {
                "id": 1,
                "email": "student@test.com",
                "full_name": "Test Student",
                "password": "oldpass",
            }
        ]
    )
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.changeStudentPassword(
        "student@test.com",
        "ignored-for-compatibility",
        "newpass",
        "oldpass",
    )

    assert response == {"ok": True}
    assert fake_db.tables["students"][0]["password"] == "newpass"
    assert fake_db.updates == [
        {
            "table": "students",
            "filters": {"email": "student@test.com"},
            "data": {"password": "newpass"},
        }
    ]


def test_change_student_password_wrong_old_password(monkeypatch):
    fake_db = FakeDB(
        students=[
            {
                "id": 1,
                "email": "student@test.com",
                "full_name": "Test Student",
                "password": "oldpass",
            }
        ]
    )
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.changeStudentPassword(
        "student@test.com",
        "ignored-for-compatibility",
        "newpass",
        "wrongold",
    )

    assert response["ok"] is False
    assert "error" in response
    assert fake_db.tables["students"][0]["password"] == "oldpass"
    assert fake_db.updates == []


def test_change_student_password_missing_old_password():
    response = services.changeStudentPassword(
        "student@test.com",
        "ignored-for-compatibility",
        "newpass",
        "",
    )

    assert response == {"ok": False, "error": "old_password is required"}


def test_change_student_password_missing_new_password():
    response = services.changeStudentPassword(
        "student@test.com",
        "ignored-for-compatibility",
        " ",
        "oldpass",
    )

    assert response == {"ok": False, "error": "new_password is required"}


def test_set_student_password_success(monkeypatch):
    fake_db = FakeDB(
        students=[
            {
                "id": 1,
                "email": "student@test.com",
                "full_name": "Test Student",
                "password": "oldpass",
            }
        ]
    )
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.setStudentPassword(" student@test.com ", "newpass")

    assert response == {"ok": True}
    assert fake_db.tables["students"][0]["password"] == "newpass"


def test_set_student_password_student_not_found(monkeypatch):
    fake_db = FakeDB(students=[])
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.setStudentPassword("missing@test.com", "newpass")

    assert response == {"ok": False, "error": "Student not found"}


def test_student_login_route_returns_service_result(client, monkeypatch):
    expected = {"ok": True, "student": {"email": "student@test.com"}}

    def fake_login(email, password):
        assert email == "student@test.com"
        assert password == "secure123"
        return expected

    monkeypatch.setattr(services, "studentLogin", fake_login)

    response = client.post(
        "/student/login",
        params={"email": "student@test.com", "password": "secure123"},
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_change_student_password_route_returns_service_result(client, monkeypatch):
    expected = {"ok": True}

    def fake_change(email, password, new_password, old_password):
        assert email == "student@test.com"
        assert password == "current"
        assert new_password == "new"
        assert old_password == "old"
        return expected

    monkeypatch.setattr(services, "changeStudentPassword", fake_change)

    response = client.post(
        "/student/change-password",
        params={
            "email": "student@test.com",
            "password": "current",
            "new_password": "new",
            "old_password": "old",
        },
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_set_student_password_route_returns_service_result(client, monkeypatch):
    expected = {"ok": True}

    def fake_set(email, password):
        assert email == "student@test.com"
        assert password == "newpass"
        return expected

    monkeypatch.setattr(services, "setStudentPassword", fake_set)

    response = client.post(
        "/student/set-password",
        params={"email": "student@test.com", "password": "newpass"},
    )

    assert response.status_code == 200
    assert response.json() == expected

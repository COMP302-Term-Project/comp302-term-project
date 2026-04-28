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
    def __init__(self, instructors=None):
        self.tables = {"instructors": instructors or []}
        self.updates = []

    def table(self, name):
        return FakeQueryBuilder(self, name)


def test_instructor_login_success(monkeypatch):
    fake_db = FakeDB(
        instructors=[
            {
                "id": 1,
                "email": "instructor@test.com",
                "full_name": "Test Instructor",
                "password": "secure123",
            }
        ]
    )
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.instructorLogin(" Instructor@Test.com ", "secure123")

    assert response == {
        "ok": True,
        "instructor": {
            "id": 1,
            "email": "instructor@test.com",
            "full_name": "Test Instructor",
        },
    }


def test_instructor_login_invalid_credentials(monkeypatch):
    fake_db = FakeDB(
        instructors=[
            {
                "id": 1,
                "email": "instructor@test.com",
                "full_name": "Test Instructor",
                "password": "secure123",
            }
        ]
    )
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.instructorLogin("instructor@test.com", "wrong")

    assert response["ok"] is False
    assert "error" in response


def test_change_instructor_password_success(monkeypatch):
    fake_db = FakeDB(
        instructors=[
            {
                "id": 1,
                "email": "instructor@test.com",
                "full_name": "Test Instructor",
                "password": "oldpass",
            }
        ]
    )
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.changeInstructorPassword(
        "instructor@test.com",
        "ignored-for-compatibility",
        "oldpass",
        "newpass",
    )

    assert response == {"ok": True}
    assert fake_db.tables["instructors"][0]["password"] == "newpass"
    assert fake_db.updates == [
        {
            "table": "instructors",
            "filters": {"email": "instructor@test.com"},
            "data": {"password": "newpass"},
        }
    ]


def test_change_instructor_password_missing_old_password():
    response = services.changeInstructorPassword(
        "instructor@test.com",
        "ignored-for-compatibility",
        "",
        "newpass",
    )

    assert response == {"ok": False, "error": "old_password is required"}


def test_change_instructor_password_missing_new_password():
    response = services.changeInstructorPassword(
        "instructor@test.com",
        "ignored-for-compatibility",
        "oldpass",
        " ",
    )

    assert response == {"ok": False, "error": "new_password is required"}


def test_set_instructor_password_success(monkeypatch):
    fake_db = FakeDB(
        instructors=[
            {
                "id": 1,
                "email": "instructor@test.com",
                "full_name": "Test Instructor",
                "password": "oldpass",
            }
        ]
    )
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.setInstructorPassword(" instructor@test.com ", "newpass")

    assert response == {"ok": True}
    assert fake_db.tables["instructors"][0]["password"] == "newpass"


def test_set_instructor_password_instructor_not_found(monkeypatch):
    fake_db = FakeDB(instructors=[])
    monkeypatch.setattr(services, "get_db", lambda: fake_db)

    response = services.setInstructorPassword("missing@test.com", "newpass")

    assert response == {"ok": False, "error": "Instructor not found"}


def test_instructor_login_route_returns_service_result(client, monkeypatch):
    expected = {"ok": True, "instructor": {"email": "instructor@test.com"}}

    def fake_login(email, password):
        assert email == "instructor@test.com"
        assert password == "secure123"
        return expected

    monkeypatch.setattr(services, "instructorLogin", fake_login)

    response = client.post(
        "/instructor/login",
        params={"email": "instructor@test.com", "password": "secure123"},
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_change_instructor_password_route_returns_service_result(client, monkeypatch):
    expected = {"ok": True}

    def fake_change(email, password, old_password, new_password):
        assert email == "instructor@test.com"
        assert password == "current"
        assert old_password == "old"
        assert new_password == "new"
        return expected

    monkeypatch.setattr(services, "changeInstructorPassword", fake_change)

    response = client.post(
        "/instructor/change-password",
        params={
            "email": "instructor@test.com",
            "password": "current",
            "old_password": "old",
            "new_password": "new",
        },
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_set_instructor_password_route_returns_service_result(client, monkeypatch):
    expected = {"ok": True}

    def fake_set(email, password=None):
        assert email == "instructor@test.com"
        assert password == "newpass"
        return expected

    monkeypatch.setattr(services, "setInstructorPassword", fake_set)

    response = client.post(
        "/instructor/set-password",
        params={"email": "instructor@test.com", "password": "newpass"},
    )

    assert response.status_code == 200
    assert response.json() == expected

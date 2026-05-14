class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQueryBuilder:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self.filters = {}
        self.range_filters = []
        self.insert_data = None
        self.update_data = None
        self.delete_requested = False
        self.order_column = None
        self.order_desc = False
        self.limit_count = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def gte(self, column, value):
        self.range_filters.append((column, ">=", value))
        return self

    def order(self, column, desc=False):
        self.order_column = column
        self.order_desc = desc
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def insert(self, data):
        self.insert_data = dict(data)
        return self

    def upsert(self, data, on_conflict=None):
        self.insert_data = dict(data)
        self._upsert_on_conflict = on_conflict
        return self

    def update(self, data):
        self.update_data = dict(data)
        return self

    def delete(self):
        self.delete_requested = True
        return self

    def execute(self):
        rows = self.db.tables.setdefault(self.table_name, [])

        if self.insert_data is not None:
            on_conflict = getattr(self, "_upsert_on_conflict", None)
            if on_conflict:
                conflict_cols = [c.strip() for c in on_conflict.split(",")]
                for row in rows:
                    if all(row.get(col) == self.insert_data.get(col) for col in conflict_cols):
                        row.update(self.insert_data)
                        self.db.updates.append({"table": self.table_name, "filters": {c: self.insert_data.get(c) for c in conflict_cols}, "data": dict(self.insert_data)})
                        return FakeResponse([row])
            inserted = dict(self.insert_data)
            if self.db.auto_ids and "id" not in inserted:
                inserted["id"] = self.db.next_id(self.table_name)
            rows.append(inserted)
            self.db.inserts.append({"table": self.table_name, "data": dict(inserted)})
            return FakeResponse([inserted])

        matched_rows = []
        for row in rows:
            if not all(row.get(column) == value for column, value in self.filters.items()):
                continue
            if not all(self._matches_range(row, column, op, value) for column, op, value in self.range_filters):
                continue
            matched_rows.append(row)

        if self.order_column is not None:
            matched_rows = sorted(
                matched_rows,
                key=lambda row: row.get(self.order_column, 0),
                reverse=self.order_desc,
            )

        if self.limit_count is not None:
            matched_rows = matched_rows[:self.limit_count]

        if self.delete_requested:
            self.db.tables[self.table_name] = [
                row
                for row in rows
                if row not in matched_rows
            ]
            self.db.deletes.append(
                {
                    "table": self.table_name,
                    "filters": dict(self.filters),
                    "range_filters": list(self.range_filters),
                }
            )
            return FakeResponse(matched_rows)

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

    def _matches_range(self, row, column, op, value):
        current = row.get(column)
        if current is None:
            return False
        if op == ">=":
            return current >= value
        return False


_DEMO_INSTRUCTORS = (
    ("instructor1@mef.edu.tr", "Instructor A"),
    ("instructor2@mef.edu.tr", "Instructor B"),
)
_DEMO_STUDENTS = (
    ("comp302.term.project@gmail.com", "Student One"),
    ("student2@mef.edu.tr", "Student Two"),
)
_DEMO_COURSES = (
    ("SE101", "Software Engineering 101"),
    ("SE102", "Software Engineering 102"),
)
_DEMO_ACTIVITIES = (
    (
        1,
        "Explain the concept of software requirements and give one clear example.",
        ["Define software requirements", "Give one example of a functional requirement"],
    ),
    (
        2,
        "Explain the difference between functional and non-functional requirements.",
        ["Define functional requirements", "Define non-functional requirements"],
    ),
)
_DEMO_PASSWORD = "pass123"


def _simulate_seed_demo_data(db):
    def _upsert(table, match_key, row):
        for existing in db.tables[table]:
            if existing.get(match_key) == row[match_key]:
                existing.update({k: v for k, v in row.items() if k != "id"})
                return existing
        new_row = dict(row)
        new_row.setdefault("id", db.next_id(table))
        db.tables[table].append(new_row)
        return new_row

    instructor_ids = [
        _upsert("instructors", "email", {"email": email, "full_name": name, "password": _DEMO_PASSWORD})["id"]
        for email, name in _DEMO_INSTRUCTORS
    ]
    student_ids = [
        _upsert("students", "email", {"email": email, "full_name": name, "password": _DEMO_PASSWORD})["id"]
        for email, name in _DEMO_STUDENTS
    ]
    course_ids = [
        _upsert("courses", "course_id", {"course_id": code, "course_name": name})["id"]
        for code, name in _DEMO_COURSES
    ]

    def _ensure_mapping(table, key_a, val_a, key_b, val_b):
        for row in db.tables[table]:
            if row.get(key_a) == val_a and row.get(key_b) == val_b:
                return
        db.tables[table].append({"id": db.next_id(table), key_a: val_a, key_b: val_b})

    _ensure_mapping("instructor_courses", "instructor_id", instructor_ids[0], "course_id", course_ids[0])
    _ensure_mapping("instructor_courses", "instructor_id", instructor_ids[1], "course_id", course_ids[1])
    _ensure_mapping("student_courses", "student_id", student_ids[0], "course_id", course_ids[0])
    _ensure_mapping("student_courses", "student_id", student_ids[1], "course_id", course_ids[1])

    for activity_no, text, los in _DEMO_ACTIVITIES:
        existing = next(
            (
                row
                for row in db.tables["activities"]
                if row.get("course_id") == course_ids[0] and row.get("activity_no") == activity_no
            ),
            None,
        )
        if existing:
            existing.update(
                {
                    "activity_text": text,
                    "learning_objectives": list(los),
                    "status": "NOT_STARTED",
                }
            )
        else:
            db.tables["activities"].append(
                {
                    "id": db.next_id("activities"),
                    "course_id": course_ids[0],
                    "activity_no": activity_no,
                    "activity_text": text,
                    "learning_objectives": list(los),
                    "status": "NOT_STARTED",
                }
            )


def _simulate_delete_demo_data(db):
    demo_instructor_emails = {email for email, _ in _DEMO_INSTRUCTORS}
    demo_student_emails = {email for email, _ in _DEMO_STUDENTS}
    demo_course_codes = {code for code, _ in _DEMO_COURSES}

    instructor_ids = {row["id"] for row in db.tables["instructors"] if row.get("email") in demo_instructor_emails}
    student_ids = {row["id"] for row in db.tables["students"] if row.get("email") in demo_student_emails}
    course_ids = {row["id"] for row in db.tables["courses"] if row.get("course_id") in demo_course_codes}

    def _filter_out(table, predicate):
        db.tables[table] = [row for row in db.tables[table] if not predicate(row)]

    _filter_out("score_logs", lambda r: r.get("student_id") in student_ids or r.get("course_id") in course_ids)
    _filter_out("conversation_state", lambda r: r.get("student_id") in student_ids or r.get("course_id") in course_ids)
    _filter_out("activities", lambda r: r.get("course_id") in course_ids)
    _filter_out("student_courses", lambda r: r.get("student_id") in student_ids or r.get("course_id") in course_ids)
    _filter_out("instructor_courses", lambda r: r.get("instructor_id") in instructor_ids or r.get("course_id") in course_ids)
    _filter_out("students", lambda r: r.get("email") in demo_student_emails)
    _filter_out("instructors", lambda r: r.get("email") in demo_instructor_emails)
    _filter_out("courses", lambda r: r.get("course_id") in demo_course_codes)


_RPC_SIMULATORS = {
    "seed_demo_data": _simulate_seed_demo_data,
    "delete_demo_data": _simulate_delete_demo_data,
}


class FakeRpcBuilder:
    def __init__(self, db, fn_name, params):
        self.db = db
        self.fn_name = fn_name
        self.params = params

    def execute(self):
        self.db.rpc_calls.append({"fn": self.fn_name, "params": dict(self.params)})
        simulator = _RPC_SIMULATORS.get(self.fn_name)
        if simulator is not None:
            simulator(self.db)
        return FakeResponse([{"ok": True}])


class FakeDB:
    def __init__(self, auto_ids=False, **tables):
        self.tables = {
            "instructors": [],
            "students": [],
            "courses": [],
            "instructor_courses": [],
            "student_courses": [],
            "activities": [],
            "conversation_state": [],
            "score_logs": [],
        }
        self.tables.update({name: rows for name, rows in tables.items()})
        self.inserts = []
        self.updates = []
        self.deletes = []
        self.rpc_calls = []
        self.auto_ids = auto_ids
        self._next_ids = {
            name: max([row.get("id", 0) for row in rows] or [0]) + 1
            for name, rows in self.tables.items()
        }

    def next_id(self, table_name):
        next_value = self._next_ids.get(table_name, 1)
        self._next_ids[table_name] = next_value + 1
        return next_value

    def table(self, name):
        return FakeQueryBuilder(self, name)

    def rpc(self, fn_name, params):
        return FakeRpcBuilder(self, fn_name, params)

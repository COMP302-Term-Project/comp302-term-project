class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQueryBuilder:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self.filters = {}
        self.insert_data = None
        self.update_data = None
        self.order_column = None
        self.order_desc = False
        self.limit_count = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self.filters[column] = value
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
        # For FakeDB: treat upsert as an insert/update by on_conflict column(s).
        # We store in insert_data and let execute() handle it.
        self.insert_data = dict(data)
        self._upsert_on_conflict = on_conflict
        return self

    def update(self, data):
        self.update_data = dict(data)
        return self

    def execute(self):
        rows = self.db.tables.setdefault(self.table_name, [])

        if self.insert_data is not None:
            # Handle upsert: if on_conflict columns are set, update existing row
            on_conflict = getattr(self, "_upsert_on_conflict", None)
            if on_conflict:
                conflict_cols = [c.strip() for c in on_conflict.split(",")]
                for row in rows:
                    if all(row.get(col) == self.insert_data.get(col) for col in conflict_cols):
                        row.update(self.insert_data)
                        self.db.updates.append({"table": self.table_name, "filters": {c: self.insert_data.get(c) for c in conflict_cols}, "data": dict(self.insert_data)})
                        return FakeResponse([row])
            rows.append(self.insert_data)
            self.db.inserts.append({"table": self.table_name, "data": dict(self.insert_data)})
            return FakeResponse([self.insert_data])

        matched_rows = [
            row
            for row in rows
            if all(row.get(column) == value for column, value in self.filters.items())
        ]

        if self.order_column is not None:
            matched_rows = sorted(
                matched_rows,
                key=lambda row: row.get(self.order_column, 0),
                reverse=self.order_desc,
            )

        if self.limit_count is not None:
            matched_rows = matched_rows[:self.limit_count]

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
    def __init__(self, **tables):
        self.tables = {
            "instructors": [],
            "students": [],
            "courses": [],
            "instructor_courses": [],
            "student_courses": [],
            "activities": [],
            "conversation_state": [],  # S2-T05 [US-J]
        }
        self.tables.update({name: rows for name, rows in tables.items()})
        self.inserts = []
        self.updates = []

    def table(self, name):
        return FakeQueryBuilder(self, name)

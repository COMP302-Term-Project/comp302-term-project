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


class FakeRpcBuilder:
    def __init__(self, db, fn_name, params):
        self.db = db
        self.fn_name = fn_name
        self.params = params

    def execute(self):
        self.db.rpc_calls.append({"fn": self.fn_name, "params": dict(self.params)})
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

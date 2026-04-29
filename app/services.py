import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _normalize_email(email: str | None) -> str:
    if email is None:
        return ""
    return email.strip().lower()


def _validate_credentials(email: str | None, password: str | None) -> dict[str, object]:
    normalized_email = _normalize_email(email)

    if _is_blank(normalized_email):
        return {"ok": False, "error": "email is required"}

    if _is_blank(password):
        return {"ok": False, "error": "password is required"}

    return {"ok": True, "email": normalized_email}


def _authenticate_instructor(db, email, password):
    credentials = _validate_credentials(email, password)
    if not credentials["ok"]:
        return credentials

    normalized_email = str(credentials["email"])
    auth_resp = db.table("instructors").select("id,email,full_name,password").eq("email", normalized_email).execute()

    if not auth_resp.data or auth_resp.data[0].get("password") != password:
        return {"ok": False, "error": "Invalid credentials"}

    instructor = auth_resp.data[0]
    return {
        "ok": True,
        "instructor": {
            "id": instructor.get("id"),
            "email": instructor.get("email"),
            "full_name": instructor.get("full_name"),
        },
    }


def _authenticate_student(db, email, password):
    credentials = _validate_credentials(email, password)
    if not credentials["ok"]:
        return credentials

    normalized_email = str(credentials["email"])
    auth_resp = db.table("students").select("id,email,full_name,password").eq("email", normalized_email).execute()

    if not auth_resp.data or auth_resp.data[0].get("password") != password:
        return {"ok": False, "error": "Invalid credentials"}

    student = auth_resp.data[0]
    return {
        "ok": True,
        "student": {
            "id": student.get("id"),
            "email": student.get("email"),
            "full_name": student.get("full_name"),
        },
    }


def _resolve_course(db, course_id):
    if _is_blank(course_id):
        return {"ok": False, "error": "Course not found"}

    course_code = str(course_id).strip()
    course_resp = db.table("courses").select("id,course_id,course_name").eq("course_id", course_code).execute()

    if not course_resp.data:
        return {"ok": False, "error": "Course not found"}

    return {"ok": True, "course": course_resp.data[0]}


def _authorize_instructor_course_access(db, identity, course_id):
    if not identity or not identity.get("ok") or not identity.get("instructor"):
        return {"ok": False, "error": "Invalid credentials"}

    instructor = identity["instructor"]
    if _is_blank(instructor.get("id")):
        return {"ok": False, "error": "Invalid credentials"}

    course_check = _resolve_course(db, course_id)
    if not course_check["ok"]:
        return course_check

    course = course_check["course"]
    access_resp = (
        db.table("instructor_courses")
        .select("id")
        .eq("instructor_id", instructor["id"])
        .eq("course_id", course["id"])
        .execute()
    )

    if not access_resp.data:
        return {"ok": False, "error": "Unauthorized"}

    return {"ok": True, "course": course, "instructor": instructor}


def _authorize_student_course_access(db, identity, course_id):
    if not identity or not identity.get("ok") or not identity.get("student"):
        return {"ok": False, "error": "Invalid credentials"}

    student = identity["student"]
    if _is_blank(student.get("id")):
        return {"ok": False, "error": "Invalid credentials"}

    course_check = _resolve_course(db, course_id)
    if not course_check["ok"]:
        return course_check

    course = course_check["course"]
    access_resp = (
        db.table("student_courses")
        .select("id")
        .eq("student_id", student["id"])
        .eq("course_id", course["id"])
        .execute()
    )

    if not access_resp.data:
        return {"ok": False, "error": "Unauthorized"}

    return {"ok": True, "course": course, "student": student}


def get_db() -> Client:
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not supabase_service_role_key:
        raise ValueError("Supabase environment variables are missing")
    return create_client(supabase_url, supabase_service_role_key)


# ==========================================
# STUDENT APIs
# ==========================================

# --- Student Auth APIs ---
def studentLogin(email: str, password: str) -> dict:
    db = get_db()
    return _authenticate_student(db, email, password)


# --- Student Password APIs ---
def changeStudentPassword(email: str, password: str, new_password: str, old_password: str) -> dict:
    normalized_email = _normalize_email(email)
    if _is_blank(normalized_email):
        return {"ok": False, "error": "email is required"}

    if _is_blank(password):
        return {"ok": False, "error": "password is required"}

    if _is_blank(old_password):
        return {"ok": False, "error": "old_password is required"}

    if _is_blank(new_password):
        return {"ok": False, "error": "new_password is required"}

    db = get_db()
    auth_resp = db.table("students").select("password").eq("email", normalized_email).execute()

    if not auth_resp.data:
        return {"ok": False, "error": "Invalid credentials"}

    current_password = auth_resp.data[0].get("password")
    if current_password != password or current_password != old_password:
        return {"ok": False, "error": "Invalid credentials"}

    db.table("students").update({"password": new_password}).eq("email", normalized_email).execute()
    return {"ok": True}


def setStudentPassword(email: str, password: str) -> dict:
    credentials = _validate_credentials(email, password)
    if not credentials["ok"]:
        return credentials

    normalized_email = str(credentials["email"])
    db = get_db()
    student_resp = db.table("students").select("id,password").eq("email", normalized_email).execute()

    if not student_resp.data:
        return {"ok": False, "error": "Student not found"}

    if not _is_blank(student_resp.data[0].get("password")):
        return {"ok": False, "error": "Password already set"}

    db.table("students").update({"password": password}).eq("email", normalized_email).execute()
    return {"ok": True}


# --- Main Student APIs ---
def getActivity(email: str, password: str, course_id: str, activity_no: int) -> dict:
    raise NotImplementedError


def logScore(email: str, password: str, course_id: str, activity_no: int, score: float, meta: str | None = None) -> dict:
    raise NotImplementedError


# ==========================================
# INSTRUCTOR APIs
# ==========================================

# --- Instructor Auth APIs ---
def instructorLogin(email: str, password: str) -> dict:
    db = get_db()
    return _authenticate_instructor(db, email, password)


# --- Instructor Password APIs ---
def changeInstructorPassword(email: str, password: str, old_password: str, new_password: str) -> dict:
    normalized_email = _normalize_email(email)
    if _is_blank(normalized_email):
        return {"ok": False, "error": "email is required"}

    if _is_blank(password):
        return {"ok": False, "error": "password is required"}

    if _is_blank(old_password):
        return {"ok": False, "error": "old_password is required"}

    if _is_blank(new_password):
        return {"ok": False, "error": "new_password is required"}

    db = get_db()
    auth_resp = db.table("instructors").select("password").eq("email", normalized_email).execute()

    if not auth_resp.data:
        return {"ok": False, "error": "Invalid credentials"}

    current_password = auth_resp.data[0].get("password")
    if current_password != password or current_password != old_password:
        return {"ok": False, "error": "Invalid credentials"}

    db.table("instructors").update({"password": new_password}).eq("email", normalized_email).execute()
    return {"ok": True}


def setInstructorPassword(email: str, password: str | None = None) -> dict:
    credentials = _validate_credentials(email, password)
    if not credentials["ok"]:
        return credentials

    normalized_email = str(credentials["email"])
    db = get_db()
    instructor_resp = db.table("instructors").select("id,password").eq("email", normalized_email).execute()

    if not instructor_resp.data:
        return {"ok": False, "error": "Instructor not found"}

    if not _is_blank(instructor_resp.data[0].get("password")):
        return {"ok": False, "error": "Password already set"}

    db.table("instructors").update({"password": password}).eq("email", normalized_email).execute()
    return {"ok": True}


# --- Main APIs for Instructor ---

# [T16] Implement and route listMyCourses
def listMyCourses(email: str, password: str) -> dict:
    db = get_db()
    identity = _authenticate_instructor(db, email, password)
    if not identity["ok"]:
        return identity

    instructor_id = identity["instructor"]["id"]
    mappings_resp = db.table("instructor_courses").select("course_id").eq("instructor_id", instructor_id).execute()

    courses = []
    for mapping in mappings_resp.data:
        course_resp = db.table("courses").select("id,course_id,course_name").eq("id", mapping.get("course_id")).execute()
        if course_resp.data:
            courses.append(course_resp.data[0])

    return {"ok": True, "courses": courses}


# [T18] Implement and route listActivities
def listActivities(email: str, password: str, course_id: str) -> dict:
    db = get_db()
    identity = _authenticate_instructor(db, email, password)
    if not identity["ok"]:
        return identity

    auth_check = _authorize_instructor_course_access(db, identity, course_id)
    if not auth_check["ok"]:
        return auth_check

    course = auth_check["course"]
    activities_resp = db.table("activities").select("*").eq("course_id", course["id"]).order("activity_no").execute()
    return {"ok": True, "activities": activities_resp.data}


def createActivity(
    email: str,
    password: str,
    course_id: str,
    activity_text: str,
    learning_objectives: list[str],
    activity_no_optional: int | None = None
) -> dict[str, object]:
    db = get_db()
    identity = _authenticate_instructor(db, email, password)
    if not identity["ok"]:
        return identity

    if _is_blank(activity_text):
        return {"ok": False, "error": "activity_text is required"}

    if not isinstance(learning_objectives, list) or not learning_objectives:
        return {"ok": False, "error": "learning_objectives must be a non-empty list"}

    if any(_is_blank(objective) for objective in learning_objectives):
        return {"ok": False, "error": "learning_objectives must be a non-empty list"}

    if activity_no_optional is not None and (not isinstance(activity_no_optional, int) or activity_no_optional < 1):
        return {"ok": False, "error": "activity_no_optional must be a positive integer"}

    auth_check = _authorize_instructor_course_access(db, identity, course_id)
    if not auth_check["ok"]:
        return auth_check

    course = auth_check["course"]

    if activity_no_optional is None:
        res = db.table("activities").select("activity_no").eq("course_id", course["id"]).order("activity_no", desc=True).limit(1).execute()
        if res.data:
            activity_no = res.data[0].get("activity_no", 0) + 1
        else:
            activity_no = 1
    else:
        activity_no = activity_no_optional

    duplicate_resp = db.table("activities").select("id").eq("course_id", course["id"]).eq("activity_no", activity_no).execute()
    if duplicate_resp.data:
        return {"ok": False, "error": "Activity number already exists"}
        
    activity_data = {
        "course_id": course["id"],
        "activity_no": activity_no,
        "activity_text": activity_text,
        "learning_objectives": learning_objectives
    }
    
    insert_res = db.table("activities").insert(activity_data).execute()
    
    if insert_res.data:
        return {"ok": True, "activity": insert_res.data[0]}
    return {"ok": False, "error": "Failed to create activity"}


def _verify_instructor_course_access(email: str, password: str, course_id: str) -> dict:
    db = get_db()
    identity = _authenticate_instructor(db, email, password)
    if not identity["ok"]:
        return identity

    return _authorize_instructor_course_access(db, identity, course_id)

# S1-T22 [US-G]
def updateActivity(email: str, password: str, course_id: str, activity_no: int, patch: dict) -> dict:
    auth_check = _verify_instructor_course_access(email, password, course_id)
    if not auth_check.get("ok"):
        return auth_check

    if not patch:
        return {"ok": False, "error": "Empty patch rejected"}

    allowed_fields = ["activity_text", "learning_objectives"]
    update_data = {k: v for k, v in patch.items() if k in allowed_fields}

    if not update_data:
        return {"ok": False, "error": "No allowed fields in patch"}

    db = get_db()
    course = auth_check["course"]
    exist = db.table("activities").select("*").eq("course_id", course["id"]).eq("activity_no", activity_no).execute()
    if not exist.data:
        return {"ok": False, "error": "Activity does not exist"}

    if exist.data[0].get("status") != "NOT_STARTED":
        return {"ok": False, "error": "Cannot update activity that has started or ended"}

    db.table("activities").update(update_data).eq("course_id", course["id"]).eq("activity_no", activity_no).execute()
    return {"ok": True, "message": "Activity updated"}


def _changeActivityState(email: str, password: str, course_id: str, activity_no: int, new_state: str, allowed_previous_states: list[str]) -> dict:
    auth_check = _verify_instructor_course_access(email, password, course_id)
    if not auth_check.get("ok"):
        return auth_check

    db = get_db()
    course = auth_check["course"]
    exist = db.table("activities").select("*").eq("course_id", course["id"]).eq("activity_no", activity_no).execute()
    if not exist.data:
        return {"ok": False, "error": "Activity does not exist"}

    current_state = exist.data[0].get("status")
    if current_state not in allowed_previous_states:
        return {"ok": False, "error": f"Invalid state transition from {current_state} to {new_state}"}

    db.table("activities").update({"status": new_state}).eq("course_id", course["id"]).eq("activity_no", activity_no).execute()
    return {"ok": True, "message": f"Activity state changed to {new_state}"}


def startActivity(email: str, password: str, course_id: str, activity_no: int) -> dict:
    return _changeActivityState(email, password, course_id, activity_no, "ACTIVE", ["NOT_STARTED"])


def endActivity(email: str, password: str, course_id: str, activity_no: int) -> dict:
    return _changeActivityState(email, password, course_id, activity_no, "ENDED", ["ACTIVE"])


# --- Export API (produces csv document) ---
def exportScores(email: str, password: str, course_id: str, activity_no: int) -> dict:
    raise NotImplementedError


# --- Reset API (deletes all scores for given activity_no) ---
def resetActivity(email: str, password: str, course_id: str, activity_no: int) -> dict:
    raise NotImplementedError


# --- Student Password Reset API ---
def resetStudentPassword(email: str, password: str, course_id: str, student_email: str, new_password: str) -> dict:
    raise NotImplementedError

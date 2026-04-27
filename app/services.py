from supabase import create_client, Client


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


def get_db() -> Client:
    from app.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase environment variables are missing")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# ==========================================
# STUDENT APIs
# ==========================================

# --- Student Auth APIs ---
def studentLogin(email: str, password: str) -> dict:
    credentials = _validate_credentials(email, password)
    if not credentials["ok"]:
        return credentials

    normalized_email = str(credentials["email"])
    db = get_db()
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


# --- Student Password APIs ---
def changeStudentPassword(email: str, password: str, new_password: str, old_password: str) -> dict:
    normalized_email = _normalize_email(email)
    if _is_blank(normalized_email):
        return {"ok": False, "error": "email is required"}

    if _is_blank(old_password):
        return {"ok": False, "error": "old_password is required"}

    if _is_blank(new_password):
        return {"ok": False, "error": "new_password is required"}

    db = get_db()
    auth_resp = db.table("students").select("password").eq("email", normalized_email).execute()

    if not auth_resp.data or auth_resp.data[0].get("password") != old_password:
        return {"ok": False, "error": "Invalid credentials"}

    db.table("students").update({"password": new_password}).eq("email", normalized_email).execute()
    return {"ok": True}


def setStudentPassword(email: str, password: str) -> dict:
    credentials = _validate_credentials(email, password)
    if not credentials["ok"]:
        return credentials

    normalized_email = str(credentials["email"])
    db = get_db()
    student_resp = db.table("students").select("id").eq("email", normalized_email).execute()

    if not student_resp.data:
        return {"ok": False, "error": "Student not found"}

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
    credentials = _validate_credentials(email, password)
    if not credentials["ok"]:
        return credentials

    normalized_email = str(credentials["email"])
    db = get_db()
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


# --- Instructor Password APIs ---
def changeInstructorPassword(email: str, password: str, old_password: str, new_password: str) -> dict:
    normalized_email = _normalize_email(email)
    if _is_blank(normalized_email):
        return {"ok": False, "error": "email is required"}

    if _is_blank(old_password):
        return {"ok": False, "error": "old_password is required"}

    if _is_blank(new_password):
        return {"ok": False, "error": "new_password is required"}

    # password is kept in the signature for compatibility; old_password is the current password check.
    db = get_db()
    auth_resp = db.table("instructors").select("password").eq("email", normalized_email).execute()

    if not auth_resp.data or auth_resp.data[0].get("password") != old_password:
        return {"ok": False, "error": "Invalid credentials"}

    db.table("instructors").update({"password": new_password}).eq("email", normalized_email).execute()
    return {"ok": True}


def setInstructorPassword(email: str, password: str | None = None) -> dict:
    credentials = _validate_credentials(email, password)
    if not credentials["ok"]:
        return credentials

    normalized_email = str(credentials["email"])
    db = get_db()
    instructor_resp = db.table("instructors").select("id").eq("email", normalized_email).execute()

    if not instructor_resp.data:
        return {"ok": False, "error": "Instructor not found"}

    db.table("instructors").update({"password": password}).eq("email", normalized_email).execute()
    return {"ok": True}


# --- Main APIs for Instructor ---

# [T16] Implement and route listMyCourses
def listMyCourses(email: str, password: str) -> dict:
    credentials = _validate_credentials(email, password)
    if not credentials["ok"]:
        return credentials

    normalized_email = str(credentials["email"])
    db = get_db()
    
    auth_resp = db.table("instructors").select("password").eq("email", normalized_email).execute()
    if not auth_resp.data or auth_resp.data[0].get("password") != password:
        return {"ok": False, "error": "Invalid credentials"}
        
    courses_resp = db.table("courses").select("*").eq("instructor_email", normalized_email).execute()
    return {"ok": True, "courses": courses_resp.data}


# [T18] Implement and route listActivities
def listActivities(email: str, password: str, course_id: str) -> dict:
    db = get_db()
    
    auth_resp = db.table("instructors").select("password").eq("email", email).execute()
    if not auth_resp.data or auth_resp.data[0].get("password") != password:
        return {"ok": False, "error": "Invalid credentials"}
        
    course_resp = db.table("courses").select("instructor_email").eq("course_id", course_id).execute()
    if not course_resp.data or course_resp.data[0].get("instructor_email") != email:
        return {"ok": False, "error": "Not authorized for this course"}
        
    activities_resp = db.table("activities").select("*").eq("course_id", course_id).execute()
    return {"ok": True, "activities": activities_resp.data}


def createActivity(
    email: str,
    password: str,
    course_id: str,
    activity_text: str,
    learning_objectives: list[str],
    activity_no_optional: int | None = None
) -> dict[str, object]:
    raise NotImplementedError


# S1-T22 [US-G]
def updateActivity(email: str, password: str, course_id: str, activity_no: int, patch: dict) -> dict:
    courses_check = listMyCourses(email, password)
    if not courses_check.get("ok"):
        return courses_check
        
    course_ids = [c.get("id") or c.get("course_id") for c in courses_check.get("courses", [])]
    if course_id not in course_ids:
        return {"ok": False, "error": "Unauthorized course access"}

    if not patch:
        return {"ok": False, "error": "Empty patch rejected"}

    allowed_fields = ["activity_text", "learning_objectives"]
    update_data = {k: v for k, v in patch.items() if k in allowed_fields}

    if not update_data:
        return {"ok": False, "error": "No allowed fields in patch"}

    db = get_db()
    # Check existence and current state
    exist = db.table("activities").select("*").eq("course_id", course_id).eq("activity_no", activity_no).execute()
    if not exist.data:
        return {"ok": False, "error": "Activity does not exist"}

    if exist.data[0].get("state") != "NOT_STARTED":
        return {"ok": False, "error": "Cannot update activity that has started or ended"}

    db.table("activities").update(update_data).eq("course_id", course_id).eq("activity_no", activity_no).execute()
    return {"ok": True, "message": "Activity updated"}


def startActivity(email: str, password: str, course_id: str, activity_no: int) -> dict:
    raise NotImplementedError


def endActivity(email: str, password: str, course_id: str, activity_no: int) -> dict:
    raise NotImplementedError


# --- Export API (produces csv document) ---
def exportScores(email: str, password: str, course_id: str, activity_no: int) -> dict:
    raise NotImplementedError


# --- Reset API (deletes all scores for given activity_no) ---
def resetActivity(email: str, password: str, course_id: str, activity_no: int) -> dict:
    raise NotImplementedError


# --- Student Password Reset API ---
def resetStudentPassword(email: str, password: str, course_id: str, student_email: str, new_password: str) -> dict:
    raise NotImplementedError

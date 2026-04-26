from supabase import create_client, Client

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
    raise NotImplementedError


# --- Student Password APIs ---
def changeStudentPassword(email: str, password: str, new_password: str, old_password: str) -> dict:
    raise NotImplementedError


def setStudentPassword(email: str, password: str) -> dict:
    raise NotImplementedError


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
    raise NotImplementedError


# --- Instructor Password APIs ---
def changeInstructorPassword(email: str, password: str, old_password: str, new_password: str) -> dict:
    raise NotImplementedError


def setInstructorPassword(email: str, password: str | None = None) -> dict:
    raise NotImplementedError


# --- Main APIs for Instructor ---

# [T16] Implement and route listMyCourses
def listMyCourses(email: str, password: str) -> dict:
    db = get_db()
    
    auth_resp = db.table("instructors").select("password").eq("email", email).execute()
    if not auth_resp.data or auth_resp.data[0].get("password") != password:
        return {"ok": False, "error": "Invalid credentials"}
        
    courses_resp = db.table("courses").select("*").eq("instructor_email", email).execute()
    return {"ok": True, "courses": courses_resp.data}


def listActivities(email: str, password: str, course_id: str) -> dict:
    raise NotImplementedError


def createActivity(
    email: str,
    password: str,
    course_id: str,
    activity_text: str,
    learning_objectives: list[str],
    activity_no_optional: int | None = None
) -> dict[str, object]:
    raise NotImplementedError


def updateActivity(email: str, password: str, course_id: str, activity_no: int, patch: dict) -> dict:
    raise NotImplementedError


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
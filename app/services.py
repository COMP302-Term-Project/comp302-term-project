import csv
import io
import json
import os
import re
import requests
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
    db = get_db()
    active_check = _get_active_student_activity(db, email, password, course_id, activity_no)
    if not active_check["ok"]:
        return active_check

    activity = active_check["activity"]
    student_activity = {
        key: activity.get(key)
        for key in ["course_id", "activity_no", "activity_text"]
        if key in activity
    }
    return {"ok": True, "activity": student_activity}


def _get_active_student_activity(db, email: str, password: str, course_id: str, activity_no: int) -> dict:
    identity = _authenticate_student(db, email, password)
    if not identity["ok"]:
        return identity

    auth_check = _authorize_student_course_access(db, identity, course_id)
    if not auth_check["ok"]:
        return auth_check

    course = auth_check["course"]
    activity_resp = (
        db.table("activities")
        .select("id,course_id,activity_no,activity_text,learning_objectives,status")
        .eq("course_id", course["id"])
        .eq("activity_no", activity_no)
        .execute()
    )

    if not activity_resp.data:
        return {"ok": False, "error": "Activity does not exist"}

    activity = activity_resp.data[0]
    if activity.get("status") != "ACTIVE":
        return {"ok": False, "error": "Activity is not active"}

    return {
        "ok": True,
        "student": auth_check["student"],
        "course": course,
        "activity": activity,
    }


def _normalize_conversation_history(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    history = []
    for item in value:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            history.append({"role": role, "content": content})

    return history


def _load_conversation_history(db, student_id: int, course_id: int, activity_no: int) -> list[dict[str, str]]:
    state_resp = (
        db.table("conversation_state")
        .select("conversation_history")
        .eq("student_id", student_id)
        .eq("course_id", course_id)
        .eq("activity_no", activity_no)
        .execute()
    )

    if not state_resp.data:
        return []

    return _normalize_conversation_history(state_resp.data[0].get("conversation_history"))


def _save_conversation_history(db, student_id: int, course_id: int, activity_no: int, history: list[dict[str, str]]) -> None:
    db.table("conversation_state").upsert(
        {
            "student_id": student_id,
            "course_id": course_id,
            "activity_no": activity_no,
            "conversation_history": history,
        },
        on_conflict="student_id,course_id,activity_no",
    ).execute()


def _get_student_score(db, student_id: int, course_id: int, activity_no: int) -> float:
    scores_resp = db.table("score_logs").select("score").eq("student_id", student_id).eq("course_id", course_id).eq("activity_no", activity_no).execute()
    return sum(record.get("score", 0.0) for record in scores_resp.data) if scores_resp.data else 0.0


def _last_assistant_response(history: list[dict[str, str]]) -> str | None:
    for message in reversed(history):
        if message["role"] == "assistant":
            return message["content"]
    return None


def _student_turn_count(history: list[dict[str, str]]) -> int:
    return sum(1 for message in history if message["role"] == "user")


def _build_initial_tutoring_response(activity_text: str) -> str:
    return (
        f"Activity: {activity_text}\n\n"
        "What is your initial answer in your own words?"
    )


def _build_followup_tutoring_response(history: list[dict[str, str]]) -> str:
    followups = [
        "Can you make your reasoning more specific using the important terms from the activity?",
        "Can you explain why your answer would work in this activity situation?",
        "Can you add one concrete detail that would make your answer more complete?",
        "Can you connect your answer to another important idea from the activity?",
    ]
    turn_index = max(_student_turn_count(history) - 1, 0)
    return followups[turn_index % len(followups)]


def _build_tutoring_llm_messages(activity: dict, history: list[dict[str, str]], current_score: float = 0.0) -> list[dict[str, str]]:
    learning_objectives = activity.get("learning_objectives") or []
    objectives_text = "\n".join(f"- {objective}" for objective in learning_objectives)
    system_prompt = (
        "ROLE: Warm university instructor. Teach for conceptual mastery using Socratic questions and academic explanations.\n\n"
        "STRICT OUTPUT STYLE:\n"
        "You MUST respond with ONLY a valid JSON object. Do not wrap it in markdown block quotes. The format is a two-field JSON:\n"
        '{"APICall": "studentApi(action:\\"logScore\\") with (score=1/meta=\\"objective text\\")" OR "", "response": "Your message to the student"}\n\n'
        "TASK:\n"
        "I will provide the activity_text and the learning_objectives.\n"
        "NEVER present or mention about learning_objectives to the student.\n"
        "Do the following in a loop so that all the learning_objectives are covered:\n"
        "- Ask one question about the ACTIVITY so that the student can learn the LEARNING POINTS.\n"
        "- If the student has not yet learned one of them, continue asking questions and receiving answers. "
        "HOWEVER, if you detect that the student has sensed or understood one of the learning_objectives (let us call its text as learned_objective):\n"
        ' 1. FIRST, set "APICall" to studentApi(action:"logScore") with parameters: score=1 and meta=learned_objective. Increase the student\'s score by one and tell the student their current score.\n'
        " 2. Then teach the corresponding point independently of the ACTIVITY, in an academic lecture format. The title must be bold and formatted as a heading. Do NOT wait for the student to learn all of them before teaching one.\n"
        " 3. If there are still some learning_objectives that are not covered, continue to ask questions.\n\n"
        "HARD RULES:\n"
        "- Never explain or directly teach anything before a score is earned.\n"
        "- Never use the words 'LO' or 'Learning Objective'.\n"
        "- Always respond in English.\n"
        "- If you give some options to the student, give them with numbered list instead of bullets.\n"
        "- All the topic related terms and words will be presented as activity. NEVER use topic word for any reason. EXAMPLE: start an activity -> start a topic OR activity_no -> topic_no OR activity text -> topic_text.\n\n"
        f"ACTIVITY TEXT:\n{activity.get('activity_text', '')}\n\n"
        f"LEARNING OBJECTIVES:\n{objectives_text}\n\n"
        f"CURRENT SCORE: {current_score}"
    )

    return [{"role": "system", "content": system_prompt}, *history]


def _extract_log_score_meta(apicall: str) -> str | None:
    if not apicall or "logScore" not in apicall:
        return None
    match = re.search(r'meta=\\?["\'](.*?)\\?["\']', apicall)
    if match:
        return match.group(1)
    match = re.search(r'meta=([^)\n]+)', apicall)
    if match:
        return match.group(1).strip()
    return None

def _call_tutoring_llm(activity: dict, history: list[dict[str, str]], current_score: float = 0.0) -> tuple[str, str]:
    messages = _build_tutoring_llm_messages(activity, history, current_score)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_MODEL")

    if not api_key or not model:
        # Fallback for local testing if no API key or model is provided
        return _build_followup_tutoring_response(history), ""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_object"}
            },
            timeout=15
        )
        response.raise_for_status()
        result_json = response.json()
        content = result_json["choices"][0]["message"]["content"]

        # Parse the JSON returned by the LLM
        parsed_content = json.loads(content)
        # Extract the response and the APICall
        return parsed_content.get("response", "Could you elaborate on that?"), parsed_content.get("APICall", "")

    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        # Fallback if API fails or returns invalid JSON
        print(f"LLM Error: {e}")
        return "Can you make your reasoning more specific using the important terms from the activity?", ""


def submitTutoringAnswer(
    email: str,
    password: str,
    course_id: str,
    activity_no: int,
    answer: str | None = None,
) -> dict:
    db = get_db()
    active_check = _get_active_student_activity(db, email, password, course_id, activity_no)
    if not active_check["ok"]:
        return active_check

    student = active_check["student"]
    course = active_check["course"]
    activity = active_check["activity"]
    history = _load_conversation_history(db, student["id"], course["id"], activity_no)
    current_score = _get_student_score(db, student["id"], course["id"], activity_no)

    if not history:
        response_text = _build_initial_tutoring_response(activity["activity_text"])
        history.append({"role": "assistant", "content": response_text})
        _save_conversation_history(db, student["id"], course["id"], activity_no, history)
        return {
            "ok": True,
            "response": response_text,
            "state": {
                "student_turns": 0,
                "assistant_turns": 1,
                "score": current_score,
            },
        }

    if _is_blank(answer):
        return {
            "ok": True,
            "response": _last_assistant_response(history),
            "state": {
                "student_turns": _student_turn_count(history),
                "assistant_turns": sum(1 for message in history if message["role"] == "assistant"),
                "score": current_score,
            },
        }

    history.append({"role": "user", "content": str(answer).strip()})
    response_text, apicall = _call_tutoring_llm(activity, list(history), current_score)
    
    meta = _extract_log_score_meta(apicall)
    if meta:
        existing_score = db.table("score_logs").select("id").eq("student_id", student["id"]).eq("course_id", course["id"]).eq("activity_no", activity_no).eq("meta", meta).execute()
        if not existing_score.data:
            logScore(email, password, course["course_id"], activity_no, 1.0, meta)
            current_score += 1.0
            
    history.append({"role": "assistant", "content": response_text})
    _save_conversation_history(db, student["id"], course["id"], activity_no, history)

    return {
        "ok": True,
        "response": response_text,
        "state": {
            "student_turns": _student_turn_count(history),
            "assistant_turns": sum(1 for message in history if message["role"] == "assistant"),
            "score": current_score,
        },
    }


def logScore(email: str, password: str, course_id: str, activity_no: int, score: float, meta: str | None = None) -> dict:
    db = get_db()
    active_check = _get_active_student_activity(db, email, password, course_id, activity_no)
    if not active_check["ok"]:
        return active_check

    student = active_check["student"]
    course = active_check["course"]

    if score <= 0:
        return {"ok": False, "error": "Score must be positive"}

    insert_data = {
        "student_id": student["id"],
        "course_id": course["id"],
        "activity_no": activity_no,
        "score": score,
        "meta": meta or ""
    }

    insert_res = db.table("score_logs").insert(insert_data).execute()
    
    if insert_res.data:
        return {"ok": True, "score_log": insert_res.data[0]}
    return {"ok": False, "error": "Failed to log score"}


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


def _delete_activity_score_logs(db, course_db_id: int, activity_no: int) -> None:
    db.table("score_logs").delete().eq("course_id", course_db_id).eq("activity_no", activity_no).execute()


def _delete_activity_conversation_state(db, course_db_id: int, activity_no: int) -> None:
    db.table("conversation_state").delete().eq("course_id", course_db_id).eq("activity_no", activity_no).execute()


def _cleanup_activity_runtime_state(db, course_db_id: int, activity_no: int) -> None:
    _delete_activity_score_logs(db, course_db_id, activity_no)
    _delete_activity_conversation_state(db, course_db_id, activity_no)


# --- Export API (produces csv document) ---
def exportScores(email: str, password: str, course_id: str, activity_no: int) -> dict:
    db = get_db()
    identity = _authenticate_instructor(db, email, password)
    if not identity["ok"]:
        return identity

    auth_check = _authorize_instructor_course_access(db, identity, course_id)
    if not auth_check["ok"]:
        return auth_check

    course = auth_check["course"]
    activity_resp = (
        db.table("activities")
        .select("id")
        .eq("course_id", course["id"])
        .eq("activity_no", activity_no)
        .execute()
    )
    if not activity_resp.data:
        return {"ok": False, "error": "Activity does not exist"}

    score_resp = (
        db.table("score_logs")
        .select("*")
        .eq("course_id", course["id"])
        .eq("activity_no", activity_no)
        .order("student_id")
        .execute()
    )
    student_resp = db.table("students").select("id,email,full_name").execute()
    students_by_id = {
        student.get("id"): student
        for student in (student_resp.data or [])
    }

    fieldnames = [
        "student_id",
        "student_email",
        "student_full_name",
        "course_id",
        "activity_no",
        "score",
        "meta",
        "created_at",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()

    for score_log in score_resp.data or []:
        student = students_by_id.get(score_log.get("student_id"), {})
        writer.writerow({
            "student_id": score_log.get("student_id", ""),
            "student_email": student.get("email", ""),
            "student_full_name": student.get("full_name", ""),
            "course_id": course.get("course_id", course_id),
            "activity_no": score_log.get("activity_no", activity_no),
            "score": score_log.get("score", ""),
            "meta": score_log.get("meta", ""),
            "created_at": score_log.get("created_at", ""),
        })

    return {"ok": True, "csv": output.getvalue()}


# --- Reset API (deletes all scores for given activity_no) ---
def resetActivity(email: str, password: str, course_id: str, activity_no: int) -> dict:
    auth_check = _verify_instructor_course_access(email, password, course_id)
    if not auth_check.get("ok"):
        return auth_check

    db = get_db()
    course = auth_check["course"]
    exist = db.table("activities").select("*").eq("course_id", course["id"]).eq("activity_no", activity_no).execute()
    if not exist.data:
        return {"ok": False, "error": "Activity does not exist"}

    _cleanup_activity_runtime_state(db, course["id"], activity_no)
    db.table("activities").update({"status": "ENDED"}).eq("course_id", course["id"]).eq("activity_no", activity_no).execute()
    return {"ok": True, "message": "Activity reset"}


# --- Student Password Reset API ---
def resetStudentPassword(email: str, password: str, course_id: str, student_email: str, new_password: str) -> dict:
    if _is_blank(student_email):
        return {"ok": False, "error": "student_email is required"}

    if _is_blank(new_password):
        return {"ok": False, "error": "new_password is required"}

    db = get_db()
    identity = _authenticate_instructor(db, email, password)
    if not identity["ok"]:
        return identity

    auth_check = _authorize_instructor_course_access(db, identity, course_id)
    if not auth_check["ok"]:
        return auth_check

    normalized_student_email = _normalize_email(student_email)
    student_resp = (
        db.table("students")
        .select("id,email")
        .eq("email", normalized_student_email)
        .execute()
    )
    if not student_resp.data:
        return {"ok": False, "error": "Student not found"}

    course = auth_check["course"]
    student = student_resp.data[0]
    enrollment_resp = (
        db.table("student_courses")
        .select("id")
        .eq("student_id", student["id"])
        .eq("course_id", course["id"])
        .execute()
    )
    if not enrollment_resp.data:
        return {"ok": False, "error": "Student is not enrolled in this course"}

    db.table("students").update({"password": new_password}).eq("id", student["id"]).execute()
    return {"ok": True, "message": "Student password reset"}


# --- Manual Grading API ---
def manualGradeStudent(
    email: str,
    password: str,
    course_id: str,
    student_id: int,
    activity_no: int,
    score: float,
    reason: str
) -> dict:

    # instructor authorization check
    auth_check = _verify_instructor_course_access(email, password, course_id)

    if not auth_check.get("ok"):
        return auth_check

    # score validation
    if score <= 0:
        return {"ok": False, "error": "Score must be positive"}

    if _is_blank(reason):
        return {"ok": False, "error": "reason is required"}

    db = get_db()
    course = auth_check["course"]

    # activity existence check
    activity_resp = (
        db.table("activities")
        .select("id,status")
        .eq("course_id", course["id"])
        .eq("activity_no", activity_no)
        .execute()
    )

    if not activity_resp.data:
        return {"ok": False, "error": "Activity does not exist"}

    activity = activity_resp.data[0]

    # only ACTIVE activities can be graded
    if activity.get("status") != "ACTIVE":
        return {"ok": False, "error": "Activity is not active"}

    # call database function
    db.rpc(
        "log_manual_grade",
        {
            "p_student_id": student_id,
            "p_activity_id": activity["id"],
            "p_instructor_id": auth_check["instructor"]["id"],
            "p_score": score,
            "p_reason": reason
        }
    ).execute()

    return {
        "ok": True,
        "message": "Manual grade logged successfully"
    }

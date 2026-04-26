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


def studentLogin(email: str, password: str) -> dict:
    raise NotImplementedError


def changeStudentPassword(email: str, password: str, new_password: str, old_password: str) -> dict:
    raise NotImplementedError


def setStudentPassword(email: str, password: str) -> dict:
    raise NotImplementedError


def getActivity(email: str, password: str, course_id: str, activity_no: int) -> dict:
    raise NotImplementedError


def logScore(email: str, password: str, course_id: str, activity_no: int, score: float, meta: str | None = None) -> dict:
    raise NotImplementedError


def instructorLogin(email: str, password: str) -> dict:
    raise NotImplementedError


def changeInstructorPassword(email: str, password: str, old_password: str, new_password: str) -> dict:
    raise NotImplementedError


def setInstructorPassword(email: str, password: str | None = None) -> dict:
    raise NotImplementedError


def listMyCourses(email: str, password: str) -> dict:
    raise NotImplementedError


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


def exportScores(email: str, password: str, course_id: str, activity_no: int) -> dict:
    raise NotImplementedError


def resetActivity(email: str, password: str, course_id: str, activity_no: int) -> dict:
    raise NotImplementedError


def resetStudentPassword(email: str, password: str, course_id: str, student_email: str, new_password: str) -> dict:
    raise NotImplementedError

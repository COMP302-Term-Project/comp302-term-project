from fastapi import FastAPI
  
app = FastAPI()


@app.get("/")
def root() -> dict:
    return {"ok": True, "message": "InClass Platform API"}


# ==========================================
# STUDENT ROUTES
# ==========================================

# --- Student Auth APIs ---
@app.post("/student/login")
def studentLogin(*, email: str, password: str) -> dict:
    from app import services
    return services.studentLogin(email=email, password=password)


@app.post("/student/change-password")
def changeStudentPassword(*, email: str, password: str, new_password: str, old_password: str) -> dict:
    from app import services
    return services.changeStudentPassword(
        email=email,
        password=password,
        new_password=new_password,
        old_password=old_password,
    )


@app.post("/student/set-password")
def setStudentPassword(*, email: str, password: str) -> dict:
    from app import services
    return services.setStudentPassword(email=email, password=password)


# --- Main Student APIs ---
@app.post("/student/get-activity")
def getActivity(*, email: str, password: str, course_id: str, activity_no: int) -> dict:
    from app import services
    return services.getActivity(
        email=email,
        password=password,
        course_id=course_id,
        activity_no=activity_no,
    )


# ==========================================
# INSTRUCTOR ROUTES
# ==========================================

# --- Instructor Auth APIs ---
@app.post("/instructor/login")
def instructorLogin(*, email: str, password: str) -> dict:
    from app import services
    return services.instructorLogin(email=email, password=password)


@app.post("/instructor/change-password")
def changeInstructorPassword(*, email: str, password: str, old_password: str, new_password: str) -> dict:
    from app import services
    return services.changeInstructorPassword(
        email=email,
        password=password,
        old_password=old_password,
        new_password=new_password,
    )


@app.post("/instructor/set-password")
def setInstructorPassword(*, email: str, password: str | None = None) -> dict:
    from app import services
    return services.setInstructorPassword(email=email, password=password)


# --- Main APIs for Instructor ---

# [T16] Implement and route listMyCourses
@app.post("/instructor/list-my-courses")
def listMyCourses(*, email: str, password: str) -> dict[str, object]:
    from app import services
    return services.listMyCourses(email=email, password=password)

# S1-T20 [US-F] Implement and route createActivity
@app.post("/instructor/create-activity")
def createActivity(
    *, 
    email: str, 
    password: str, 
    course_id: str, 
    activity_text: str, 
    learning_objectives: list[str], 
    activity_no_optional: int | None = None
) -> dict[str, object]:
    from app import services
    return services.createActivity(
        email=email,
        password=password,
        course_id=course_id,
        activity_text=activity_text,
        learning_objectives=learning_objectives,
        activity_no_optional=activity_no_optional
    )

# [T18] Implement and route listActivities
@app.post("/instructor/list-activities")
def listActivities(*, email: str, password: str, course_id: str) -> dict[str, object]:
    from app import services
    return services.listActivities(email=email, password=password, course_id=course_id)

# S1-T22 [US-G] - Implement and route updateActivity
@app.post("/instructor/update-activity")
def updateActivity(
    *, 
    email: str, 
    password: str, 
    course_id: str, 
    activity_no: int, 
    patch: dict
) -> dict:
    from app import services
    return services.updateActivity(
        email=email, 
        password=password, 
        course_id=course_id,
        activity_no=activity_no, 
        patch=patch
    )

# S1-T24 [US-H] - Implement startActivity
@app.post("/instructor/start-activity")
def startActivity(
    *, 
    email: str, 
    password: str, 
    course_id: str, 
    activity_no: int
) -> dict:
    from app import services
    return services.startActivity(
        email=email,
        password=password,
        course_id=course_id,
        activity_no=activity_no
    )

# S1-T24 [US-H] - Implement endActivity
@app.post("/instructor/end-activity")
def endActivity(
    *, 
    email: str, 
    password: str, 
    course_id: str, 
    activity_no: int
) -> dict:
    from app import services
    return services.endActivity(
        email=email,
        password=password,
        course_id=course_id,
        activity_no=activity_no
    )

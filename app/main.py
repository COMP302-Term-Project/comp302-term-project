from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any


class AuthRequest(BaseModel):
    email: str
    password: str

class CourseRequest(AuthRequest):
    course_id: str

class ActivityPatchRequest(CourseRequest):
    activity_no: int
    patch: Dict[str, Any]


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

# S1-T22 [US-G] - Implement and route updateActivity
@app.post("/instructor/update-activity")
def updateActivity(req: ActivityPatchRequest) -> dict:
    from app import services
    return services.updateActivity(
        email=req.email, 
        password=req.password, 
        course_id=req.course_id,
        activity_no=req.activity_no, 
        patch=req.patch
    )

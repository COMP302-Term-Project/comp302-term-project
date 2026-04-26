from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root() -> dict:
    return {"ok": True, "message": "InClass Platform API"}


# ==========================================
# INSTRUCTOR ROUTES
# ==========================================

# --- Main APIs for Instructor ---

# [T16] Implement and route listMyCourses
@app.post("/instructor/list-my-courses")
def listMyCourses(*, email: str, password: str) -> dict[str, object]:
    from app import services
    return services.listMyCourses(email=email, password=password)

# [T18] Implement and route listActivities
@app.post("/instructor/list-activities")
def listActivities(*, email: str, password: str, course_id: str) -> dict[str, object]:
    from app import services
    return services.listActivities(email=email, password=password, course_id=course_id)

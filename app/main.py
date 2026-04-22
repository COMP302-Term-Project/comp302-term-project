from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root() -> dict:
    return {"ok": True, "message": "InClass Platform API"}

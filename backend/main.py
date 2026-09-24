"""Yale SOM course explorer API desk.

Run from backend/:  uvicorn main:app --reload --port 8000
Open API docs:      http://127.0.0.1:8000/docs
Frontend (Vite):    http://127.0.0.1:5173
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import run_agent

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "yale_som.db"
load_dotenv(PROJECT_ROOT / ".env")

app = FastAPI(title="Yale SOM Courses", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _course_dict(row: sqlite3.Row) -> dict[str, str]:
    course = dict(row)
    course.update(
        {
            "title": course.get("course_title") or "",
            "number": course.get("course_number") or "",
            "faculty": course.get("faculty_1") or "",
            "day_time": course.get("daytimes") or "",
            "category": course.get("course_category") or "",
            "description": course.get("course_description") or "",
        }
    )
    return course


def load_courses(query: str | None = None) -> list[dict[str, str]]:
    sql = "SELECT * FROM courses"
    params: list[str] = []
    if query and query.strip():
        sql += " WHERE LOWER(course_title || ' ' || course_number || ' ' || COALESCE(course_description, '') || ' ' || COALESCE(faculty_1, '')) LIKE ?"
        params.append(f"%{query.strip().lower()}%")
    sql += " ORDER BY course_number, course_title"
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [_course_dict(row) for row in connection.execute(sql, params)]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


@app.get("/api/health")
def health():
    return {"ok": True, "database": str(DATABASE_PATH.name)}


@app.get("/api/courses")
def list_courses(q: str | None = Query(default=None)):
    """Return courses for the React catalog (optional text filter)."""
    courses = load_courses(q)
    return {"count": len(courses), "courses": courses}


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    result = run_agent(body.message)
    return ChatResponse(
        reply=result.get("reply", ""),
        tools_used=list(result.get("tools_used") or []),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

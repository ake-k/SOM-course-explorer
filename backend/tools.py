from __future__ import annotations

import html
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

from models import Course, ToolCall


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "yale_som.db"

SEARCH_COLUMNS = (
    "course_id", "course_number", "course_title", "course_category",
    "course_type", "course_session", "course_description", "faculty_1",
    "faculty_1_email", "faculty_bio", "daytimes", "timings_day",
    "timings_start", "timings_end", "room", "section", "units", "term_code",
)


@dataclass
class ToolState:
    calls: list[ToolCall] = field(default_factory=list)


def _value(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _course(row: dict[str, Any]) -> Course:
    normalized = dict(row)
    normalized.update(
        {
        "title": _value(row, "course_title", "Course Title", "title"),
        "number": _value(row, "course_number", "Course Number", "number"),
        "faculty": _value(row, "faculty_1", "Faculty 1", "faculty"),
        "day_time": _value(row, "daytimes", "Daytimes", "day_time", "day/time"),
        "category": _value(row, "course_category", "Course Category", "category"),
        "description": _value(row, "course_description", "Course Description", "description"),
        "faculty_bio": _value(row, "faculty_bio", "Faculty Bio"),
        "room": _value(row, "Room", "room"),
        "units": _value(row, "Units", "units"),
        }
    )
    return Course(**normalized)


def _short(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def search_courses(query: str, limit: int = 15, state: ToolState | None = None) -> list[Course]:
    """Search the Yale SOM course database across catalog and schedule fields."""
    needle = query.strip().lower()
    safe_limit = max(1, min(limit, 15))
    terms = [term for term in re.split(r"\s+", needle) if term]
    where = " AND ".join(
        "(" + " OR ".join(f"LOWER(COALESCE({column}, '')) LIKE ?" for column in SEARCH_COLUMNS) + ")"
        for _ in terms
    )
    params = [f"%{term}%" for term in terms for _ in SEARCH_COLUMNS]
    sql = "SELECT * FROM courses"
    if where:
        sql += f" WHERE {where}"
    sql += " ORDER BY course_number, course_title LIMIT ?"
    params.append(safe_limit)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        matches = [dict(row) for row in connection.execute(sql, params)]
    result = [_course(row) for row in matches]
    if state is not None:
        state.calls.append(
            ToolCall(
                name="search_courses",
                args={"query": query, "limit": safe_limit},
                result=f"Found {len(result)} matching course rows.",
            )
        )
    return result


class _SearchLinkParser:
    def __init__(self) -> None:
        self.links: list[tuple[str, str]] = []
        self._current_href = ""
        self._current_text: list[str] = []

    def feed(self, document: str) -> None:
        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            re.I | re.S,
        )
        for href, body in pattern.findall(document):
            title = re.sub(r"<[^>]+>", "", html.unescape(body)).strip()
            if title:
                self.links.append((title, html.unescape(href)))


def web_search(query: str, state: ToolState | None = None) -> list[dict[str, str]]:
    """Search the public web for current faculty news, syllabus context, or other information absent from the course JSON."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query.strip())}"
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": "Yale-SOM-Course-Explorer/1.0"},
            timeout=10,
            follow_redirects=True,
        )
        response.raise_for_status()
        parser = _SearchLinkParser()
        parser.feed(response.text)
        results = [{"title": title, "url": link} for title, link in parser.links[:6]]
        summary = f"Found {len(results)} public web results."
    except httpx.HTTPError as exc:
        results = []
        summary = f"Web search unavailable: {type(exc).__name__}."
    if state is not None:
        state.calls.append(
            ToolCall(name="web_search", args={"query": query}, result=summary)
        )
    return results

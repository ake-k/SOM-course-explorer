from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Course(BaseModel):
    """A normalized course row, with the original dataset fields retained."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    title: str = Field(default="", description="Course title")
    number: str = Field(default="", description="Course number")
    faculty: str = Field(default="", description="Primary faculty")
    day_time: str = Field(default="", description="Meeting day and time")
    category: str = Field(default="", description="Course category")
    description: str = Field(default="")
    faculty_bio: str = Field(default="")
    room: str = Field(default="")
    units: str = Field(default="")


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: str = ""


class AgentResult(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


class AuditEntry(BaseModel):
    time: str
    user_message: str
    thoughts: list[str] = Field(default_factory=list)
    tools: list[ToolCall] = Field(default_factory=list)
    stopped_because: str

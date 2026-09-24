from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import AgentResult, AuditEntry, ToolCall
from tools import ToolState, search_courses, web_search


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
REPO_ROOT = PROJECT_ROOT.parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"

# Prefer a Lecture 7 .env, while supporting the project-level .env used by the course.
load_dotenv(REPO_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env", override=True)


def _instructions() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _new_agent(state: ToolState) -> Agent[ToolState, str]:
    api_key = __import__("os").getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not configured in a .env file.")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.portkey.ai/v1",
        default_headers={
            "x-portkey-api-key": api_key,
            "x-portkey-provider": "openai",
        },
    )
    model = OpenAIChatModel(
        "gpt-5.6-luna",
        provider=OpenAIProvider(openai_client=client),
    )

    async def search_tool(ctx: RunContext[ToolState], query: str, limit: int = 15):
        return search_courses(query, limit, ctx.deps)

    async def web_tool(ctx: RunContext[ToolState], query: str):
        return web_search(query, ctx.deps)

    return Agent(
        model,
        deps_type=ToolState,
        output_type=str,
        system_prompt=_instructions(),
        tools=[search_tool, web_tool],
        retries=2,
    )


def _write_audit(entry: AuditEntry) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        rows = json.loads(AUDIT_PATH.read_text(encoding="utf-8")) if AUDIT_PATH.exists() else []
        if not isinstance(rows, list):
            rows = []
    except (OSError, json.JSONDecodeError):
        rows = []
    rows.append(entry.model_dump(mode="json"))
    AUDIT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_agent(message: str) -> dict[str, Any]:
    state = ToolState()
    thoughts: list[str] = []
    stopped_because = "The assistant returned a final answer."
    try:
        agent = _new_agent(state)
        result = agent.run_sync(message, deps=state)
        reply = result.output
        if state.calls:
            thoughts.append("The assistant consulted the selected course and/or public-web tools.")
        else:
            thoughts.append("The assistant answered without invoking a tool.")
    except Exception as exc:
        reply = (
            "I’m unable to reach the course assistant right now. "
            "Please check the backend configuration and try again."
        )
        stopped_because = f"The agent stopped after an error: {type(exc).__name__}."
        thoughts.append("The request could not be completed because the agent service was unavailable.")

    _write_audit(
        AuditEntry(
            time=datetime.now(timezone.utc).isoformat(),
            user_message=message,
            thoughts=thoughts,
            tools=state.calls,
            stopped_because=stopped_because,
        )
    )
    output = AgentResult(reply=reply, tools_used=list(dict.fromkeys(call.name for call in state.calls)))
    return output.model_dump()

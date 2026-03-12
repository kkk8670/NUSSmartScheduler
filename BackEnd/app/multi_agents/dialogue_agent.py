from typing import Any, Dict, List
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from uuid import uuid4

try:
    from app.agent.parse import parse_to_request  # LLM parser
except Exception:
    parse_to_request = None



class DialogueInput(BaseModel):
    message: str = Field(..., description="User input that needs task parsing")

def dialogue_tool_func(message: str) -> Dict[str, Any]:
    notes = []
    tasks = []

    # 1) 调用 LLM parser
    if parse_to_request is not None:
        try:
            req = parse_to_request([("user", message)])
            parsed = list(req.tasks or [])
            if parsed:
                # 组装结构化任务
                for idx, t in enumerate(parsed):
                    title = getattr(t, "title", None) or f"task_{idx}"
                    duration = getattr(t, "duration_min", None) or 60
                    location = getattr(t, "location", None)
                    earliest = getattr(t, "earliest", None)
                    latest = getattr(t, "latest", None)
                    tasks.append({
                        "id": str(uuid4()),
                        "title": title.strip(),
                        "duration_min": duration,
                        "location": location,
                        "earliest": str(earliest) if earliest else None,
                        "latest": str(latest) if latest else None,
                    })
                notes.append(f"[Dialogue] parsed {len(tasks)} tasks via LLM")
        except Exception as e:
            notes.append(f"[Dialogue] parse_to_request failed: {e}")

    # 2) fallback: 如果没任务，用 && 分裂
    if not tasks:
        parts = message.split("&&")
        for idx, part in enumerate(parts):
            cleaned = part.strip()
            if not cleaned:
                continue
            tasks.append({
                "id": str(uuid4()),
                "title": cleaned,
                "duration_min": 60,
                "location": None,
                "earliest": None,
                "latest": None,
            })
        notes.append(f"[Dialogue] fallback {len(tasks)} tasks")

    return {
        "tasks": tasks,
        "notes": notes
    }

dialogue_agent_tool = StructuredTool.from_function(
    name="dialogue_agent_tool",
    description="Parse user input into structured tasks (title, duration, time hints, location).",
    func=lambda message: dialogue_tool_func(message),
    args_schema=DialogueInput,
)

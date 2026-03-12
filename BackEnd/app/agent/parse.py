# app/agent/parse.py
from typing import List
from pydantic import BaseModel, Field  # ✅ v2
from langchain_openai import ChatOpenAI

from app.agent.prompts import PLAN_PARSE_SYSTEM
from app.core.config import settings
from app.schemas.tasks import TaskIn

class PlanRequest(BaseModel):
    tasks: List[TaskIn]
    commute_mode: str = "auto"
    mode: str = "travel"

def parse_to_request(messages: list) -> PlanRequest:

    llm = ChatOpenAI(
        model=settings.AGENT_MODEL,
        temperature=settings.AGENT_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY
    )
    tool = llm.with_structured_output(PlanRequest)
    out: PlanRequest = tool.invoke(messages)

    user_text = ""
    for role, content in messages:
        if role == "user":
            user_text = content or ""
            break
    multi_markers = [",", "，", " and ", " then ", "之后", "然后", "再"]
    if sum(m in user_text for m in multi_markers) >= 1 and len(out.tasks) <= 1:
        strong_sys = PLAN_PARSE_SYSTEM + "\nIMPORTANT: The user listed MULTIPLE tasks. Return ALL tasks."
        out = tool.invoke([("system", strong_sys), *[(r, c) for (r, c) in messages if r != "system"]])

    return out

# app/agent/chat.py
from typing import List, Optional
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from app.agent import prompts
from app.agent.schemas_chat import ChatIn, ChatOut, PlanItemOut
from app.core.config import settings


class PlanLLMItem(BaseModel):
    title: str
    loc: Optional[str] = None
    start: str  # HH:MM
    end: str    # HH:MM
    color: Optional[str] = None

class PlanLLMResponse(BaseModel):
    items: List[PlanLLMItem]

def handle_chat(body: ChatIn) -> ChatOut:
    llm = ChatOpenAI(
        model=settings.AGENT_MODEL,
        temperature=settings.AGENT_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY
    )
    print(ChatIn)
    tool = llm.with_structured_output(PlanLLMResponse)

    resp: PlanLLMResponse = tool.invoke([
        ("system", prompts.PLAN_SYSTEM),
        ("user", body.prompt)
    ])

    plan = [PlanItemOut(**it.dict()) for it in resp.items]

    reply = "Drafted a plan. Click Open Timeline to review." if plan else \
        "No schedule change; try specifying time/place/duration."

    return ChatOut(reply=reply, plan=plan)

from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from app.schemas.tasks import TaskIn
from app.agent.prompts import PLAN_PARSE_SYSTEM

class PlanRequest(BaseModel):
    tasks: List[TaskIn]
    commute_mode: str = "auto"
    mode: str = "travel"

def parse_to_request(messages: list) -> PlanRequest:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tool = llm.with_structured_output(PlanRequest)
    return tool.invoke([("system", PLAN_PARSE_SYSTEM), *messages])

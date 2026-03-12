from typing import List, Optional
from pydantic import BaseModel

class ChatIn(BaseModel):
    prompt: str

class PlanItemOut(BaseModel):
    title: str
    loc: Optional[str] = None
    start: str  # "HH:MM"
    end: str    # "HH:MM"
    color: Optional[str] = None

class ChatOut(BaseModel):
    reply: str
    plan: List[PlanItemOut] = []

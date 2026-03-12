from pydantic import BaseModel
from typing import Optional
class EventData(BaseModel):
    summary: str
    description: Optional[str] = None
    start: str # ISO
    end: str # ISO
    timeZone: str = "Asia/Singapore"

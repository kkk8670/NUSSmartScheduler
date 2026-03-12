import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, field_validator


def _hhmm_from_any(s: str) -> str:
    s = str(s).strip()
    try:
        s2 = s.replace(" ", "T")
        if "T" in s2:
            dt = datetime.fromisoformat(s2)
            return dt.strftime("%H:%M")
    except Exception:
        pass
    m = re.search(r'(\d{1,2}):(\d{2})', s)
    if m:
        hh = int(m.group(1)); mm = int(m.group(2))
        if 0 <= hh < 24 and 0 <= mm < 60:
            return f"{hh:02d}:{mm:02d}"
    raise ValueError(f"Unrecognized time format: {s!r}")

class TaskIn(BaseModel):
    id: str
    title: str
    location: str
    type: str ="task"
    earliest: str # "HH:MM"
    latest: str # "HH:MM"
    duration_min: int
    fixed: bool = False
    priority: int = 3
    prefer_win: Optional[List[List[str]]] = None # e.g. [["13:30","16:30"]]

    @field_validator("earliest", "latest", mode="before")
    @classmethod
    def _normalize_time(cls, v: str) -> str:
        return _hhmm_from_any(v)

    @field_validator("prefer_win", mode="before")
    @classmethod
    def _normalize_prefer_win(cls, v):
        if not v:
            return v
        return [[_hhmm_from_any(a), _hhmm_from_any(b)] for a, b in v]
class GenerateReq(BaseModel):
    tasks: List[TaskIn]
    commuteMode: Optional[str] = "auto"
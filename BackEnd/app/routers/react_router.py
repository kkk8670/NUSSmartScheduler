# app/routers/react_lc_router.py
from http.client import HTTPException
from typing import Dict, Any, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.multi_agents.react_controller import run_react_agent

router = APIRouter(prefix="/agent", tags=["agent-react-lc"])

class ChatIn(BaseModel):
    prompt: str

class ReactStep(BaseModel):
    type: str                 # "thought" | "action" | "observation" | "final_log"
    content: str
    tool: Optional[str] = None

class ReactFinal(BaseModel):
    reply: str
    plan: List[Dict[str, Any]] = []
    schedule: Optional[Dict[str, Any]] = None
    evidence: List[Any] = []
    notes: List[str] = []

class ReactOut(BaseModel):
    steps: List[ReactStep]
    final: ReactFinal

from fastapi import HTTPException

@router.post("/chat/react", response_model=ReactOut)
def chat_react(body: ChatIn):
    try:
        steps_raw, final_raw = run_react_agent(body.prompt)

        # ✅ Ensure final_raw is a dict
        if not isinstance(final_raw, dict):
            final_raw = {}

        # ✅ Safe defaults for all fields
        final_raw["reply"] = final_raw.get("reply") or ""
        final_raw["plan"] = final_raw.get("plan") or []
        final_raw["schedule"] = final_raw.get("schedule") or None
        final_raw["evidence"] = final_raw.get("evidence") or []
        final_raw["notes"] = final_raw.get("notes") or []

        steps = [ReactStep(**s) for s in steps_raw]
        final = ReactFinal(**final_raw)
        return ReactOut(steps=steps, final=final)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"react_agent_failed: {e}")

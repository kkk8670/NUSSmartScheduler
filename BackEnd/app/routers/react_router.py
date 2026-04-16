# app/routers/react_router.py
import hashlib, time
from http.client import HTTPException
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.multi_agents.react_controller import run_react_agent
from app.users.auth.deps import get_current_user    # 已有的 JWT 依赖
from app.users.models import User

router = APIRouter(prefix="/agent", tags=["agent-react-lc"])

class ChatIn(BaseModel):
    prompt: str
    session_id: Optional[str] = None    # ← 新增：前端可传已有 session_id 延续会话

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

 

@router.post("/chat/react", response_model=ReactOut)
def chat_react(
    body: ChatIn,
    current_user: User = Depends(get_current_user),   # ← 新增：拿到登录用户
):
    try:
        uid = str(current_user.id)
 
        # session_id：前端没传时自动生成（精确到分钟，同一分钟内的请求归同一 session）
        session_id = body.session_id or _make_session_id(uid)

        steps_raw, final_raw = run_react_agent(
            body.prompt,
            user_id=uid,
            session_id=session_id,
        )

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


def _make_session_id(user_id: str) -> str:
    """
    Generate a stable session_id based on user_id + current minute.
    Multiple requests from the same user within the same minute are grouped into the same Langfuse Session, making it easy to see the complete trace chain of a conversation.
    This makes it easy to see the complete trace chain of a conversation.
    """
    minute_bucket = int(time.time() // 60)
    raw = f"{user_id}-{minute_bucket}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]
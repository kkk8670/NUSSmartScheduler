from fastapi import APIRouter, HTTPException, Depends
from app.agent.service import AgentService, PlanReq, CompareReq
from app.agent.schemas_chat import ChatIn, ChatOut
from app.agent.chat import handle_chat
from app.security import TokenData, get_current_user
import os 
from app.core.config import settings


router = APIRouter(tags=["agent"])
svc = AgentService()

@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, me: TokenData = Depends(get_current_user)) -> ChatOut:
    print(f"🔍 接口实时检查: settings.LANGFUSE_HOST = {settings.LANGFUSE_HOST}")
    print(f"🔍 DEBUG: Public Key = {os.environ.get('LANGFUSE_PUBLIC_KEY', '')[:10]}...")

    try:
        return handle_chat(body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"agent_chat_error: {e}")

from fastapi import APIRouter, HTTPException, Depends
from app.agent.service import AgentService, PlanReq, CompareReq
from app.agent.schemas_chat import ChatIn, ChatOut
from app.agent.chat import handle_chat
from app.security import TokenData, get_current_user

router = APIRouter(tags=["agent"])
svc = AgentService()

@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, me: TokenData = Depends(get_current_user)) -> ChatOut:
    try:
        return handle_chat(body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"agent_chat_error: {e}")

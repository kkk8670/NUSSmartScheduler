# app/routers/multiagents_router.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

# from app.multi_agents.orchestrator import run_pipeline, generate_reply
from app.multi_agents.base import State, Message

# 明确导出 APIRouter 实例
router = APIRouter(prefix="/agent", tags=["agent"])


# —— I/O 模型（可先用 Dict/Any，后面再换成你自定义的 Pydantic 模型）——
class ChatIn(BaseModel):
    prompt: str = Field(..., description="用户输入")

class ChatOut(BaseModel):
    reply: str
    plan: List[Dict[str, Any]]
    schedule: Optional[Dict[str, Any]] = None
    notes: List[str]
    evidence: List[Dict[str, Any]]


# @router.post("/chat/multi", response_model=ChatOut)
# async def chat_multi(request: Request, body: ChatIn):
#     """
#     多智能体入口：
#     - 把 Request 传入 orchestrator，内部可以安全使用 request.app.state.xxx（Weaviate client / VectorStore）
#     - 统一异常处理，避免 500 堆栈直接暴露
#     """
#     try:
#         # 1) 初始化对话状态
#         state = State(messages=[Message(role="user", content=body.prompt)])
#
#         # 2) 跑多智能体流水线（签名推荐：run_pipeline(request, state)）
#         final_state = run_pipeline(request, state)
#
#         # 3) 生成对用户的自然语言回复（签名推荐：generate_reply(request, final_state)）
#         reply_text = generate_reply(request, final_state)
#
#         # 4) 组织响应
#         return ChatOut(
#             reply=reply_text,
#             plan=[p.model_dump() for p in final_state.plan],
#             schedule=(final_state.schedule.model_dump() if getattr(final_state, "schedule", None) else None),
#             notes=getattr(final_state, "notes", []),
#             evidence=[e.model_dump() for e in getattr(final_state, "evidence", [])],
#         )
#     except Exception as e:
#         # 统一返回 500，并在服务端日志查看详细异常
#         raise HTTPException(status_code=500, detail=f"multi-agent pipeline failed: {e}")

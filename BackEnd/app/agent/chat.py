# app/agent/chat.py
from typing import List, Optional
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from app.agent import prompts
from app.agent.schemas_chat import ChatIn, ChatOut, PlanItemOut
from app.core.config import settings
from app.core.tracing import get_langfuse 
 

class PlanLLMItem(BaseModel):
    title: str
    loc: Optional[str] = None
    start: str  # HH:MM
    end: str    # HH:MM
    color: Optional[str] = None

class PlanLLMResponse(BaseModel):
    items: List[PlanLLMItem]

def handle_chat(body: ChatIn) -> ChatOut:
    lf = get_langfuse()
 

    llm = ChatOpenAI(
        model=settings.AGENT_MODEL,
        temperature=settings.AGENT_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY
    )
    print(ChatIn)
    tool = llm.with_structured_output(PlanLLMResponse)

    def _run() -> PlanLLMResponse:
        if lf:
            # 内层：generation span 记录 LLM 调用
            with lf.start_as_current_observation(
                as_type="generation",
                name="plan-llm",
                model=settings.AGENT_MODEL,
                input=[
                    {"role": "system", "content": prompts.PLAN_SYSTEM},
                    {"role": "user",   "content": body.prompt},
                ],
            ) as generation:
                result: PlanLLMResponse = tool.invoke([
                    ("system", prompts.PLAN_SYSTEM),
                    ("user", body.prompt),
                ])
                generation.update(
                    output={"items": [it.dict() for it in result.items]}
                )
                return result
        else:
            return tool.invoke([
                ("system", prompts.PLAN_SYSTEM),
                ("user", body.prompt),
            ])


    if lf:
        # 外层：根 span，作为整条 trace 的入口
        with lf.start_as_current_observation(
            as_type="span",
            name="chat-plan",
            input={"prompt": body.prompt},
        ) as root_span:
            resp = _run()

            plan = [PlanItemOut(**it.dict()) for it in resp.items]
            reply = (
                "Drafted a plan. Click Open Timeline to review."
                if plan
                else "No schedule change; try specifying time/place/duration."
            )

            # ✅ v4 正确写法：直接在 span 对象上 update，不用 update_current_trace
            root_span.update(
                output={"reply": reply, "plan_count": len(plan)},
                metadata={"model": settings.AGENT_MODEL},
            )
        lf.flush()
    else:
        resp = _run()
        plan = [PlanItemOut(**it.dict()) for it in resp.items]
        reply = (
            "Drafted a plan. Click Open Timeline to review."
            if plan
            else "No schedule change; try specifying time/place/duration."
        )

    return ChatOut(reply=reply, plan=plan)

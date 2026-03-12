from typing import Dict, Any, List
from datetime import datetime, date, time
import pytz
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.agent import prompts  # 你已有的 PLAN_SYSTEM
from pydantic import BaseModel, Field

SG = pytz.timezone("Asia/Singapore")

# ==== 你的 LLM 输出 Schema（示例）====
class PlanItemOut(BaseModel):
    title: str
    start: str                    # 可能是 "HH:MM" 或 ISO
    end: str
    location: str | None = None
    notes: str | None = None

class PlanLLMResponse(BaseModel):
    items: List[PlanItemOut] = Field(default_factory=list)

def _to_today_iso(s: str) -> str:
    # "HH:MM" -> 今天 ISO；已是 ISO 就原样返回
    try:
        if len(s) <= 5 and ":" in s and "T" not in s:
            hh, mm = map(int, s.split(":")[:2])
            dt = SG.localize(datetime.combine(date.today(), time(hh, mm)))
            return dt.isoformat()
        # 简单兜底：能被 datetime 解析就返回原串
        datetime.fromisoformat(s.replace("Z","+00:00"))
        return s
    except Exception:
        return s  # 让上游去兜底/告警

def schedule_suggest_llm(prompt_text: str) -> Dict[str, Any]:
    llm = ChatOpenAI(
        model=getattr(settings, "AGENT_MODEL", "gpt-4o-mini"),
        temperature=getattr(settings, "AGENT_TEMPERATURE", 0),
        api_key=settings.OPENAI_API_KEY
    )
    tool = llm.with_structured_output(PlanLLMResponse)

    resp: PlanLLMResponse = tool.invoke([
        ("system", prompts.PLAN_SYSTEM),   # 你的排程 system 提示词
        ("user", prompt_text)
    ])

    # 统一成 React 控制器喜欢的结构：{"items":[{title,start,end,location}]}
    items = []
    for it in resp.items:
        items.append({
            "title": it.title,
            "start": _to_today_iso(it.start),
            "end":   _to_today_iso(it.end),
            "location": it.location or ""
        })
    return {"items": items}
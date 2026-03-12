from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import tool
from fastapi import Request

# ---------- memory_search（后面你再接 Weaviate） ----------
class MemoryArgs(BaseModel):
    query: str = Field(..., description="What to search in user memory")
    k: int = Field(5, ge=1, le=20, description="top-k results")
    user_id: Optional[str] = Field(None, description="Filter by user id")

@tool("memory_search", args_schema=MemoryArgs)
def memory_search_tool(query: str, k: int = 5, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search user's preferences/history. Returns a JSON list of hits:
    [{"source":"memory","text": "...", "score": 0.88, "meta": {...}}, ...]
    """
    # TODO: 用 request.app.state.vectorstore 接 Weaviate（这里先给占位数据）
    # 你可以把 request 放到全局或用 dependency 注入；LC @tool 默认不传 Request，所以先用假数据跑通。
    return [
        {"source": "memory", "text": "Prefers lunch before 12:30", "score": 0.9, "meta": {"kind": "pref"}},
    ][:k]

# ---------- knowledge_search（校内常识/静态库 或 Weaviate） ----------
class KnowledgeArgs(BaseModel):
    query: str = Field(..., description="What campus fact to search")
    k: int = Field(5, ge=1, le=20, description="top-k results")

@tool("knowledge_search", args_schema=KnowledgeArgs)
def knowledge_search_tool(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Search campus knowledge (UTown/CLB/USC etc.). Returns a JSON list of snippets.
    """
    base = [
        {"source":"knowledge","text":"UTown dining peak 11:30–13:30","score":0.8,"meta":{"loc":"UTown"}},
        {"source":"knowledge","text":"CLB is Central Library; quieter in the morning","score":0.7,"meta":{"loc":"CLB"}},
        {"source":"knowledge","text":"USC gym is busy after 17:00","score":0.6,"meta":{"loc":"USC"}},
    ]
    return base[:k]

# ---------- schedule_suggest（用你的 LLM 一次直出排程） ----------
from datetime import datetime, date, time
import pytz
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.agent import prompts  # 你的 PLAN_SYSTEM

SG = pytz.timezone("Asia/Singapore")

class PlanItemOut(BaseModel):
    title: str
    start: str               # could be "HH:MM" or ISO8601
    end: str
    location: Optional[str] = None
    notes: Optional[str] = None

class PlanLLMResponse(BaseModel):
    items: List[PlanItemOut] = Field(default_factory=list)

def _to_today_iso(s: str) -> str:
    try:
        if len(s) <= 5 and ":" in s and "T" not in s:
            hh, mm = map(int, s.split(":")[:2])
            dt = SG.localize(datetime.combine(date.today(), time(hh, mm)))
            return dt.isoformat()
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return s
    except Exception:
        return s

class ScheduleArgs(BaseModel):
    prompt: str = Field(..., description="User's scheduling request in natural language")

@tool("schedule_suggest_tool", args_schema=ScheduleArgs)
def schedule_suggest_tool(prompt: str) -> Dict[str, Any]:
    """
    Generate a feasible schedule for TODAY (Asia/Singapore).
    Returns {"items":[{"title","start","end","location"}]}
    """
    llm = ChatOpenAI(
        model=getattr(settings, "AGENT_MODEL", "gpt-4o-mini"),
        temperature=getattr(settings, "AGENT_TEMPERATURE", 0),
        api_key=settings.OPENAI_API_KEY,
    )
    tool_ = llm.with_structured_output(PlanLLMResponse)
    resp: PlanLLMResponse = tool_.invoke([
        ("system", prompts.PLAN_SYSTEM),
        ("user", prompt),
    ])
    items = []
    for it in resp.items:
        items.append({
            "title": it.title,
            "start": _to_today_iso(it.start),
            "end": _to_today_iso(it.end),
            "location": it.location or ""
        })
    return {"items": items}

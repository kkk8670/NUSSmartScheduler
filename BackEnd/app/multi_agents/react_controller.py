from __future__ import annotations
from typing import Dict, Any, Tuple, List, Optional
import json
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from app.multi_agents.dialogue_agent import dialogue_agent_tool
from app.multi_agents.knowledge_agent import knowledge_agent_tool
from app.multi_agents.memory_agent import memory_agent_tool
from app.multi_agents.reranker_agent import reranker_agent_tool
from app.multi_agents.tools.react_trace import ReactTraceHandler
from app.agent import prompts
from app.core.config import settings
from app.core.tracing import make_lc_handler
from app.multi_agents.verification_agent import verification_agent_tool
from app.tool_lc import (
    memory_search_tool,
    knowledge_search_tool,
    schedule_suggest_tool,
)

 

def run_react_agent(
    user_prompt: str,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Tuple[List[dict], Dict[str, Any]]:
    tools = [
        dialogue_agent_tool,
        memory_agent_tool,
        knowledge_agent_tool,
        reranker_agent_tool,
        schedule_suggest_tool,
        verification_agent_tool,
    ]
    llm = ChatOpenAI(
        model=getattr(settings, "AGENT_MODEL", "gpt-4o-mini-2024-07-18"),
        temperature=0,
        api_key=settings.OPENAI_API_KEY,
    )

    tracer = ReactTraceHandler()
    lf_handlers = make_lc_handler(
        trace_name="react-agent",
        user_id=user_id,
        session_id=session_id,
        metadata={"agent_model": settings.AGENT_MODEL},
    )
    all_callbacks = [tracer] + lf_handlers

    graph = create_react_agent(
        model=llm,
        tools=tools,
        prompt=prompts.REACT_SYSTEM,
    )

    result = graph.invoke(
        {"messages": [("user", user_prompt)]},
        config={"callbacks": all_callbacks},
    )

    last_msg = result["messages"][-1]
    out_str = (last_msg.content or "").strip()

    final: Dict[str, Any]
    try:
        final = json.loads(out_str)
        if not isinstance(final, dict):
            raise ValueError
        final.setdefault("reply", out_str)
        final.setdefault("plan", [])
        final.setdefault("schedule", None)
        final.setdefault("evidence", [])
        final.setdefault("notes", [])
    except Exception:
        final = {"reply": out_str, "plan": [], "schedule": None, "evidence": [], "notes": ["fallback: non-json output"]}

    return tracer.steps, final

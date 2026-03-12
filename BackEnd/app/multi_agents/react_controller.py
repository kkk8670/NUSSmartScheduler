from __future__ import annotations
from typing import Dict, Any, Tuple, List
import json

from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import render_text_description

from app.multi_agents.dialogue_agent import dialogue_agent_tool
from app.multi_agents.knowledge_agent import knowledge_agent_tool
from app.multi_agents.memory_agent import memory_agent_tool
from app.multi_agents.reranker_agent import reranker_agent_tool
from app.multi_agents.tools.react_trace import ReactTraceHandler

from app.agent import prompts
from app.core.config import settings
from app.multi_agents.verification_agent import verification_agent_tool
from app.tool_lc import (
    memory_search_tool,
    knowledge_search_tool,
    schedule_suggest_tool,
)

def build_react_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        (
            "system",
            prompts.REACT_SYSTEM
            + "\n\n---\n"
            + "Available tools:\n{tools}\n"
            + "You can call: {tool_names}"
        ),
        ("user", "{input}"),
        ("assistant", "{agent_scratchpad}"),
    ])


# def run_react_agent(user_prompt: str):
#     tools = [memory_search_tool, knowledge_search_tool, schedule_suggest_tool]
#
#     llm = ChatOpenAI(
#         model=getattr(settings, "AGENT_MODEL", "gpt-4o-mini-2024-07-18"),
#         temperature=0,
#         api_key=settings.OPENAI_API_KEY,
#     )
#
#     prompt = build_react_prompt()  # ← 不要手动渲染 tools，交给 LC
#
#     agent = create_react_agent(llm, tools, prompt)
#     executor = AgentExecutor(
#         agent=agent,
#         tools=tools,
#         verbose=True,
#         handle_parsing_errors=True,
#         max_iterations=4,
#     )
#
#     result = executor.invoke({"input": user_prompt})
#     # result["output"] 多半是字符串，这里按你需要做 JSON 解析/兜底
#     out_str = (result.get("output") or "").strip()
#     try:
#         import json
#         return json.loads(out_str)
#     except Exception:
#         return {"reply": out_str, "plan": [], "schedule": None, "evidence": [], "notes": ["[fallback] non-json output"]}




def run_react_agent(user_prompt: str) -> Tuple[List[dict], Dict[str, Any]]:
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

    prompt = build_react_prompt()  # 交给 LC 绑定工具，不手工渲染

    agent = create_react_agent(llm, tools, prompt)
    tracer = ReactTraceHandler()
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,                  # 必须打开，便于回调拿到日志
        handle_parsing_errors=True,
        max_iterations=12,
        return_intermediate_steps=True,
        callbacks=[tracer],            # 关键：挂上回调
    )

    result = executor.invoke({"input": user_prompt})

    # 最终输出通常在 result["output"]，可能是 JSON 字符串
    out_str = (result.get("output") or "").strip()
    final: Dict[str, Any]
    try:
        import json
        final = json.loads(out_str)
        # 期望结构：{"reply": str, "plan": [...], "schedule": ..., "evidence": [...], "notes": [...]}
        if not isinstance(final, dict):
            raise ValueError("final is not dict")
        # 兜底字段
        final.setdefault("reply", out_str)
        final.setdefault("plan", [])
        final.setdefault("schedule", None)
        final.setdefault("evidence", [])
        final.setdefault("notes", [])
    except Exception:
        final = {"reply": out_str, "plan": [], "schedule": None, "evidence": [], "notes": ["fallback: non-json output"]}

    return tracer.steps, final

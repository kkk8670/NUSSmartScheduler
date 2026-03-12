# app/agent/graph_compare.py
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.services.travel_graph import load_travel_graph
from app.services.scheduler import solve_plan
from app.schemas.tasks import TaskIn
from app.agent.prompts import AI_TUNE_SYSTEM
import json

class CompareState(TypedDict):
    tasks: List[TaskIn]
    commute_mode: str
    mode_b: str                  # "compact" or "preference"
    G: object
    plan_travel: Optional[list]
    plan_b: Optional[list]
    tuned_tasks: Optional[List[TaskIn]]
    tuned_mode: Optional[str]
    plan_ai: Optional[list]
    messages: list

def load_graph(s: CompareState):
    return {"G": load_travel_graph(s.get("commute_mode","auto"))}

def baseline_travel(s: CompareState):
    return {"plan_travel": solve_plan(s["G"], s["tasks"], mode="travel")}

def baseline_b(s: CompareState):
    return {"plan_b": solve_plan(s["G"], s["tasks"], mode=s.get("mode_b","compact"))}

def ai_tune(s: CompareState):
    llm = ChatOpenAI(
        model=settings.AGENT_MODEL,
        temperature=settings.AGENT_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY
    )
    sys = SystemMessage(content=AI_TUNE_SYSTEM)
    human = HumanMessage(content=json.dumps({
        "tasks": [t.model_dump() for t in s["tasks"]],
        "baseline_travel": s.get("plan_travel", []),
        "baseline_b": s.get("plan_b", []),
        "commute_mode": s.get("commute_mode","auto")
    }))
    resp = llm.invoke([sys, human]).content
    tuned = {"tuned_tasks": s["tasks"], "tuned_mode": "travel"}
    try:
        data = json.loads(resp)
        tuned["tuned_tasks"] = data.get("tuned_tasks", tuned["tuned_tasks"])
        tuned["tuned_mode"] = data.get("tuned_mode", tuned["tuned_mode"])
    except Exception:
        pass
    return tuned

def _ensure_task_models(tasks):
    out = []
    for x in tasks:
        if isinstance(x, TaskIn):
            out.append(x)
        else:
            # Pydantic v2：model_validate；v1 用 parse_obj
            out.append(TaskIn.model_validate(x))
    return out

def ai_plan(s: CompareState):
    raw_tasks = s.get("tuned_tasks", s["tasks"])
    tasks = _ensure_task_models(raw_tasks)  # ← 关键一步：把 dict 转成 TaskIn
    items = solve_plan(
        s["G"],
        tasks,
        mode=s.get("tuned_mode", "travel")
    )
    return {"plan_ai": items}

def build_graph():
    g = StateGraph(CompareState)
    g.add_node("load_graph", load_graph)
    g.add_node("baseline_travel", baseline_travel)
    g.add_node("baseline_b", baseline_b)
    g.add_node("ai_tune", ai_tune)
    g.add_node("ai_plan", ai_plan)
    g.set_entry_point("load_graph")
    g.add_edge("load_graph","baseline_travel")
    g.add_edge("load_graph","baseline_b")
    g.add_edge("baseline_travel","ai_tune")
    g.add_edge("baseline_b","ai_tune")
    g.add_edge("ai_tune","ai_plan")
    g.add_edge("ai_plan", END)
    return g.compile()


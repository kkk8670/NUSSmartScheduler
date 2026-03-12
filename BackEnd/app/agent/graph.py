# app/agent/graph.py
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.services.scheduler import solve_plan
from app.services.travel_graph import load_travel_graph
from app.schemas.tasks import TaskIn

class PlanState(TypedDict):
    messages: list
    tasks_def: List[TaskIn]
    commute_mode: str
    mode: str
    G: object
    items: Optional[list]

def load_graph_node(s: PlanState):
    return {"G": load_travel_graph(s.get("commute_mode","auto"))}

def solve_node(s: PlanState):
    items = solve_plan(s["G"], s["tasks_def"], mode=s.get("mode","travel"))
    return {"items": items}

def explain_if_empty_node(s: PlanState):
    if s.get("items"):
        return {}
    llm = ChatOpenAI(
        model=settings.AGENT_MODEL,
        temperature=settings.AGENT_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY
    )
    msg = llm.invoke([
        SystemMessage(content="Explain infeasible schedule briefly and propose what to relax."),
        HumanMessage(content=str({"tasks": [t.model_dump() for t in s["tasks_def"]]}))
    ])
    return {"messages": s.get("messages", []) + [msg]}

def build_graph():
    g = StateGraph(PlanState)
    g.add_node("load_graph", load_graph_node)
    g.add_node("solve", solve_node)
    g.add_node("explain", explain_if_empty_node)
    g.set_entry_point("load_graph")
    g.add_edge("load_graph","solve")
    g.add_edge("solve","explain")
    g.add_edge("explain", END)
    return g.compile()

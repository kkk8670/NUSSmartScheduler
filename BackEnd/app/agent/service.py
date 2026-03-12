from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel

from app.agent.graph import build_graph
from app.agent.graph_compare import build_graph as build_compare_graph
from app.schemas.tasks import TaskIn

class PlanReq(BaseModel):
    tasks: List[TaskIn]
    commute_mode: str = "auto"
    mode: str = "travel"  # "travel" | "compact" | "preference"

class PlanRes(BaseModel):
    items: List[dict]
    trace: Dict[str, Any]

class CompareReq(BaseModel):
    tasks: List[TaskIn]
    commute_mode: str = "auto"
    baseline_b: str = "compact"  # "compact" | "preference"

class CompareRes(BaseModel):
    plans: List[Dict[str, Any]]
    trace: Dict[str, Any]

class AgentService:
    """LangGraph 编排的唯一服务入口。"""

    def __init__(self) -> None:
        # 预编译两套图，避免每次请求重复构建
        self._graph = build_graph()
        self._compare_graph = build_compare_graph()

    def plan(self, req: PlanReq) -> PlanRes:
        state = {
            "messages": [],
            "tasks_def": req.tasks,
            "commute_mode": req.commute_mode,
            "mode": req.mode,
        }
        out = self._graph.invoke(state)
        return PlanRes(
            items=out.get("items", []),
            trace={
                "mode": req.mode,
                "commute_mode": req.commute_mode,
                "nodes": ["load_graph", "solve", "explain"],
            },
        )

    def compare(self, req: CompareReq) -> CompareRes:
        state = {
            "tasks": req.tasks,
            "commute_mode": req.commute_mode,
            "mode_b": req.baseline_b,
            "messages": [],
        }
        out = self._compare_graph.invoke(state)
        plans = [
            {
                "id": "baseline_travel",
                "label": "Baseline · Travel",
                "source": "baseline",
                "items": out.get("plan_travel", []),
            },
            {
                "id": f"baseline_{req.baseline_b}",
                "label": f"Baseline · {req.baseline_b.title()}",
                "source": "baseline",
                "items": out.get("plan_b", []),
            },
            {
                "id": "ai_plan",
                "label": "AI Plan · Soft-relaxed",
                "source": "ai",
                "items": out.get("plan_ai", []),
            },
        ]
        return CompareRes(
            plans=plans,
            trace={
                "commute_mode": req.commute_mode,
                "baseline_b": req.baseline_b,
                "nodes": ["load_graph", "baseline_travel", "baseline_b", "ai_tune", "ai_plan"],
            },
        )

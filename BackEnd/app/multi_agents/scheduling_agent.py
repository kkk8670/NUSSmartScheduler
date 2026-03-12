from __future__ import annotations
from typing import List

from .base import Agent, State, Schedule, ScheduleItem

try:
    from app.services.travel_graph import load_travel_graph  # type: ignore
    from app.services.scheduler import solve_plan  # type: ignore
    from app.schemas.tasks import TaskIn  # type: ignore
except Exception:
    load_travel_graph = None  # type: ignore
    solve_plan = None  # type: ignore
    TaskIn = None  # type: ignore


class SchedulingAgent(Agent):


    name = "scheduling"

    def run(self, state: State) -> State:
        # Only run scheduling if the solver is available
        if not solve_plan or not TaskIn or not load_travel_graph:
            state.notes.append("[Scheduling] solver not available; skipping scheduling")
            return state

        # Convert plan items into TaskIn objects
        tasks: List[TaskIn] = []
        for p in state.plan:
            # create TaskIn; fallback attributes if missing
            kwargs = {
                "id": p.id,
                "title": p.title,
                "location": p.where_hint or "",
                "earliest": p.when_hint,
                "latest": None,
                "duration_min": p.duration_min or 60,
                "priority": 1,
                "fixed": False,
                "prefer_win": [],
            }
            try:
                task = TaskIn.model_validate(kwargs)  # type: ignore
            except Exception:
                # If model_validate doesn't exist (pydantic v1), use parse_obj
                task = TaskIn.parse_obj(kwargs)  # type: ignore
            tasks.append(task)

        # Load travel graph based on user preferences
        commute_mode = getattr(state.preferences, "commute_mode", "auto")
        G = load_travel_graph(commute_mode)

        # Solve the plan; expect a list of dicts with keys id/title/loc/start/end
        try:
            result_items = solve_plan(G, tasks, mode="travel")
        except Exception:
            result_items = []

        schedule_items: List[ScheduleItem] = []
        for item in result_items or []:
            schedule_items.append(
                ScheduleItem(
                    id=item.get("id", ""),
                    title=item.get("title", ""),
                    start=item.get("start", ""),
                    end=item.get("end", ""),
                    location=item.get("loc", None),
                )
            )

        state.schedule = Schedule(items=schedule_items, objective={})
        state.notes.append(f"[Scheduling] scheduled {len(schedule_items)} items")
        return state

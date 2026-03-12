from __future__ import annotations
from typing import List, Optional, Dict, Any
from uuid import uuid4
from fastapi import Request
from pydantic import BaseModel, Field


class Message(BaseModel):
    """A message exchanged between user, system or agents."""

    role: str
    content: str


class PlanItem(BaseModel):
    """A simple representation of a high level task."""

    id: str
    title: str
    when_hint: Optional[str] = None
    where_hint: Optional[str] = None
    duration_min: Optional[int] = 60
    deps: List[str] = Field(default_factory=list)


class Evidence(BaseModel):
    """A piece of evidence supporting a scheduled item."""

    source: str
    snippet: str
    score: float = 0.0


class ScheduleItem(BaseModel):
    """Represents a single scheduled block."""

    id: str
    title: str
    start: str
    end: str
    location: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class Schedule(BaseModel):
    """Collection of scheduled items together with an objective or cost."""

    items: List[ScheduleItem] = Field(default_factory=list)
    objective: Dict[str, Any] = Field(default_factory=dict)


class Preferences(BaseModel):
    """User specific preferences that influence planning and scheduling."""

    walk_threshold_min: int = 12
    preferred_buildings: List[str] = Field(default_factory=list)
    lunch_window: List[int] = [12 * 60, 14 * 60]  # [start_minute, end_minute]
    weights: Dict[str, float] = {"walk": 1.0, "bus": 0.8, "breaks": 1.0}
    commute_mode: str = "auto"


class State(BaseModel):
    """
    Global state exchanged between agents in the pipeline.

    Agents read from and write to this state. As new information becomes
    available (e.g. parsed plans, retrieved docs, scheduled items) it is
    stored here.
    """

    messages: List[Message] = Field(default_factory=list)
    plan: List[PlanItem] = Field(default_factory=list)
    queries: List[str] = Field(default_factory=list)
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    ranked: List[Dict[str, Any]] = Field(default_factory=list)
    schedule: Optional[Schedule] = None
    evidence: List[Evidence] = Field(default_factory=list)
    preferences: Preferences = Preferences()
    constraints: Dict[str, Any] = Field(default_factory=dict)
    ok: bool = True
    notes: List[str] = Field(default_factory=list)
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    request: Optional[Request] = None
    memories: List[Dict[str, Any]] = Field(default_factory=list)

    def brief(self) -> dict:
        """用于日志的轻量摘要，不泄露大文本。"""
        return {
            "msg_count": len(self.messages),
            "plan_count": len(self.plan),
            "cands": len(self.candidates),
            "ranked": len(self.ranked),
            "sched_items": len(self.schedule.items) if self.schedule else 0,
            "evidences": len(self.evidence),
            "ok": self.ok,
        }

    model_config = {
        "arbitrary_types_allowed": True
    }


class Agent:
    """
    Base class for all agents. Each agent implements a `run` method that
    takes the current state and returns an updated state.
    """

    name: str = "base"

    def run(self, state: State) -> State:
        raise NotImplementedError("Agents must implement the run method")

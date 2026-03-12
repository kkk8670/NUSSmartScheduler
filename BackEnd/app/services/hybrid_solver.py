from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Callable
import random

from ..schemas.tasks import TaskIn
from ..utils.timeutils import to_slot, slot_to_hhmm
from ..core.constants import DAY_START, DAY_END, SLOT_MIN

@dataclass
class _LiteTask:
    id: str
    title: str
    loc: str
    duration: int  # in slots
    window: Tuple[int, int]  # (earliest_slot, latest_slot)
    priority: int
    fixed: bool
    prefer_win: Optional[List[Tuple[int, int]]]


@dataclass
class _Placed:
    id: str
    title: str
    loc: str
    start: int
    end: int


class HybridScheduler:
    """
    Hybrid greedy + local search solver for task scheduling.
    """

    def __init__(self, travel_fn: Callable[[object, str, str], int], mode: str = "travel") -> None:
        self.travel_fn = travel_fn
        self.mode = mode
        print(f"[HYBRID] Initializing HybridScheduler with mode={self.mode}")  # << LOG

    def _feasible_insert(
        self, sched: List[_Placed], task: _LiteTask, start: int, H: int, G: object
    ) -> bool:
        end = start + task.duration
        a, b = task.window
        if start < a or start > min(b, H - task.duration):
            return False
        for p in sched:
            if not (end <= p.start or start >= p.end):
                return False
        before = None
        for p in sched:
            if p.end <= start and (before is None or p.end > before.end):
                before = p
        after = None
        for p in sched:
            if p.start >= end and (after is None or p.start < after.start):
                after = p
        if before:
            need = self.travel_fn(G, before.loc, task.loc)
            if start < before.end + need:
                return False
        if after:
            need = self.travel_fn(G, task.loc, after.loc)
            if after.start < end + need:
                return False
        return True

    # -------------------------
    # Objective function
    # -------------------------
    def _objective(self, sched: List[_Placed], tasks: Dict[str, _LiteTask], G: object) -> int:
        travel_cost = 0
        ordered = sorted(sched, key=lambda p: p.start)
        for i in range(len(ordered) - 1):
            travel_cost += self.travel_fn(G, ordered[i].loc, ordered[i + 1].loc)

        preference_cost = 0
        if self.mode == "preference":
            for p in ordered:
                t = tasks[p.id]
                if t.prefer_win:
                    ok = False
                    for a, b in t.prefer_win:
                        if a <= p.start <= b:
                            ok = True
                            break
                    if not ok:
                        preference_cost += 10

        makespan = 0
        if self.mode == "compact" and ordered:
            makespan = ordered[-1].end - ordered[0].start

        priority_reward = 0
        for p in ordered:
            priority_reward += tasks[p.id].priority

        cost = travel_cost + preference_cost + makespan - priority_reward
        return cost

    def _build_initial(self, tasks: List[_LiteTask], H: int, G: object) -> List[_Placed]:
        def sort_key(t: _LiteTask):
            span = max(1, t.window[1] - t.window[0])
            fixed_priority = 1000 if t.fixed else 0
            return (-(1000 / span + fixed_priority), t.priority, -span)

        ordered = sorted(tasks, key=sort_key)
        schedule: List[_Placed] = []
        print(f"[HYBRID] Building initial solution with {len(tasks)} tasks")  # << LOG

        for t in ordered:
            placed = False
            earliest_start = t.window[0]
            latest_start = min(t.window[1], H - t.duration)
            for s in range(earliest_start, latest_start + 1):
                if self._feasible_insert(schedule, t, s, H, G):
                    schedule.append(_Placed(t.id, t.title, t.loc, s, s + t.duration))
                    placed = True
                    break
            if not placed and t.fixed:
                schedule.append(_Placed(t.id, t.title, t.loc, H + 1000, H + 1000 + t.duration))

        print(f"[HYBRID] Initial solution built: {len(schedule)} tasks placed")  # << LOG
        return schedule

    # -------------------------
    # Local search (Move + Swap)
    # -------------------------
    def _local_search(
        self,
        base: List[_Placed],
        tasks: Dict[str, _LiteTask],
        H: int,
        G: object,
        iterations: int = 300,
    ) -> List[_Placed]:
        print(f"[HYBRID] Starting local search with {iterations} iterations")  # << LOG

        rng = random.Random(42)
        best = [p for p in base]
        best_cost = self._objective(best, tasks, G)

        for _ in range(iterations):
            cand = [p for p in best]
            op = rng.random()
            if op < 0.5 and cand:
                k = rng.randrange(len(cand))
                p = cand.pop(k)
                t = tasks[p.id]
                shift = rng.choice([-3, -2, -1, 1, 2, 3])
                new_start = p.start + shift
                new_start = max(t.window[0], min(new_start, t.window[1], H - t.duration))
                if self._feasible_insert(cand, t, new_start, H, G):
                    cand.append(_Placed(p.id, p.title, p.loc, new_start, new_start + t.duration))
                else:
                    cand.append(p)
            else:
                if len(cand) >= 2:
                    i, j = rng.sample(range(len(cand)), 2)
                    pi, pj = cand[i], cand[j]
                    ti, tj = tasks[pi.id], tasks[pj.id]
                    rest = [cand[m] for m in range(len(cand)) if m not in (i, j)]
                    if self._feasible_insert(rest, ti, pj.start, H, G) and \
                       self._feasible_insert(rest, tj, pi.start, H, G):
                        cand[i] = _Placed(pi.id, pi.title, pi.loc, pj.start, pj.start + ti.duration)
                        cand[j] = _Placed(pj.id, pj.title, pj.loc, pi.start, pi.start + tj.duration)

            cost = self._objective(cand, tasks, G)
            if cost < best_cost or rng.random() < 0.05:
                best = cand
                best_cost = cost

        print(f"[HYBRID] Local search finished. Best cost = {best_cost}")  # << LOG
        print(f"[HYBRID] Final schedule size = {len(best)} tasks")         # << LOG
        return best

    # -------------------------
    # Public solve() API
    # -------------------------
    def solve(self, G: object, tasks_def: List[TaskIn]) -> List[Dict[str, str]]:
        print(f"[HYBRID] solve() called with {len(tasks_def)} TaskIn")  # << LOG

        H = int((DAY_END - DAY_START).total_seconds() // 60 // SLOT_MIN)
        lite_tasks: List[_LiteTask] = []
        for t in tasks_def:
            dur = max(1, int((t.duration_min + SLOT_MIN - 1) // SLOT_MIN))
            est = max(0, to_slot(t.earliest))
            let = min(H, to_slot(t.latest))
            prefer = None
            if t.prefer_win:
                p_list = []
                for a, b in t.prefer_win:
                    p_list.append((max(0, to_slot(a)), max(0, to_slot(b))))
                prefer = p_list

            lite_tasks.append(
                _LiteTask(
                    id=t.id,
                    title=t.title,
                    loc=t.location,
                    duration=dur,
                    window=(est, let),
                    priority=int(t.priority),
                    fixed=bool(getattr(t, "fixed", False)),
                    prefer_win=prefer,
                )
            )

        initial = self._build_initial(lite_tasks, H, G)
        task_map = {t.id: t for t in lite_tasks}

        improved = self._local_search(initial, task_map, H, G)

        items: List[Dict[str, str]] = []
        for p in improved:
            if p.start > H:
                continue
            items.append(
                {
                    "id": p.id,
                    "title": p.title,
                    "loc": p.loc,
                    "start": slot_to_hhmm(p.start),
                    "end": slot_to_hhmm(p.end),
                }
            )

        items.sort(key=lambda x: x["start"])
        print(f"[HYBRID] solve() finished. Returned {len(items)} tasks")  # << LOG
        return items

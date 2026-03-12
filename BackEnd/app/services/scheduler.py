from typing import List
from fastapi import HTTPException
from ortools.sat.python import cp_model
from math import ceil

from .travel_graph import travel_slots
from ..schemas.tasks import TaskIn
from ..utils.timeutils import to_slot, slot_to_hhmm
from ..core.constants import DAY_START, DAY_END, SLOT_MIN


def solve_plan(G, tasks_def: List[TaskIn], mode: str = "travel", engine: str = "cp"):
    """Plan a list of tasks using either CP‑SAT or a custom hybrid solver.

    :param G: the travel graph instance
    :param tasks_def: list of tasks to schedule
    :param mode: objective mode; one of ``"travel"``, ``"preference"``, ``"compact"``
    :param engine: solver backend; ``"cp"`` (default) uses OR‑Tools CP‑SAT,
        ``"hybrid"`` uses a custom greedy/local search solver defined in
        :mod:`app.services.hybrid_solver`.  Additional values fall back to
        ``"cp"``.

    The return value is a list of dicts each with ``id``, ``title``,
    ``loc``, ``start`` and ``end`` keys where ``start`` and ``end`` are
    ``HH:MM`` formatted strings.  This signature is backwards
    compatible with earlier versions; callers that ignore the
    ``engine`` parameter will continue to use the CP based solver.
    """

    # If the hybrid engine is requested, delegate to the custom solver.
    if engine == "hybrid":
        # Import lazily to avoid pulling in heavy modules on CP code path
        from .hybrid_solver import HybridScheduler
        # Instantiate solver with the travel time callback and mode
        hs = HybridScheduler(travel_fn=travel_slots, mode=mode)
        return hs.solve(G, tasks_def)


    # 总 horizon（单位：slot）
    H = int((DAY_END - DAY_START).total_seconds() // 60 // SLOT_MIN)
    model = cp_model.CpModel()

    starts, ends, pres, itvs = {}, {}, {}, {}

    # --- 定义变量 ---
    for t in tasks_def:
        dur = max(1, ceil(t.duration_min / SLOT_MIN))
        est = max(0, to_slot(t.earliest))     # earliest start
        let = min(H, to_slot(t.latest))       # latest start

        if est > let:
            raise HTTPException(400, f"Invalid window for task '{t.title}': earliest > latest")

        # start domain: earliest ≤ s ≤ min(latest, H - dur)
        s_lb = est
        s_ub = min(let, H - dur)
        if s_lb > s_ub:
            # 窗口太窄导致完全不可行 → 这个任务永远无法被排入
            s_ub = s_lb  # 给个退化域，后面 pres=0 时就会被丢弃

        # end domain: 宽一些，保证 interval 可行
        e_lb = s_lb + dur
        e_ub = min(let + dur, H)

        s = model.NewIntVar(s_lb, s_ub, f"s_{t.id}")
        e = model.NewIntVar(e_lb, e_ub, f"e_{t.id}")
        p = model.NewBoolVar(f"p_{t.id}")
        itv = model.NewOptionalIntervalVar(s, dur, e, p, f"iv_{t.id}")

        starts[t.id], ends[t.id], pres[t.id], itvs[t.id] = s, e, p, itv
        if t.fixed:
            model.Add(p == 1)

    # --- 不重叠约束 ---
    model.AddNoOverlap(list(itvs.values()))

    # --- travel 顺序约束 ---
    for i in range(len(tasks_def)):
        for j in range(i + 1, len(tasks_def)):
            ti, tj = tasks_def[i], tasks_def[j]
            lij = travel_slots(G, ti.location, tj.location)
            lji = travel_slots(G, tj.location, ti.location)

            bij = model.NewBoolVar(f"{ti.id}_before_{tj.id}")
            bji = model.NewBoolVar(f"{tj.id}_before_{ti.id}")

            # 只有两者都被选中时，必须有一个先一个后
            model.Add(bij + bji == 1).OnlyEnforceIf([pres[ti.id], pres[tj.id]])

            model.Add(starts[tj.id] >= ends[ti.id] + lij).OnlyEnforceIf(
                [pres[ti.id], pres[tj.id], bij]
            )
            model.Add(starts[ti.id] >= ends[tj.id] + lji).OnlyEnforceIf(
                [pres[tj.id], pres[ti.id], bji]
            )

    # --- 目标函数 ---
    penalties: list = []
    if mode == "travel":

        pass
    elif mode == "preference":
        for t in tasks_def:
            if t.prefer_win:
                for a, b in t.prefer_win:
                    a_s, b_s = to_slot(a), to_slot(b)
                    good = model.NewBoolVar(f"pref_{t.id}_{a}_{b}")
                    # 只有任务存在时才考虑偏好
                    model.Add(starts[t.id] >= a_s).OnlyEnforceIf([good, pres[t.id]])
                    model.Add(starts[t.id] <= b_s).OnlyEnforceIf([good, pres[t.id]])
                    penalties.append(-5 * good)
    elif mode == "compact":
        makespan = model.NewIntVar(0, H, "makespan")
        for t in tasks_def:
            model.Add(ends[t.id] <= makespan).OnlyEnforceIf(pres[t.id])
        penalties.append(makespan)

    # base reward: priority
    for t in tasks_def:
        penalties.append(-int(t.priority) * pres[t.id])

    if penalties:
        model.Minimize(sum(penalties))

    # --- 求解 (CP‑SAT) ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    status = solver.Solve(model)

    items = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for t in tasks_def:
            if solver.Value(pres[t.id]):
                s = solver.Value(starts[t.id])
                e = solver.Value(ends[t.id])
                items.append(
                    {
                        "id": t.id,
                        "title": t.title,
                        "loc": t.location,
                        "start": slot_to_hhmm(s),
                        "end": slot_to_hhmm(e),
                    }
                )

    items.sort(key=lambda x: x["start"])
    return items

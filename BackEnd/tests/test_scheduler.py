# BackEnd/tests/test_scheduler.py

"""
Measure two things:
  A. Time conversion (to_slot / slot_to_hhmm)
  B. CP-SAT scheduling constraints
"""

import pytest
import networkx as nx
from fastapi import HTTPException

from app.utils.timeutils import to_slot, slot_to_hhmm
from app.schemas.tasks import TaskIn
from app.services.scheduler import solve_plan


# ─────── Assistant: Construct a fake travel graph  ──────────────
# solve_plan needs to be passed into networkx DiGraph, which replaces the travel_times table in the real database.

def make_graph(edges: dict) -> nx.DiGraph:
    """
    edges: { ("COM1", "USC"): 3, ... }  value: number of slot
    """
    G = nx.DiGraph()
    for (a, b), slots in edges.items():
        G.add_edge(a, b, slots=slots, minutes=slots * 5)
    return G


# 3 slots (15 minutes) commute between two locations
TWO_LOC_GRAPH = make_graph({
    ("COM1", "USC"): 3,
    ("USC", "COM1"): 3,
})

# Same loc does not need an edge, travel_slots returns 0 when it encounters the same loc
SAME_LOC_GRAPH = make_graph({})


# ─────── Assistant: Construct TaskIn ───────────────────────────

def make_task(id, title, location, earliest, latest, duration_min,
              fixed=False, priority=2, prefer_win=None):
    return TaskIn(
        id=id, title=title, location=location,
        earliest=earliest, latest=latest,
        duration_min=duration_min,
        fixed=fixed, priority=priority,
        prefer_win=prefer_win,
    )


# ════════════════════════════════════════════════════════════════════════════
# 小块 A：时间换算
#
# 为什么分三个 func：
#   换算依赖两个配置参数 DAY_START（基准）和 SLOT_MIN（步长），
#   任何一个出错都会让所有排程时间静默偏移。
#   分开测才能在失败时立刻知道是基准错了还是步长错了。
#   再加一个双向互逆验证，确保两个函数不会各自正确但合在一起出错。
# ════════════════════════════════════════════════════════════════════════════

class TestTimeUtils:
    """
    Time conversion
    to test:
    1. start
    2. slot_min
    3. slot_to_hhmm
    """

    def test_to_slot_day_start_is_zero(self):
        """
        DAY_START: 08:00 must map to slot 0
        """

        assert to_slot("08:00") == 0

    def test_to_slot_one_slot_increment(self):
        """
        SLOT_MIN: 8:05 must map to slot 1 
        test SLOT_MIN=5
        """
        assert to_slot("08:05") == 1

    def test_roundtrip(self):
        """
        For any legal time, slot_to_hhmm(to_slot(t)) must revert back to the original value.
        """
        for t in ["08:00", "09:30", "13:00", "21:55"]:
            assert slot_to_hhmm(to_slot(t)) == t


# ════════════════════════════════════════════════════════════════════════════
# 小块 B：CP-SAT 调度约束
#
# 为什么分五个 func：
#   代码里手写了四类约束：不重叠、travel gap、fixed 强制、时间窗口。
#   每类约束独立存在，对应一个业务需求，写错了不会报错只会结果违反约束。
#   所以每条约束需要一个独立的 func，构造刚好能触发它的最小场景。
#   额外加一个测不可行输入的 func，因为它走的是提前拦截逻辑，性质不同。
# ════════════════════════════════════════════════════════════════════════════

class TestSolvePlan:
    """
    CP-SAT scheduling constraints
    """

    def test_no_overlap(self):
        """
        No overlap in time between the two tasks once they are scheduled.
        """
        tasks = [
            make_task("t1", "Study", "COM1", "09:00", "12:00", 60),
            make_task("t2", "Meeting", "COM1", "09:00", "12:00", 60),
        ]
        items = solve_plan(SAME_LOC_GRAPH, tasks, engine="cp")
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                assert items[i]["end"] <= items[j]["start"] or \
                       items[j]["end"] <= items[i]["start"]

    def test_travel_gap_respected(self):
        """
        For tasks at two different locations, the interval between the end of the first task and the start of the second task must be ≥ travel slots.
        """
        tasks = [
            make_task("t1", "Study",  "COM1", "09:00", "12:00", 60),
            make_task("t2", "Lunch",  "USC",  "09:00", "14:00", 45),
        ]
        items = solve_plan(TWO_LOC_GRAPH, tasks, engine="cp")
        assert len(items) == 2
        items_sorted = sorted(items, key=lambda x: x["start"])
        first, second = items_sorted[0], items_sorted[1]
        # 3 slots = 15 min
        end_slot   = to_slot(first["end"])
        start_slot = to_slot(second["start"])
        assert start_slot - end_slot >= 3

    def test_fixed_task_always_scheduled(self):
        """
        Fixed tasks are tasks that the user explicitly specifies cannot be lost.
        """
        tasks = [
            make_task("t1", "Exam", "COM1", "10:00", "11:00", 60, fixed=True),
            make_task("t2", "Study", "COM1", "09:00", "12:00", 60),
        ]
        items = solve_plan(SAME_LOC_GRAPH, tasks, engine="cp")
        ids = [item["id"] for item in items]
        assert "t1" in ids

    def test_infeasible_window_raises_400(self):
        """
        Tasks with earliest > latest should return 400, which is explicitly intercepted before going to solver.
        """
        tasks = [
            make_task("t1", "Study", "COM1", "12:00", "09:00", 60),
        ]
        with pytest.raises(HTTPException) as exc_info:
            solve_plan(SAME_LOC_GRAPH, tasks, engine="cp")
        assert exc_info.value.status_code == 400

    def test_result_within_time_window(self):
        """
        Hard sequential logic constraints on the time window, for each scheduled task, start must be >= earliest and end must be <= latest.
        """
        tasks = [
            make_task("t1", "Study",   "COM1", "09:00", "11:00", 60),
            make_task("t2", "Meeting", "COM1", "13:00", "15:00", 45),
        ]
        items = solve_plan(SAME_LOC_GRAPH, tasks, engine="cp")
        task_map = {t.id: t for t in tasks}
        for item in items:
            t = task_map[item["id"]]
            assert item["start"] >= t.earliest
            assert item["end"]   <= t.latest
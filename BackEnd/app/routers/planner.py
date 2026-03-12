from fastapi import APIRouter, HTTPException
from ..schemas.tasks import GenerateReq
from ..services.travel_graph import load_travel_graph, travel_slots
from ..services.scheduler import solve_plan
from ..core.constants import SLOT_MIN


router = APIRouter()


@router.post("/generate")
def api_generate(req: GenerateReq):
    print(req)
    if not req.tasks:
        raise HTTPException(400, "No tasks provided.")
    for t in req.tasks:
        if t.earliest > t.latest:
            raise HTTPException(400, f"Earliest must be <= Latest for task '{t.title}'")


    cm = (req.commuteMode or "bus").lower()
    if cm == "transit":
        cm = "bus"
    G = load_travel_graph(cm)


    modes = [
        ("Travel-first", "Minimize inter-location travel", "indigo", "travel"),
        ("Preference-first", "Maximize preferred windows", "emerald", "preference"),
        ("Compact-day", "Minimize makespan", "sky", "compact"),
    ]


    plans, all_timelines = [], []


    for idx, (title, desc, color, mode_key) in enumerate(modes):
        items = solve_plan(G, req.tasks, mode=mode_key, engine="hybrid")


        total_travel_slots = 0
        for i in range(len(items) - 1):
            a, b = items[i]["loc"], items[i + 1]["loc"]
            total_travel_slots += travel_slots(G, a, b)
        total_travel_min = total_travel_slots * SLOT_MIN


        timeline = [
            {
                "title": it["title"],
                "loc": it["loc"],
                "start": it["start"],
                "end": it["end"],
                "travel": f"{total_travel_min}′" if len(items) > 1 else "—",
                "color": color,
            }
            for it in items
        ]


        plans.append({
            "title": title,
            "desc": desc,
            "meta": f"{len(items)} tasks · {total_travel_min}′ travel",
            "active": (idx == 0)
        })
        all_timelines.append(timeline)
        print({"ok": True, "plans": plans, "all_timelines": all_timelines})
    return {"ok": True, "plans": plans, "all_timelines": all_timelines}
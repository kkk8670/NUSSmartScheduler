# app/agent/tools.py
from langchain_core.tools import tool
from app.services.travel_graph import load_travel_graph, travel_slots

@tool
def eta_slots(loc_from: str, loc_to: str, mode: str="auto") -> int:
    """Return slot count (SLOT_MIN units) between two locations."""
    G = load_travel_graph(mode)
    return travel_slots(G, loc_from, loc_to)


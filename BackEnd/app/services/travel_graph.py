import math
import networkx as nx
import pandas as pd
from sqlalchemy import text
from ..db.session import get_engine
from ..core.constants import SLOT_MIN




def _build_graph(df: pd.DataFrame) -> nx.DiGraph:
    G = nx.DiGraph()
    for _, r in df.iterrows():
        minutes = int(r["minutes"])
        slots = math.ceil(minutes / SLOT_MIN)
        G.add_edge(r["loc_from"], r["loc_to"], minutes=minutes, slots=slots)
    return G




def load_travel_graph(commute_mode: str = "bus") -> nx.DiGraph:
    eng = get_engine()
    if commute_mode in ("bus", "transit"):
        df = pd.read_sql(text("SELECT loc_from, loc_to, minutes FROM travel_times WHERE mode='bus'"), eng)
        return _build_graph(df)
    elif commute_mode == "walk":
        df = pd.read_sql(text("SELECT loc_from, loc_to, minutes FROM travel_times WHERE mode='walk'"), eng)
        return _build_graph(df)
    elif commute_mode == "auto":
        df = pd.read_sql(
            text(
                """
                SELECT loc_from, loc_to, MIN(minutes) AS minutes
                FROM travel_times
                WHERE mode IN ('bus','walk')
                GROUP BY loc_from, loc_to
                """
            ),
            eng,
        )
        return _build_graph(df)
    else:
        df = pd.read_sql(text("SELECT loc_from, loc_to, minutes FROM travel_times WHERE mode='bus'"), eng)
        return _build_graph(df)




def travel_slots(G: nx.DiGraph, a: str, b: str) -> int:
    if a == b:
        return 0
    try:
        return nx.dijkstra_path_length(G, a, b, weight="slots")
    except Exception:
        return 9999
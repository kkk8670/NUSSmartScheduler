from fastapi import APIRouter
from sqlalchemy import text
from ..db.session import get_engine


router = APIRouter()


@router.get("/locations")
def get_locations():
    eng = get_engine()
    sql = text(
        """
        SELECT DISTINCT loc_from AS loc FROM travel_times
        UNION
        SELECT DISTINCT loc_to FROM travel_times
        """
    )
    with eng.begin() as conn:
        rows = conn.execute(sql).fetchall()
    return {"locations": [r[0] for r in rows]}
from datetime import timedelta
from ..core.constants import DAY_START, SLOT_MIN
def to_slot(hhmm: str) -> int:
    hh, mm = map(int, hhmm.split(":"))
    return (hh - DAY_START.hour) * 60 // SLOT_MIN + mm // SLOT_MIN
def slot_to_hhmm(slot: int) -> str:
    t = DAY_START + timedelta(minutes=slot * SLOT_MIN)
    return t.strftime("%H:%M")

from fastapi import APIRouter, HTTPException
from ..schemas.calendar import EventData
from ..services.calendar_service import insert_event


router = APIRouter()


@router.post("/calendar/add")
def add_event(event: EventData):
    try:
        event_id = insert_event(
            user_id="demo_user",
            summary=event.summary,
            description=event.description,
            start=event.start,
            end=event.end,
            tz=event.timeZone,
        )
        return {"ok": True, "event_id": event_id}
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
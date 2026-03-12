from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import Optional




USER_CREDS: dict[str, Credentials] = {}




def get_user_creds(user_id: str) -> Optional[Credentials]:
    return USER_CREDS.get(user_id)




def set_user_creds(user_id: str, creds: Credentials) -> None:
    USER_CREDS[user_id] = creds




def insert_event(user_id: str, summary: str, description: str | None, start: str, end: str, tz: str) -> str:
    creds = get_user_creds(user_id)
    if not creds:
        raise PermissionError("Google Calendar not authorized yet")


    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request as GReq
        creds.refresh(GReq())


    service = build("calendar", "v3", credentials=creds)
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start, "timeZone": tz},
        "end": {"dateTime": end, "timeZone": tz},
    }
    created = service.events().insert(calendarId="primary", body=body).execute()
    return created.get("id")
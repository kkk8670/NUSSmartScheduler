import secrets
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow
from ..core.config import settings
from ..services.calendar_service import set_user_creds


router = APIRouter()
SESSION_STORE: dict[str, dict] = {}




def build_flow(state: str | None = None):
    return Flow.from_client_secrets_file(
    settings.GOOGLE_CLIENT_SECRETS_FILE,
    scopes=settings.GOOGLE_SCOPES,
    redirect_uri=settings.OAUTH_REDIRECT_URI,
    state=state,
    )




@router.get("/auth/start")
def auth_start(_: Request):
    state = secrets.token_urlsafe(16)
    flow = build_flow(state=state)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    SESSION_STORE[state] = {"user_id": "demo_user"}
    return RedirectResponse(auth_url)




@router.get("/oauth2callback")
def oauth2callback(request: Request):
    state = request.query_params.get("state")
    if not state or state not in SESSION_STORE:
        raise HTTPException(400, "Invalid state")


    flow = build_flow()
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials


    user_id = SESSION_STORE[state]["user_id"]
    set_user_creds(user_id, creds)


    return HTMLResponse("""
    <html>
        <body>
            <h3>✅ Authorization successful</h3>
            <p>You can now POST /calendar/add to create an event.</p>
        </body>
    </html>
    """)
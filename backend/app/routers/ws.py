from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.security import COOKIE_NAME, verify_session_token
from app.services.broadcaster import broadcaster

router = APIRouter()


@router.websocket("/ws/live")
async def live_feed(ws: WebSocket):
    token = ws.cookies.get(COOKIE_NAME)
    if not token or not verify_session_token(token):
        await ws.close(code=4401)
        return
    await broadcaster.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await broadcaster.disconnect(ws)

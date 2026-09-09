from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.config import settings
from app.security import COOKIE_NAME, create_session_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    if payload.password != settings.app_password:
        raise HTTPException(status_code=401, detail="invalid_password")
    token = create_session_token()
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=7 * 24 * 3600)
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}

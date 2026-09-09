from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

COOKIE_NAME = "session"
MAX_AGE_SECONDS = 7 * 24 * 3600

_serializer = URLSafeTimedSerializer(settings.session_secret)


def create_session_token() -> str:
    return _serializer.dumps({"authenticated": True})


def verify_session_token(token: str) -> bool:
    try:
        data = _serializer.loads(token, max_age=MAX_AGE_SECONDS)
        return bool(data.get("authenticated"))
    except (BadSignature, SignatureExpired):
        return False


def require_auth(request: Request) -> None:
    token = request.cookies.get(COOKIE_NAME)
    if not token or not verify_session_token(token):
        raise HTTPException(status_code=401, detail="not_authenticated")

from fastapi import Cookie, HTTPException

from app.services.auth_service import parse_token


def require_auth(nasadmin_session: str | None = Cookie(default=None)):
    if not nasadmin_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = parse_token(nasadmin_session)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid session")
    return data

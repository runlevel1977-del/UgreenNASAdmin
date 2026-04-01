from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.routers.deps import require_auth
from app.services.auth_service import COOKIE_NAME, ensure_admin, issue_token, verify_login

router = APIRouter(tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.get("/auth/bootstrap")
def auth_bootstrap():
    data = ensure_admin()
    return {"ok": True, "admin_user": data.get("admin_user")}


@router.post("/auth/login")
def auth_login(body: LoginBody, response: Response):
    if not verify_login(body.username, body.password):
        return {"ok": False, "error": "Invalid credentials"}
    token = issue_token(body.username)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax")
    return {"ok": True}


@router.post("/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/auth/me")
def auth_me(_=Depends(require_auth)):
    return {"ok": True}

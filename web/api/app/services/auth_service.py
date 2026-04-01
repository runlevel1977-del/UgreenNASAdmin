import os
import time

from itsdangerous import BadSignature, URLSafeSerializer
from passlib.context import CryptContext

from app.services.config_store import AUTH_FILE, ensure_dirs, read_json, write_json

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeSerializer(os.environ.get("APP_SESSION_SECRET", "change-me"), salt="nasadmin-web")
COOKIE_NAME = "nasadmin_session"


def ensure_admin():
    ensure_dirs()
    data = read_json(AUTH_FILE, {})
    if data.get("admin_user") and data.get("admin_hash"):
        return data
    user = os.environ.get("APP_ADMIN_USER", "admin")
    password = os.environ.get("APP_ADMIN_PASSWORD", "admin")
    payload = {
        "admin_user": user,
        "admin_hash": pwd_ctx.hash(password),
        "created_at": int(time.time()),
    }
    write_json(AUTH_FILE, payload)
    return payload


def verify_login(username: str, password: str) -> bool:
    data = ensure_admin()
    if username != data.get("admin_user"):
        return False
    return pwd_ctx.verify(password, data.get("admin_hash", ""))


def issue_token(username: str) -> str:
    return serializer.dumps({"u": username, "iat": int(time.time())})


def parse_token(token: str):
    try:
        return serializer.loads(token)
    except BadSignature:
        return None

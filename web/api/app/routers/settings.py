from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routers.deps import require_auth
from app.services.config_store import get_settings, save_settings
from app.services.ssh_service import run_cmd

router = APIRouter(tags=["settings"])


class SettingsBody(BaseModel):
    host: str
    port: int = 22
    user: str
    password: str = ""
    ssh_use_key: bool = False
    ssh_key_path: str = ""
    ssh_key_passphrase: str = ""


@router.get("/settings")
def read_settings(_=Depends(require_auth)):
    s = get_settings()
    return {"ok": True, "settings": s}


@router.post("/settings")
def write_settings(body: SettingsBody, _=Depends(require_auth)):
    saved = save_settings(body.model_dump())
    return {"ok": True, "settings": saved}


@router.post("/settings/test")
def test_connection(_=Depends(require_auth)):
    out = run_cmd("hostname && uptime", use_sudo=False)
    ok = "Fehler bei SSH-Verbindung" not in out
    return {"ok": ok, "output": out}

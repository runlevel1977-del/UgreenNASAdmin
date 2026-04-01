import shlex

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routers.deps import require_auth
from app.services.ssh_service import run_cmd

router = APIRouter(tags=["acl"])


class AclPath(BaseModel):
    path: str


class AclChmod(BaseModel):
    path: str
    mode: str


class AclChown(BaseModel):
    path: str
    owner_group: str


@router.post("/acl/stat")
def acl_stat(body: AclPath, _=Depends(require_auth)):
    p = shlex.quote(body.path.strip())
    out = run_cmd(f"stat -c 'Modus: %a Besitzer: %U:%G Größe: %s' {p} 2>&1; ls -ldn {p} 2>&1", True)
    return {"ok": True, "output": out}


@router.post("/acl/chmod")
def acl_chmod(body: AclChmod, _=Depends(require_auth)):
    out = run_cmd(f"chmod {body.mode} {shlex.quote(body.path.strip())}", True)
    return {"ok": True, "output": out}


@router.post("/acl/chown")
def acl_chown(body: AclChown, _=Depends(require_auth)):
    out = run_cmd(f"chown {body.owner_group} {shlex.quote(body.path.strip())}", True)
    return {"ok": True, "output": out}

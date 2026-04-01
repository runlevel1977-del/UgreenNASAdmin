import shlex

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routers.deps import require_auth
from app.services.ssh_service import run_cmd

router = APIRouter(tags=["snapshots"])


class SnapBase(BaseModel):
    base: str = "/volume1"


class SnapCreate(BaseModel):
    src: str
    dst: str


class SnapDelete(BaseModel):
    target: str


@router.post("/snapshots/list")
def snap_list(body: SnapBase, _=Depends(require_auth)):
    base = shlex.quote((body.base or "/volume1").strip())
    out = run_cmd(f"btrfs subvolume list -p {base} 2>/dev/null || btrfs subvolume list {base} 2>/dev/null", True)
    return {"ok": True, "output": out}


@router.post("/snapshots/create")
def snap_create(body: SnapCreate, _=Depends(require_auth)):
    src = shlex.quote(body.src.strip())
    dst = shlex.quote(body.dst.strip())
    out = run_cmd(f"mkdir -p $(dirname {dst}) 2>/dev/null; btrfs subvolume snapshot {src} {dst}", True)
    return {"ok": True, "output": out}


@router.post("/snapshots/delete")
def snap_delete(body: SnapDelete, _=Depends(require_auth)):
    out = run_cmd(f"btrfs subvolume delete {shlex.quote(body.target.strip())}", True)
    return {"ok": True, "output": out}

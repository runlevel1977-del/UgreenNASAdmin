from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routers.deps import require_auth
from app.services.ssh_service import run_cmd

router = APIRouter(tags=["docker"])


class DockerAction(BaseModel):
    name: str


@router.get("/docker/list")
def docker_list(_=Depends(require_auth)):
    out = run_cmd("docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}'", True)
    rows = []
    for ln in out.splitlines():
        if "|" not in ln:
            continue
        name, status, image = ln.split("|", 2)
        rows.append({"name": name.strip(), "status": status.strip(), "image": image.strip()})
    return {"ok": True, "containers": rows, "raw": out}


@router.post("/docker/start")
def docker_start(body: DockerAction, _=Depends(require_auth)):
    out = run_cmd(f"docker start {body.name}", True)
    return {"ok": True, "output": out}


@router.post("/docker/stop")
def docker_stop(body: DockerAction, _=Depends(require_auth)):
    out = run_cmd(f"docker stop {body.name}", True)
    return {"ok": True, "output": out}


@router.get("/docker/logs/{name}")
def docker_logs(name: str, _=Depends(require_auth)):
    out = run_cmd(f"docker logs --tail 200 {name}", True)
    return {"ok": True, "output": out}

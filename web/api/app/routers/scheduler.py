import shlex

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routers.deps import require_auth
from app.services.ssh_service import run_cmd, write_remote

router = APIRouter(tags=["scheduler"])

CRON_PATH = "/etc/cron.d/papa_jobs"


class CronBody(BaseModel):
    content: str


@router.get("/scheduler/read")
def scheduler_read(_=Depends(require_auth)):
    out = run_cmd(f"cat {shlex.quote(CRON_PATH)}", True)
    return {"ok": True, "content": out}


@router.post("/scheduler/save")
def scheduler_save(body: CronBody, _=Depends(require_auth)):
    ok, err = write_remote(CRON_PATH, body.content, use_sudo=True)
    return {"ok": ok, "error": err}

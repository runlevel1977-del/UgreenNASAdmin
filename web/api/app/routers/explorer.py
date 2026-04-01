import shlex

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.routers.deps import require_auth
from app.services.ssh_service import connect_client, run_cmd

router = APIRouter(tags=["explorer"])


class PathBody(BaseModel):
    path: str


class CopyBody(BaseModel):
    src: str
    dst: str


@router.post("/explorer/list")
def explorer_list(body: PathBody, _=Depends(require_auth)):
    p = body.path.strip() or "/volume1"
    out = run_cmd(f"LC_ALL=C ls -lnAp {shlex.quote(p)}", False)
    return {"ok": True, "path": p, "output": out}


@router.post("/explorer/delete")
def explorer_delete(body: PathBody, _=Depends(require_auth)):
    out = run_cmd(f"rm -rf {shlex.quote(body.path.strip())}", True)
    return {"ok": True, "output": out}


@router.post("/explorer/copy")
def explorer_copy(body: CopyBody, _=Depends(require_auth)):
    out = run_cmd(f"cp -a {shlex.quote(body.src.strip())} {shlex.quote(body.dst.strip())}", True)
    return {"ok": True, "output": out}


@router.post("/explorer/upload")
def explorer_upload(path: str, file: UploadFile = File(...), _=Depends(require_auth)):
    remote_path = path.strip()
    if not remote_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Remote path must be absolute")
    ssh = connect_client()
    try:
        sftp = ssh.open_sftp()
        try:
            with sftp.file(remote_path, "wb") as f:
                f.write(file.file.read())
        finally:
            sftp.close()
    finally:
        ssh.close()
    return {"ok": True, "path": remote_path, "name": file.filename}


@router.get("/explorer/download")
def explorer_download(path: str, _=Depends(require_auth)):
    remote_path = path.strip()
    if not remote_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Remote path must be absolute")
    ssh = connect_client()
    try:
        sftp = ssh.open_sftp()
        try:
            with sftp.file(remote_path, "rb") as f:
                data = f.read()
        finally:
            sftp.close()
    finally:
        ssh.close()
    filename = remote_path.split("/")[-1] or "download.bin"
    return StreamingResponse(
        iter([data]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

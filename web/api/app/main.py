from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import acl, auth, docker, explorer, health, scheduler, settings, snapshots

app = FastAPI(title="NAS Admin Web API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(docker.router, prefix="/api")
app.include_router(explorer.router, prefix="/api")
app.include_router(scheduler.router, prefix="/api")
app.include_router(acl.router, prefix="/api")
app.include_router(snapshots.router, prefix="/api")


@app.get("/api/healthz")
def healthz():
    return {"ok": True}

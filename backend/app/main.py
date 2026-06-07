from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.api.routes import pipelines, runs
from app.api.ws_design import ws_design_handler
from app.api.ws_run import ws_run_handler
from app.api.ws_extend import ws_extend_handler
from app.db import Base, engine
from app.gcs_backup import restore_from_gcs
import os

import app.models.pipeline  # noqa: F401
import app.models.run  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    restore_from_gcs()          # download DB from GCS before creating tables
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="AgentMaster",
    version="2.0.0",
    description="Autonomous Agentic Graph Framework — Design pipelines at design time, execute at run time.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipelines.router)
app.include_router(runs.router)


@app.websocket("/ws/design/{pipeline_id}")
async def ws_design(ws: WebSocket, pipeline_id: str):
    await ws_design_handler(ws, pipeline_id)


@app.websocket("/ws/extend/{pipeline_id}")
async def ws_extend(ws: WebSocket, pipeline_id: str):
    await ws_extend_handler(ws, pipeline_id)


@app.websocket("/ws/run/{run_id}")
async def ws_run(ws: WebSocket, run_id: str):
    await ws_run_handler(ws, run_id)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "version": "2.0.0"}


# Serve built frontend (production) — must be last
_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static_dir):
    _assets_dir = os.path.join(_static_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(os.path.join(_static_dir, "index.html"))

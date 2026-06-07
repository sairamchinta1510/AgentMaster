from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import pipelines, runs
from app.api.ws_design import ws_design_handler
from app.api.ws_run import ws_run_handler
from app.db import Base, engine

import app.models.pipeline  # noqa: F401
import app.models.run  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(
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


@app.websocket("/ws/run/{run_id}")
async def ws_run(ws: WebSocket, run_id: str):
    await ws_run_handler(ws, run_id)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "version": "2.0.0"}

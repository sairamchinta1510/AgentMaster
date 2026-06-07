from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import sessions, library, agents
from app.api.websocket import websocket_endpoint
from app.db import Base, engine

# Create all ORM tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AgentMaster",
    version="1.0.0",
    description="Autonomous Agentic Graph Framework — AI-powered multi-agent DAG orchestration",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(library.router)
app.include_router(agents.router)


@app.websocket("/ws/{session_id}")
async def ws_handler(ws: WebSocket, session_id: str):
    await websocket_endpoint(ws, session_id)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "version": "1.0.0"}

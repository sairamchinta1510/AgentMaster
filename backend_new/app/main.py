from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.utils import setup_logging
from app.api.routes import health, executions, agents
from app.api.websockets import studio, control_room

# Setup logging
setup_logging()

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="AgentMaster API",
    description="Recursive Multi-Agent Orchestrator",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(health.router, tags=["Health"])
app.include_router(executions.router, tags=["Executions"])
app.include_router(agents.router, tags=["Agents"])

# Include WebSocket routes
app.include_router(studio.router, tags=["WebSocket - Studio"])
app.include_router(control_room.router, tags=["WebSocket - Control Room"])


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "AgentMaster",
        "version": "1.0.0",
        "docs": "/docs"
    }

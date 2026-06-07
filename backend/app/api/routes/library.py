from fastapi import APIRouter, HTTPException
from app.library.agent_library import AgentLibrary

router = APIRouter(prefix="/api/library", tags=["library"])
_library = AgentLibrary()


@router.get("")
def list_library():
    return _library.list_all()


@router.get("/search")
def search_library(q: str):
    return _library.search(q)


@router.get("/{pattern_id}")
def get_pattern(pattern_id: str):
    p = _library.get_by_id(pattern_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return p

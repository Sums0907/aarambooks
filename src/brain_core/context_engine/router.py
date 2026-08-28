from fastapi import APIRouter, Depends
from src.brain_core.context_engine.assembler import ContextAssembler

router = APIRouter(prefix="/api/v1/context", tags=["Context Engine"])

def get_context_assembler() -> ContextAssembler:
    # Dependency will be overridden in main.py if needed
    raise NotImplementedError("Dependency not wired")

# Active Stage F endpoints (e.g. generic /resolve) would go here in the future.
# The legacy /assemble endpoint has been removed.

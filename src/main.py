from fastapi import FastAPI
from src.shared.config import settings
from src.brain_core.context_engine.router import router as context_router

app = FastAPI(
    title="AaramBooks Brain Core API",
    description="Intelligence foundation and orchestrator for AaramBooks.",
    version="0.1.0",
)

app.include_router(context_router)

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok", 
        "service": "aarambooks-brain-api", 
        "environment": settings.environment
    }

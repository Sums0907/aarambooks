from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .routers import ndr, system, orders, customers, events
from .routers.ndr_queue import router as ndr_queue_router, intelligence_router, engagement_router
from shopdeck import config

app = FastAPI(
    title="ShopDeck Business System API",
    description="Canonical Sovereign API for the ShopDeck operational domain.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include canonical routers
app.include_router(system.router)
app.include_router(ndr.router)
app.include_router(orders.router)
app.include_router(customers.router)
app.include_router(events.router)
app.include_router(ndr_queue_router)
app.include_router(intelligence_router)
app.include_router(engagement_router)

@app.on_event("shutdown")
async def shutdown_event():
    from .dependencies import _pool
    if _pool:
        await _pool.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

"""
Catalog Business System - HTTP boundary.

Wraps CatalogService (service.py) as a real HTTP service, the same shape ShopDeck BS and
Inventory already use for their integration with Brain. Before this file existed, Brain
imported CatalogService and its Pydantic models directly as Python code
(src/infrastructure/adapters/catalog_cem_adapter.py, src/main.py,
src/application/catalog_translator.py) and constructed its own asyncpg pool against
whatever database_url it was handed - which in practice was Brain's own database, not
CATALOG_DATABASE_URL (see config.py), so Catalog's real data ended up living inside Brain's
database by accident. This file is the fix: Catalog now owns its own database connection
end-to-end, and Brain reaches it only over HTTP.

Every request (except /health) must carry the shared internal secret in the
Authorization: Bearer <CATALOG_INTERNAL_TOKEN> header - this is an internal, same-network
service (Brain and Catalog only), not a public API, so a shared secret is proportionate here
rather than the full Aaram Identity M2M flow ShopDeck/Inventory use for their public-facing
boundaries.
"""
import os
from typing import Optional
from uuid import UUID

import asyncpg
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import CATALOG_DATABASE_URL
from .service import CatalogService
from .models import (
    SaveProductFamilyPayload,
    TransitionLifecycleStatePayload,
    MutationResponse,
)

CATALOG_INTERNAL_TOKEN = os.environ.get("CATALOG_INTERNAL_TOKEN", "")

app = FastAPI(title="Catalog Business System")

_pool: Optional[asyncpg.Pool] = None
_service: Optional[CatalogService] = None


@app.on_event("startup")
async def startup():
    global _pool, _service
    _pool = await asyncpg.create_pool(CATALOG_DATABASE_URL, min_size=1, max_size=10)
    _service = CatalogService(_pool)


@app.on_event("shutdown")
async def shutdown():
    if _pool:
        await _pool.close()


def _verify_token(authorization: str = Header(default="")):
    if not CATALOG_INTERNAL_TOKEN:
        raise HTTPException(status_code=500, detail="CATALOG_INTERNAL_TOKEN not configured on server")
    expected = f"Bearer {CATALOG_INTERNAL_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing internal token")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "catalog-bs"}


class ProductCodeVerifyRequest(BaseModel):
    product_code: str


@app.post("/internal/verify/product-code")
async def verify_product_code(body: ProductCodeVerifyRequest, authorization: str = Header(default="")):
    _verify_token(authorization)
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT internal_id as product_internal_id, product_code, lifecycle_state
               FROM catalog_products
               WHERE product_code = $1
               LIMIT 1""",
            body.product_code,
        )
    if row is None:
        return {"exists": False, "product_code": body.product_code, "lifecycle_state": None}
    return {
        "exists": True,
        "active": row["lifecycle_state"] not in ("RETIRED",),
        "product_code": body.product_code,
        "lifecycle_state": row["lifecycle_state"],
        "product_internal_id": str(row["product_internal_id"]),
    }


class FamilyExistenceRequest(BaseModel):
    parent_internal_id: str


@app.post("/internal/verify/family-existence")
async def verify_family_existence(body: FamilyExistenceRequest, authorization: str = Header(default="")):
    _verify_token(authorization)
    try:
        uid = UUID(body.parent_internal_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="parent_internal_id is not a valid UUID")
    async with _pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM vw_catalog_products WHERE product_internal_id = $1)",
            uid,
        )
    return {"exists": exists, "parent_internal_id": str(uid)}


@app.get("/internal/search/product-by-code")
async def search_product_by_code(product_code: str, authorization: str = Header(default="")):
    _verify_token(authorization)
    async with _pool.acquire() as conn:
        records = await conn.fetch(
            "SELECT product_internal_id, product_name FROM vw_catalog_products WHERE product_code = $1",
            product_code,
        )
    return {
        "count": len(records),
        "results": [
            {"internal_id": str(r["product_internal_id"]), "name": r["product_name"]}
            for r in records
        ],
    }


@app.post("/internal/products/save-family", response_model=MutationResponse)
async def save_family(payload: SaveProductFamilyPayload, authorization: str = Header(default="")):
    _verify_token(authorization)
    return await _service.save_product_family(payload)


@app.post("/internal/products/transition", response_model=MutationResponse)
async def transition(payload: TransitionLifecycleStatePayload, authorization: str = Header(default="")):
    _verify_token(authorization)
    return await _service.transition_lifecycle_state(payload)


@app.post("/internal/publications/{channel}", response_model=MutationResponse)
async def publish(channel: str, authorization: str = Header(default="")):
    _verify_token(authorization)
    return await _service.generate_channel_publication_artifact(channel)


@app.get("/internal/artifacts/{artifact_id}")
async def download_artifact(artifact_id: UUID, authorization: str = Header(default="")):
    _verify_token(authorization)
    file_path = await _service.get_publication_artifact_path(artifact_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Artifact not found or not committed")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Artifact file missing from disk")
    return FileResponse(file_path, filename=os.path.basename(file_path))

import os
from typing import AsyncGenerator
import asyncpg
from fastapi import Depends, HTTPException, status, Security
from .auth import get_current_user
from .repositories.ndr import NDRRepository
from .services.ndr import NDRService

# Use explicit target DB, never Brain
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is strictly required for the API.")

DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

# Global pool
_pool = None

async def get_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return _pool

async def get_ndr_repository(pool: asyncpg.Pool = Depends(get_db_pool)) -> NDRRepository:
    return NDRRepository(pool)

async def get_ndr_service(repository: NDRRepository = Depends(get_ndr_repository)) -> NDRService:
    return NDRService(repository)



import asyncio
import os
os.environ["DATABASE_URL_SYNC"] = "postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod"

import sys
import json
from src.main import rabta_orch, text_to_sql_engine
from src.shared.evidence_request_contracts import BusinessRealityStatus
import httpx
from fastapi.testclient import TestClient
from business_systems.shopdeck.api.main import app

def run_api():
    client = TestClient(app)
    
    awb_history = "142285158114035"
    print("=== API CERTIFICATION ===")
    
    # Test AWB with NDR history
    response = client.get(
        f"/api/v1/shipments/{awb_history}/ndr",
        headers={"Authorization": "Bearer mock-m2m-token-for-dev"}
    )
    print("STATUS (WITH HISTORY):", response.status_code)
    
    # Test unknown AWB
    response_unknown = client.get(
        "/api/v1/shipments/UNKNOWN_AWB_123/ndr",
        headers={"Authorization": "Bearer mock-m2m-token-for-dev"}
    )
    print("UNKNOWN AWB STATUS:", response_unknown.status_code)

async def run_cem():
    print("\n=== CEM CERTIFICATION ===")
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app)
    
    class PatchedAsyncClient(AsyncClient):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            kwargs["base_url"] = "http://localhost:8000"
            super().__init__(**kwargs)
            
    original_client = httpx.AsyncClient
    httpx.AsyncClient = PatchedAsyncClient

    try:
        response = await rabta_orch.process_query(
            query="Where is AWB 142285158114035?",
            id_urn="urn:aarambooks:intelligence:ndr",
            cem_urn="urn:aarambooks:cem:ndr",
            auth_context="mock-m2m-token-for-dev"
        )
        print("RABTA RESPONSE MSG:", response.message)
    finally:
        httpx.AsyncClient = original_client

run_api()
asyncio.run(run_cem())

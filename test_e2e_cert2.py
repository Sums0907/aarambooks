import asyncio
import os
os.environ["DATABASE_URL_SYNC"] = "postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod"

import sys
import json
import subprocess
import time
from src.main import rabta_orch, text_to_sql_engine
from src.shared.evidence_request_contracts import BusinessRealityStatus
import httpx

# Start the uvicorn server in a subprocess
server = subprocess.Popen(
    ["python3", "-m", "uvicorn", "business_systems.shopdeck.api.main:app", "--port", "8008"],
    env=os.environ
)

# wait for it to boot
time.sleep(2)

async def run_api():
    async with httpx.AsyncClient(base_url="http://localhost:8008") as client:
        awb_history = "142285158114035"
        print("=== API CERTIFICATION ===")
        
        response = await client.get(
            f"/api/v1/shipments/{awb_history}/ndr",
            headers={"Authorization": "Bearer mock-m2m-token-for-dev"}
        )
        print("STATUS (WITH HISTORY):", response.status_code)
        if response.status_code == 200:
            print("BODY:", json.dumps(response.json(), indent=2))
        
        response_unknown = await client.get(
            "/api/v1/shipments/UNKNOWN_AWB_123/ndr",
            headers={"Authorization": "Bearer mock-m2m-token-for-dev"}
        )
        print("UNKNOWN AWB STATUS:", response_unknown.status_code)

async def run_cem():
    print("\n=== CEM CERTIFICATION ===")
    
    class PatchedAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs["base_url"] = "http://localhost:8008"
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

async def main():
    try:
        await run_api()
        await run_cem()
    finally:
        server.terminate()

asyncio.run(main())

import asyncio
from fastapi.testclient import TestClient
import sys
sys.path.append("/Users/sumatidhingra/Documents/AaramBooks/business_systems/shopdeck")
from api.main import app

client = TestClient(app)

def run():
    awb = "142285158114035" # Has NDR Action log
    response = client.get(
        f"/api/v1/shipments/{awb}/ndr",
        headers={"Authorization": "Bearer MOCK_TOKEN"}
    )
    print("STATUS:", response.status_code)
    import json
    print("BODY:", json.dumps(response.json(), indent=2))

run()

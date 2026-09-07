import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import os
import sys

# Add shopdeck root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from api.main import app
from api.dependencies import get_ndr_repository
from api.repositories.ndr import NDRRepository
from api.schemas.ndr import NDRShipmentContext

from api.auth import get_current_user

class MockNDRRepository(NDRRepository):
    def __init__(self):
        pass

    async def check_awb_exists(self, awb_no: str) -> bool:
        return awb_no == "AWB_VALID"

    async def get_shipment_ndr_report(self, awb_no: str):
        if awb_no == "AWB_VALID":
            return {
                "awb_no": "AWB_VALID",
                "order_status": "rto_initiated",
                "courier_partner": "Delhivery",
                "customer_id": "CUST_123",
                "customer_name": "Test User",
                "payment_mode": "cod",
                "pickup_time": datetime(2023, 1, 1),
                "latest_ndr_time": datetime(2023, 1, 2),
                "latest_ndr_reason": "Customer not available",
                "latest_ofd_time": datetime(2023, 1, 2),
                "delivery_time": None,
                "ndr_count": 1,
                "ofd_count": 1,
                "seller_actions": None,
                "ndr_status": "action_required"
            }
        return None

    async def get_ndr_action_history(self, awb_no: str):
        if awb_no == "AWB_VALID":
            return [
                {
                    "action_type": "ivr_call",
                    "action_by": "SYSTEM",
                    "action_time": datetime(2023, 1, 2, 10, 0, 0),
                    "response_status": "no_answer",
                    "response_time": None,
                    "remarks": None,
                    "message_text": None,
                    "reattempt_date": None,
                    "is_priority_escalate": False,
                    "call_duration": "10s"
                }
            ]
        return []

@pytest.fixture(autouse=True)
def override_dependencies():
    app.dependency_overrides[get_ndr_repository] = lambda: MockNDRRepository()
    app.dependency_overrides[get_current_user] = lambda: {"permissions": ["SHOPDECK_VIEW"], "aud": "AARAM_ECOSYSTEM"}
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

def test_authentication_boundary():
    # Authentication boundary is tested in test_auth.py now
    pass

def test_valid_awb_request():
    # 2, 4, 5. Valid AWB, correct aggregation, schema validation
    response = client.get(
        "/api/v1/ndr/AWB_VALID", 
        headers={"Authorization": "Bearer mock-m2m-token-for-dev"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["awb_no"] == "AWB_VALID"
    assert data["ndr_count"] == 1
    assert len(data["action_history"]) == 1
    assert data["action_history"][0]["action_type"] == "ivr_call"

def test_unknown_awb_behavior():
    # 3. Unknown AWB
    response = client.get(
        "/api/v1/ndr/AWB_UNKNOWN", 
        headers={"Authorization": "Bearer mock-m2m-token-for-dev"}
    )
    assert response.status_code == 404
    assert "No NDR records found" in response.json()["detail"]

def test_health_endpoint():
    # 10. Health endpoint works when Brain is unavailable (No auth needed)
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    assert "status" in response.json()

def test_sync_status_endpoint():
    response = client.get(
        "/api/v1/sync/health", 
        headers={"Authorization": "Bearer mock-m2m-token-for-dev"}
    )
    assert response.status_code == 200
    assert "checkpoints" in response.json()

def test_architectural_sovereignty():
    # 6, 7, 8, 9. Verify no Brain imports exist in the API layer
    import ast
    import glob
    
    api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../api'))
    python_files = glob.glob(f"{api_dir}/**/*.py", recursive=True)
    
    for filepath in python_files:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read(), filename=filepath)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        assert not name.name.startswith("src."), f"Sovereignty violation: {filepath} imports Brain module {name.name}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert not node.module.startswith("src."), f"Sovereignty violation: {filepath} imports Brain module {node.module}"

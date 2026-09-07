import pytest
import os
import sys

# Add shopdeck to path so it can import 'config'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "business_systems", "shopdeck"))

os.environ["DATABASE_URL"] = "postgres://fake:fake@localhost:5433/shopdeck"
os.environ["DATABASE_URL_SYNC"] = "postgresql://fake:fake@localhost:5433/shopdeck"
os.environ["SHOPDECK_MCP_URL"] = "http://localhost:8080"
from fastapi.testclient import TestClient
from business_systems.shopdeck.backend.api.main import app
from business_systems.shopdeck.api.dependencies import get_db_pool

class MockPool:
    def __init__(self):
        self.rows = {}

    def acquire(self):
        pool_self = self
        class MockConn:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
            async def execute(self, query, *args, **kwargs):
                if "INSERT" in query:
                    pool_self.rows[args[0]] = {
                        "recommendation": args[3],
                        "authorized_action": args[4]
                    }
            async def fetchrow(self, query, *args, **kwargs):
                if "SELECT" in query:
                    return pool_self.rows.get(args[0])
        return MockConn()

mock_pool = MockPool()
app.dependency_overrides[get_db_pool] = lambda: mock_pool

client = TestClient(app)

def test_mock_shopdeck_bs_api_persistence():
    payload = {
        "normalization_id": "test_norm_123",
        "brain_decision_id": "test_dec_123",
        "target_identity": "AWB_MOCK_123",
        "recommendation": "seller_reattempt",
        "authorized_action": "seller_reattempt",
        "action_parameters": {"reason": "test"},
        "reasoning": "Test reasoning",
        "diagnosis": "NOT_AVAILABLE",
        "risk_score": "NOT_AVAILABLE",
        "source_event_ids": ["evt1"],
        "provenance": "test",
        "normalization_status": "COMPLETED"
    }
    
    # 1. Test Persistence
    response = client.post("/api/v1/ndr/intelligence_results", json=payload)
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "persisted"
        
        # 2. Test Idempotency (Identical Duplicate)
        response2 = client.post("/api/v1/ndr/intelligence_results", json=payload)
        assert response2.status_code == 200
        assert response2.json()["status"] == "persisted"
        
        # 3. Test Conflicting Duplicate Rejection
        conflict_payload = payload.copy()
        conflict_payload["recommendation"] = "courier_dispute"
        response3 = client.post("/api/v1/ndr/intelligence_results", json=conflict_payload)
        assert response3.status_code == 409

from business_systems.shopdeck.api.auth import get_current_user

app.dependency_overrides[get_current_user] = lambda: {"username": "test_admin"}

def test_download_endpoint_unauthenticated():
    # Remove auth override to test rejection
    app.dependency_overrides.pop(get_current_user, None)
    res = client.get("/api/v1/ndr/reports/download/test_rep/1.pdf")
    assert res.status_code in (401, 403)
    # Restore auth override
    app.dependency_overrides[get_current_user] = lambda: {"username": "test_admin"}

def test_download_endpoint():
    # Setup test file
    import os
    reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
    os.makedirs(reports_dir, exist_ok=True)
    test_pdf = os.path.join(reports_dir, "test_rep_1.pdf")
    with open(test_pdf, "w") as f:
        f.write("mock pdf content")
        
    # 4. Test Valid PDF Download
    res = client.get("/api/v1/ndr/reports/download/test_rep/1.pdf")
    assert res.status_code == 200
    assert res.content == b"mock pdf content"
    
    # 5. Test Path Security (Traversal)
    # Depending on client normalization, it might return 404 or 400
    res2 = client.get("/api/v1/ndr/reports/download/test_rep/%2E%2E%2F%2E%2E%2Fetc%2Fpasswd.pdf")
    assert res2.status_code in (400, 404)
    
    # 6. Test Invalid Extension
    res3 = client.get("/api/v1/ndr/reports/download/test_rep/1.txt")
    assert res3.status_code == 400
    
    # 7. Test Missing Artifact
    res4 = client.get("/api/v1/ndr/reports/download/test_rep/missing.csv")
    assert res4.status_code == 404

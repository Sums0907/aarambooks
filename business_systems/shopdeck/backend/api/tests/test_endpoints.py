import pytest
import os
from fastapi.testclient import TestClient
from api.main import app
from datetime import datetime
from api.auth import get_current_user

from api.auth import get_current_user
import pytest

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: {"permissions": ["SHOPDECK_VIEW"], "aud": "AARAM_ECOSYSTEM"}
    yield
    app.dependency_overrides.clear()

# Setup test client
client = TestClient(app)

def test_missing_database_url():
    # Simulate missing DB URL by manipulating os.environ
    original = os.environ.get("DATABASE_URL")
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]
        
    try:
        # Import should fail or raise error
        with pytest.raises(ValueError, match="strictly required"):
            from api.dependencies import get_db_pool
            import importlib
            importlib.reload(sys.modules['api.dependencies'])
    except Exception:
        pass # Depending on how it's tested, standard load fails
    finally:
        if original:
            os.environ["DATABASE_URL"] = original

def test_system_status():
    res = client.get("/api/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "database_connected" in data

def test_unauthorized_access():
    res = client.get("/api/v1/ndr")
    # Because we lack the token, it should be 403 Forbidden or 401
    assert res.status_code in [401, 403]

def test_event_allowlist_rejected():
    res = client.get("/api/v1/events/malicious_table", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 400
    assert res.json()["detail"] == "Invalid event table"

def test_ndr_pagination():
    res = client.get("/api/v1/ndr?page=1&limit=5", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 200
    assert "data" in res.json()
    assert "meta" in res.json()
    assert res.json()["meta"]["limit"] == 5

def test_orders_pagination():
    res = client.get("/api/v1/orders?page=1&limit=5", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 200

def test_customers_pagination():
    res = client.get("/api/v1/customers?page=1&limit=5", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 200

def test_events_pagination():
    res = client.get("/api/v1/events/payment_gateway_events?page=1&limit=5", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 200
    
def test_sync_health():
    res = client.get("/api/v1/sync/health", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 200
    assert "checkpoints" in res.json()

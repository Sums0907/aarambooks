import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.event_bus.router import get_inbound_receiver
from src.event_bus.receiver import InboundReceiver
from src.shared.config import settings

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import jwt
from datetime import datetime, timedelta
import uuid

# Generate a synthetic RSA key pair for testing
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()
pem_private = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
pem_public = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

@pytest.fixture(autouse=True)
def setup_test_environment():
    settings.identity_public_key = pem_public.decode('utf-8')

class MockReceiver:
    def __init__(self):
        self.called = False
    async def process_raw_payload(self, raw_payload: str):
        self.called = True
        return '{"action_dispatched": true}'

@pytest.fixture
def client():
    mock_receiver = MockReceiver()
    app.dependency_overrides[get_inbound_receiver] = lambda: mock_receiver
    yield TestClient(app), mock_receiver
    app.dependency_overrides.clear()

def test_internal_route_missing_auth(client):
    test_client, mock_receiver = client
    response = test_client.post("/api/v1/webhooks/inbound/internal", data="{}")
    assert response.status_code == 401
    assert mock_receiver.called == False

def test_internal_route_valid_auth(client):
    test_client, mock_receiver = client
    payload = {
        "sub": "sa:aaram_brain",
        "type": "service",
        "roles": ["AARAM_BRAIN_CORE"],
        "applications": ["AARAM_BRAIN_APP"],
        "permissions": [
            "INVENTORY_CATALOG_VIEW",
            "INVENTORY_PRODUCT_VIEW",
            "INVENTORY_EXCEPTION_VIEW",
            "INVENTORY_ACTIVITY_VIEW",
            "INVENTORY_JOBWORK_VIEW"
        ],
        "aud": "AARAM_ECOSYSTEM",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "jti": uuid.uuid4().hex
    }
    token = jwt.encode(payload, pem_private, algorithm="RS256")
    
    response = test_client.post(
        "/api/v1/webhooks/inbound/internal", 
        data='{"event_type": "ndr_update", "content": {}}',
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ACKNOWLEDGED"
    assert mock_receiver.called == True

def test_shiprocket_route_blocked(client):
    test_client, mock_receiver = client
    response = test_client.post("/api/v1/webhooks/inbound/shiprocket", data="{}")
    assert response.status_code == 501
    assert mock_receiver.called == False

def test_shopdeck_route_blocked(client):
    test_client, mock_receiver = client
    response = test_client.post("/api/v1/webhooks/inbound/shopdeck", data="{}")
    assert response.status_code == 501
    assert mock_receiver.called == False

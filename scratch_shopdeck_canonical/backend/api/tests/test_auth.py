import pytest
import jwt
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from api.main import app
import api.auth

# Generate a mock RSA keypair for testing
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_identity_public_key():
    with patch("api.auth.get_public_key", return_value=public_pem):
        yield

def generate_token(permissions=None, audience="AARAM_ECOSYSTEM", expired=False):
    if permissions is None:
        permissions = ["SHOPDECK_VIEW"]
    
    now = datetime.utcnow()
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    
    payload = {
        "sub": "test_user",
        "permissions": permissions,
        "aud": audience,
        "exp": exp,
        "iat": now
    }
    
    return jwt.encode(payload, private_key, algorithm="RS256")

def test_missing_token():
    response = client.get("/api/v1/sync/health")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

def test_malformed_token():
    response = client.get("/api/v1/sync/health", headers={"Authorization": "Bearer malformed.token.here"})
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]

def test_valid_token_with_permission():
    token = generate_token(permissions=["SHOPDECK_VIEW"])
    response = client.get("/api/v1/sync/health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_valid_token_without_permission():
    token = generate_token(permissions=["OTHER_PERMISSION"])
    response = client.get("/api/v1/sync/health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert "Missing SHOPDECK_VIEW" in response.json()["detail"]

def test_wrong_audience():
    token = generate_token(audience="WRONG_AUDIENCE")
    response = client.get("/api/v1/sync/health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]

def test_expired_token():
    token = generate_token(expired=True)
    response = client.get("/api/v1/sync/health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]

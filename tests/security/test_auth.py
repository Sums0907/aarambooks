import pytest
from fastapi import Request, HTTPException
import jwt
from datetime import datetime, timedelta
import uuid

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from src.security.auth import verify_m2m_token
from src.shared.config import settings

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
def mock_settings():
    settings.identity_public_key = pem_public.decode('utf-8')

class MockRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}

def test_missing_auth_header():
    request = MockRequest()
    with pytest.raises(HTTPException) as exc:
        verify_m2m_token(request)
    assert exc.value.status_code == 401
    assert "Missing Authorization header" in exc.value.detail

def test_malformed_auth_header():
    request = MockRequest(headers={"Authorization": "NotBearer token"})
    with pytest.raises(HTTPException) as exc:
        verify_m2m_token(request)
    assert exc.value.status_code == 401
    assert "Invalid Authorization header format" in exc.value.detail

def test_valid_token_without_brain_invoke():
    payload = {
        "sub": "sa:aaram_brain",
        "type": "service",
        "permissions": [],
        "aud": "AARAM_ECOSYSTEM",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "jti": uuid.uuid4().hex
    }
    token = jwt.encode(payload, pem_private, algorithm="RS256")
    request = MockRequest(headers={"Authorization": f"Bearer {token}"})
    
    claims = verify_m2m_token(request)
    assert claims["sub"] == "sa:aaram_brain"

def test_valid_token_with_brain_core_role():
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
    request = MockRequest(headers={"Authorization": f"Bearer {token}"})
    
    claims = verify_m2m_token(request)
    assert claims["sub"] == "sa:aaram_brain"
    assert "AARAM_BRAIN_CORE" in claims["roles"]
    assert "INVENTORY_CATALOG_VIEW" in claims["permissions"]

def test_expired_token():
    payload = {
        "sub": "sa:aaram_brain",
        "type": "service",
        "aud": "AARAM_ECOSYSTEM",
        "exp": datetime.utcnow() - timedelta(hours=1),
        "jti": uuid.uuid4().hex
    }
    token = jwt.encode(payload, pem_private, algorithm="RS256")
    request = MockRequest(headers={"Authorization": f"Bearer {token}"})
    
    with pytest.raises(HTTPException) as exc:
        verify_m2m_token(request)
    assert exc.value.status_code == 401
    assert "Token expired" in exc.value.detail

def test_wrong_audience():
    payload = {
        "sub": "sa:aaram_brain",
        "type": "service",
        "aud": "OTHER_ECOSYSTEM",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "jti": uuid.uuid4().hex
    }
    token = jwt.encode(payload, pem_private, algorithm="RS256")
    request = MockRequest(headers={"Authorization": f"Bearer {token}"})
    
    with pytest.raises(HTTPException) as exc:
        verify_m2m_token(request)
    assert exc.value.status_code == 401
    assert "Invalid audience" in exc.value.detail

def test_wrong_type():
    payload = {
        "sub": "user:123",
        "type": "human",
        "aud": "AARAM_ECOSYSTEM",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "jti": uuid.uuid4().hex
    }
    token = jwt.encode(payload, pem_private, algorithm="RS256")
    request = MockRequest(headers={"Authorization": f"Bearer {token}"})
    
    with pytest.raises(HTTPException) as exc:
        verify_m2m_token(request)
    assert exc.value.status_code == 403
    assert "Only M2M service tokens" in exc.value.detail


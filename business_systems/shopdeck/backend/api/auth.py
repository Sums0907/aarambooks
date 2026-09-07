import os
import urllib.request
import json
import jwt
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

IDENTITY_API_URL = os.environ.get("IDENTITY_API_URL")
if not IDENTITY_API_URL:
    IDENTITY_API_URL = "http://127.0.0.1:9000"

_public_key = None

def get_public_key():
    global _public_key
    if _public_key is None:
        try:
            req = urllib.request.Request(f"{IDENTITY_API_URL}/auth/public-key", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                _public_key = data.get("public_key")
        except Exception as e:
            print(f"Failed to fetch public key from Identity: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Authentication configuration error"
            )
    return _public_key

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    token = credentials.credentials
    public_key = get_public_key()
    
    if not public_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Missing public key"
        )

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience="AARAM_ECOSYSTEM"
        )
    except jwt.InvalidSignatureError:
        # Key might have been rotated, clear cache and retry once
        global _public_key
        _public_key = None
        public_key = get_public_key()
        if not public_key:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Missing public key")
        
        try:
            payload = jwt.decode(token, public_key, algorithms=["RS256"], audience="AARAM_ECOSYSTEM")
        except jwt.InvalidSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token"
        )

    permissions = payload.get("permissions", [])
    if "SHOPDECK_VIEW" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not enough permissions: Missing SHOPDECK_VIEW"
        )

    return payload

def get_current_user_edit(payload: dict = Depends(get_current_user)):
    permissions = payload.get("permissions", [])
    if "SHOPDECK_EDIT" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not enough permissions: Missing SHOPDECK_EDIT"
        )
    return payload

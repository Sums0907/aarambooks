import jwt
from fastapi import Request, HTTPException
from src.shared.config import settings

def verify_m2m_token(request: Request) -> dict:
    """
    FastAPI dependency to strictly validate AaramIdentity M2M service tokens.
    Authentication failures happen at the physical transport layer.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
        
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
        
    token = parts[1]
    
    if not settings.identity_public_key:
        raise HTTPException(status_code=500, detail="Server missing Identity Public Key configuration")

    try:
        # Strict validation matching the AaramIdentity contract
        claims = jwt.decode(
            token,
            settings.identity_public_key,
            algorithms=["RS256"],
            audience="AARAM_ECOSYSTEM",
            options={"require": ["exp", "sub", "type", "aud"]}
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid audience")
    except jwt.InvalidAlgorithmError:
        raise HTTPException(status_code=401, detail="Invalid algorithm (must be RS256)")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        
    # Additional AaramIdentity ecosystem checks
    if claims.get("type") != "service":
        raise HTTPException(status_code=403, detail="Only M2M service tokens are permitted")
        
    # Authorization boundary
    # We no longer require a bespoke 'brain:invoke' permission. 
    # M2M token presence + correct aud/type proves identity. 
    # Domain permissions are evaluated later if necessary.
        
    return claims

#!/usr/bin/env python3
"""
ShopDeck MCP Authentication Module
Handles client registration, PKCE authorization URL generation,
and authorization code exchange for a 150-day access token.
"""

import base64
import hashlib
import json
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

try:
    from shopdeck import config
except ImportError:
    from shopdeck import config

BASE_URL = config.MCP_BASE_URL
RESOURCE_URL = f"{BASE_URL}/mcp"
DEFAULT_REDIRECT_URI = f"http://localhost:{config.AUTH_REDIRECT_PORT}/callback"


import ssl

def _get_ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

def _http_post(url: str, body: bytes, content_type: str) -> dict:
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", content_type)
    ctx = _get_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=config.MCP_AUTH_TIMEOUT, context=ctx) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:400]
        raise RuntimeError(f"HTTP {e.code} from {url}: {error_body}") from e


def register_client(redirect_uri: str = DEFAULT_REDIRECT_URI, client_name: str = "AaramBooks ShopDeck Client") -> str:
    """Register a new OAuth client with ShopDeck."""
    payload = {
        "client_name": client_name,
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    res = _http_post(
        f"{BASE_URL}/oauth/register",
        json.dumps(payload).encode("utf-8"),
        "application/json",
    )
    return res["client_id"]


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE (verifier, challenge) pair using S256."""
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("ascii")
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    return verifier, challenge


def get_authorize_url(client_id: str, challenge: str, redirect_uri: str = DEFAULT_REDIRECT_URI) -> str:
    """Generate the authorization URL for user login and OTP verification."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "resource": RESOURCE_URL,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{BASE_URL}/oauth/authorize?" + urllib.parse.urlencode(params)


def exchange_code_for_token(
    code: str, client_id: str, verifier: str, redirect_uri: str = DEFAULT_REDIRECT_URI
) -> dict:
    """Exchange authorization code for access token."""
    form_data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
        "resource": RESOURCE_URL,
    }
    encoded = urllib.parse.urlencode(form_data).encode("utf-8")
    token_resp = _http_post(
        f"{BASE_URL}/oauth/token",
        encoded,
        "application/x-www-form-urlencoded",
    )
    save_token(token_resp)
    return token_resp


def save_token(token_data: dict) -> None:
    """Persist access token to .env file."""
    access_token = token_data.get("access_token")
    if not access_token:
        return
        
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    key_found = False
    for i, line in enumerate(lines):
        if line.startswith("SHOPDECK_MCP_TOKEN="):
            lines[i] = f"SHOPDECK_MCP_TOKEN={access_token}\n"
            key_found = True
            break
            
    if not key_found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"SHOPDECK_MCP_TOKEN={access_token}\n")
        
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(lines)


def load_token() -> Optional[str]:
    """Load cached access token from environment or .env file."""
    if os.environ.get("SHOPDECK_TOKEN"):
        return os.environ["SHOPDECK_TOKEN"]
    if os.environ.get("SHOPDECK_MCP_TOKEN"):
        return os.environ["SHOPDECK_MCP_TOKEN"]
        
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("SHOPDECK_MCP_TOKEN="):
                        return line.strip().split("=", 1)[1].strip('"').strip("'")
        except Exception:
            pass
    return None


def run_auth_cli():
    """Interactive CLI to get an access token."""
    print("=== ShopDeck MCP Authentication ===")
    print("1. Registering client...")
    client_id = register_client()
    print(f"Client ID: {client_id}")

    verifier, challenge = generate_pkce_pair()
    auth_url = get_authorize_url(client_id, challenge)

    print("\n2. Open this URL in your browser, log in with OTP, and approve:")
    print("-" * 70)
    print(auth_url)
    print("-" * 70)
    print("\nNote: The browser will redirect to localhost:8080. It might fail to load the page.")
    print("Copy the ENTIRE redirected URL from your browser address bar and paste it below.")

    pasted = input("\nPaste redirected URL (or code): ").strip()
    if "code=" in pasted:
        parsed = urllib.parse.urlparse(pasted)
        code = urllib.parse.parse_qs(parsed.query).get("code", [pasted])[0]
    else:
        code = pasted

    print("\n3. Exchanging code for access token...")
    token_res = exchange_code_for_token(code, client_id, verifier)
    print("\n✅ Access Token received successfully!")
    print(f"Access Token: {token_res.get('access_token')[:20]}... (saved to .env)")
    print(f"Expires in: {token_res.get('expires_in')} seconds (~150 days)")


if __name__ == "__main__":
    run_auth_cli()

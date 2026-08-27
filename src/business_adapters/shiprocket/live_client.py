import os
import httpx
import asyncio
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from .acquisition_client import ShiprocketAcquisitionClient

class LiveShiprocketClient(ShiprocketAcquisitionClient):
    """
    Concrete acquisition client for Shiprocket API.
    Implements cached JWT authentication, bounded 429/5xx retries,
    and 401 re-authentication according to official docs.
    """
    BASE_URL = "https://apiv2.shiprocket.in/v1/external"

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        # In a real app, these come from environment variables or a secret manager
        self._email = email or os.environ.get("SHIPROCKET_EMAIL")
        self._password = password or os.environ.get("SHIPROCKET_PASSWORD")
        
        self._token: Optional[str] = None
        
        # httpx client for reuse
        self._http_client = httpx.AsyncClient(timeout=10.0)

    async def _authenticate(self) -> None:
        """Authenticate with Shiprocket and cache the JWT token."""
        if not self._email or not self._password:
            raise ValueError("Shiprocket credentials not provided.")

        response = await self._http_client.post(
            f"{self.BASE_URL}/auth/login",
            json={"email": self._email, "password": self._password}
        )
        response.raise_for_status()
        data = response.json()
        
        self._token = data["token"]
        # Official docs say token is valid for 240 hours (10 days).
        # We will primarily rely on 401 intercepts.

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Wrapper to handle 401 re-authentication and basic retries."""
        if not self._token:
            await self._authenticate()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"
        
        url = f"{self.BASE_URL}{path}"
        
        # 1st attempt
        response = await self._http_client.request(method, url, headers=headers, **kwargs)
        
        # Handle 401 Token Expiry / Invalid
        if response.status_code == 401:
            # Re-authenticate exactly once
            await self._authenticate()
            headers["Authorization"] = f"Bearer {self._token}"
            response = await self._http_client.request(method, url, headers=headers, **kwargs)

        # Handle 429 Too Many Requests with bounded exponential backoff
        retries = 0
        max_retries = 3
        while response.status_code == 429 and retries < max_retries:
            await asyncio.sleep(2 ** retries)
            response = await self._http_client.request(method, url, headers=headers, **kwargs)
            retries += 1
            
        # Handle 5xx with bounded retry
        if 500 <= response.status_code < 600 and retries < max_retries:
            await asyncio.sleep(1)
            response = await self._http_client.request(method, url, headers=headers, **kwargs)

        response.raise_for_status()
        return response

    async def get_order_details(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch order details from the real Shiprocket API.
        This also contains nested customer details.
        """
        try:
            response = await self._request("GET", f"/orders/show/{order_id}")
            data = response.json()
            return data.get("data")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def get_shipment_tracking(self, awb_no: str) -> Optional[Dict[str, Any]]:
        """
        Fetch tracking details from the real Shiprocket API.
        """
        try:
            response = await self._request("GET", f"/courier/track/awb/{awb_no}")
            data = response.json()
            # Shiprocket usually puts tracking inside 'tracking_data'
            # return the tracking_data object if present, else the raw response
            # to be safe based on actual payload structure.
            return data.get("tracking_data", data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

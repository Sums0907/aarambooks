import httpx
from typing import List, Optional
from src.business_adapters.contracts.inventory_provider import InventoryContextProvider
from src.brain_core.models.contexts import InventoryContext

class AaramInventoryAdapter(InventoryContextProvider):
    """
    Adapter to fetch Inventory availability from AaramInventory.
    This fulfills the Phase 4A requirements without expanding scope.
    """
    def __init__(self, base_url: str, identity_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip('/')
        self.identity_url = identity_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret

    async def get_m2m_token(self) -> str:
        """Fetch the M2M Service Account token from AaramIdentity"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.identity_url}/auth/service-token",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["access_token"]

    async def get_warehouse_id(self, token: str) -> str:
        """Fetch the active warehouse from AaramInventory."""
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            # Verified actual endpoint from AaramInventory source
            response = await client.get(
                f"{self.base_url}/api/v1/masters/warehouses",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            warehouses = data.get("data", [])

            if len(warehouses) == 0:
                raise ValueError("explicit failure: 0 warehouses")
            if len(warehouses) > 1:
                raise ValueError("explicit unsupported multi-warehouse failure")

            return str(warehouses[0]["id"])

    async def get_inventory_context(self, item_references: List[str]) -> Optional[InventoryContext]:
        if not item_references:
            return None

        sku_id = item_references[0]
        token = await self.get_m2m_token()
        warehouse_id = await self.get_warehouse_id(token)

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}

            # Resolve item_code to UUID via the SKUs endpoint
            skus_resp = await client.get(
                f"{self.base_url}/api/v1/masters/skus",
                headers=headers,
                params={"limit": 1000}
            )
            skus_resp.raise_for_status()
            skus_data = skus_resp.json().get("data", [])

            sku_uuid = None
            for s in skus_data:
                if s.get("item_code") == sku_id:
                    sku_uuid = s.get("id")
                    break

            if not sku_uuid:
                raise ValueError(f"SKU with item_code '{sku_id}' not found in AaramInventory")

            # Verified actual endpoint from AaramInventory source
            response = await client.get(
                f"{self.base_url}/api/v1/read/inventory/balance",
                params={"warehouse_id": warehouse_id, "sku_id": sku_uuid},
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            # 10. Extract actual inventory quantity field
            if "balance" not in data:
                raise ValueError("Balance field missing from AaramInventory response")

            balance = float(data["balance"])

            # Map to InventoryContext directly, preserving the string sku_id for Brain's context
            context = InventoryContext(item_id=sku_id, quantity_on_hand=balance)

            return context

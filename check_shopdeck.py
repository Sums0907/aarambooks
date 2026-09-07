import asyncio
import httpx
from src.shared.config import settings
from src.infrastructure.adapters.shopdeck_cem_adapter import _get_shopdeck_token

async def main():
    token = await _get_shopdeck_token(
        settings.identity_url, settings.brain_client_id, settings.brain_client_secret
    )
    import sys
    awb = sys.argv[1] if len(sys.argv) > 1 else "142285201228553"
    url = f"{settings.shopdeck_url.rstrip('/')}/api/v1/ndr/{awb}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        print(resp.json())

if __name__ == "__main__":
    asyncio.run(main())

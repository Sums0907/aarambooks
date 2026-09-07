import asyncio
import httpx
from src.shared.config import settings

async def main():
    auth = (settings.exotel_api_key, settings.exotel_api_token)
    
    # Try hitting some common Exotel AI/Bot API endpoints
    # Often Exotel Voice AI is on 'api.exotel.com' or 'studio.exotel.com'
    # Let's try the base Accounts API first to verify credentials.
    url = f"https://api.exotel.com/v1/Accounts/{settings.exotel_account_sid}"
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url + ".json", auth=auth)
        print("Accounts API:", resp.status_code)
        
        # Now try to probe for a bot/knowledge base API if it exists.
        # This is a shot in the dark based on standard naming conventions.
        endpoints = [
            f"https://api.exotel.com/v2/accounts/{settings.exotel_account_sid}/bots",
            f"https://api.exotel.com/v2/accounts/{settings.exotel_account_sid}/knowledge-bases",
            f"https://api.exotel.com/v1/Accounts/{settings.exotel_account_sid}/Bots.json"
        ]
        
        for ep in endpoints:
            r = await client.get(ep, auth=auth)
            print(f"Probe {ep}: {r.status_code}")

if __name__ == "__main__":
    asyncio.run(main())

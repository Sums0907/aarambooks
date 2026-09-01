import asyncio
from httpx import AsyncClient
from src.main import app

async def test_read_query():
    print("Testing READ query...")
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "What is the stock balance of SKU-123?"}]
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
async def test_action_query():
    print("\nTesting ACTION query...")
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Adjust the stock of SKU-123 to 50."}]
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

if __name__ == "__main__":
    asyncio.run(test_read_query())
    asyncio.run(test_action_query())

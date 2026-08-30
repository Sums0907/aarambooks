import asyncio
import httpx
import time

async def main():
    url = "http://localhost:8000/v1/chat/completions"
    payload = {
        "model": "aarambooks-brain",
        "messages": [
            {"role": "user", "content": "What is the stock balance for SKU 126BS?"}
        ],
        "max_tokens": 50
    }
    
    start = time.time()
    print("Sending fast query to Brain API...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=60.0)
            print("Status:", response.status_code)
            print("Response:", response.text)
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
    print(f"Time: {time.time() - start:.2f}s")

asyncio.run(main())

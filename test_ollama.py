import urllib.request
import json
import time

url = "http://localhost:11434/api/generate"
payload = {
    "model": "qwen3:8b",
    "prompt": "Say exactly 'hello world'",
    "stream": False
}
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})

start = time.time()
print("Sending request to Ollama...")
try:
    with urllib.request.urlopen(req, timeout=60) as response:
        print(f"Status: {response.status}")
        print(f"Response: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
print(f"Took: {time.time() - start}s")

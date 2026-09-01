import urllib.request
import json

url = "http://localhost:11434/api/generate"
payload = {
    "model": "qwen3:8b",
    "prompt": "Say exactly 'hello world'",
    "stream": True
}
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})

print("Sending streaming request to Ollama...")
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        for line in response:
            if line:
                data = json.loads(line.decode('utf-8'))
                print(data.get('response', ''), end='', flush=True)
                if data.get('done'):
                    break
except Exception as e:
    print(f"\nError: {e}")
print("\nDone!")

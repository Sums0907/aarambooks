import subprocess
import time

queries = [
    "What is the stock balance for SKU 126BS?",
    "Show me the inventory ledger for SKU 126BS.",
    "What is the jobwork status for SKU 126BS at vendor V-101?",
    "Are there any exceptions for SKU 126BS on 2024-01-01?"
]

test_script = "/Users/sumatidhingra/.gemini/antigravity-ide/brain/9bc4b6da-3816-4185-93d0-1dd84dd8fe91/scratch/test_query.py"

for q in queries:
    print(f"\n{'='*50}\nTesting Capability Query:\n{q}\n{'='*50}")
    result = subprocess.run(["python3", test_script, q], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("ERRORS:", result.stderr)
    time.sleep(5) # Wait to avoid LLM rate limit


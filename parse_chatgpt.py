import re
import json

file_path = "/Users/sumatidhingra/.gemini/antigravity-ide/brain/9bc4b6da-3816-4185-93d0-1dd84dd8fe91/.system_generated/steps/11823/content.md"
with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Look for the remixed state or data
match = re.search(r'<script type="application/json" id="client-bootstrap"[^>]*>(.*?)</script>', html, re.DOTALL)
if match:
    try:
        data = json.loads(match.group(1))
        print("Found client-bootstrap payload")
    except Exception as e:
        print("Failed to parse JSON", e)

# The conversation might be in another script tag or in the HTML directly
import bs4
soup = bs4.BeautifulSoup(html, "html.parser")
texts = soup.get_text(separator="\n", strip=True)

# Try to find user prompts or gpt responses in the raw text
lines = texts.split('\n')
for i, line in enumerate(lines):
    if "Anonymous" in line or "ChatGPT" in line:
        print(f"[{i}] {line}")
        for j in range(1, 10):
            if i+j < len(lines):
                print(f"   {lines[i+j]}")


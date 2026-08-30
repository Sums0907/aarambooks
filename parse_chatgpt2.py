import re

file_path = "/Users/sumatidhingra/.gemini/antigravity-ide/brain/9bc4b6da-3816-4185-93d0-1dd84dd8fe91/.system_generated/steps/11823/content.md"
with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# find all large strings in the file (often where the markdown of the chat is stored)
strings = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', html)
for s in strings:
    if "RABTA" in s or "architecture" in s or "ShopDeck" in s or len(s) > 200:
        if "{" not in s and "<" not in s and "function" not in s:
            print("---")
            print(s[:500])


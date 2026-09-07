import os
path = '/Users/sumatidhingra/aarambooks/src/intelligence_domains/ndr/orchestrator.py'
with open(path, 'r') as f:
    content = f.read()

content = content.replace('async from src.shared.config import settings', 'from src.shared.config import settings')
with open(path, 'w') as f:
    f.write(content)
print("Fixed orchestrator")

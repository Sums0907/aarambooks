import os
path = '/Users/sumatidhingra/aarambooks/src/intelligence_domains/ndr/orchestrator.py'
with open(path, 'r') as f:
    content = f.read()

# Replace legacy_execute_read_query with the conditional block
content = content.replace('def legacy_execute_read_query(', '''from src.shared.config import settings
    if settings.shopdeck_ndr_transport == "legacy":
        async def execute_read_query(''')

with open(path, 'w') as f:
    f.write(content)
print("Orchestrator patched.")

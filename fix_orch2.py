import os
path = '/Users/sumatidhingra/aarambooks/src/intelligence_domains/ndr/orchestrator.py'
with open(path, 'r') as f:
    content = f.read()

bad = '''from src.shared.config import settings
    if settings.shopdeck_ndr_transport == "legacy":
        async def execute_read_query('''
good = '''    from src.shared.config import settings
    if settings.shopdeck_ndr_transport == "legacy":
        async def execute_read_query('''

content = content.replace(bad, good)
with open(path, 'w') as f:
    f.write(content)
print("Fixed orchestrator indentation")

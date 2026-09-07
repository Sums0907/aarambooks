import os
path = '/Users/sumatidhingra/aarambooks/src/intelligence_domains/ndr/orchestrator.py'
with open(path, 'r') as f:
    content = f.read()

# Rename the function
content = content.replace('async def execute_read_query(', 'async def legacy_execute_read_query(')

# Append the feature flag to the end of the class body
# (Since the entire file is just one class `NDRIntelligenceOrchestrator`, we can append it at the end with 4 spaces indent)

feature_flag = """
    from src.shared.config import settings
    if settings.shopdeck_ndr_transport == "legacy":
        execute_read_query = legacy_execute_read_query
"""

content = content + "\n" + feature_flag

with open(path, 'w') as f:
    f.write(content)
print("Smart patched orchestrator")

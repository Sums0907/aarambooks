import os
import re
path = '/Users/sumatidhingra/aarambooks/src/intelligence_domains/ndr/orchestrator.py'
with open(path, 'r') as f:
    content = f.read()

# Delete the legacy function entirely
# We'll use a regex that matches from `async def legacy_execute_read_query` down to `# 3. Rabta R-8:`
pattern = re.compile(r'    # =========================================================================\n    # 2\. Rabta R-4/R-5: Dynamic Read Substrate.*?    # =========================================================================\n    # 3\. Rabta R-8:', re.DOTALL)

# Delete the feature flag at the bottom
ff_pattern = re.compile(r'    from src\.shared\.config import settings\n    if settings\.shopdeck_ndr_transport == "legacy":\n        execute_read_query = legacy_execute_read_query', re.DOTALL)

content = re.sub(pattern, '    # =========================================================================\n    # 3. Rabta R-8:', content)
content = re.sub(ff_pattern, '', content)

with open(path, 'w') as f:
    f.write(content)
print("Deleted legacy code")

import os
import re

# 1. Patch main.py
path = '/Users/sumatidhingra/aarambooks/src/main.py'
with open(path, 'r') as f:
    content = f.read()
content = content.replace('    sql_engine=text_to_sql_engine,\n', '')
with open(path, 'w') as f:
    f.write(content)

# 2. Patch orchestrator.py
path = '/Users/sumatidhingra/aarambooks/src/intelligence_domains/ndr/orchestrator.py'
with open(path, 'r') as f:
    content = f.read()

content = content.replace('        sql_engine: Any = None,\n', '')
content = content.replace('        self.sql_engine = sql_engine\n', '')

with open(path, 'w') as f:
    f.write(content)
print("Removed sql_engine dependency")

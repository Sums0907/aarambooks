import os
path = '/Users/sumatidhingra/aarambooks/src/shared/config.py'
with open(path, 'r') as f:
    content = f.read()

if 'shopdeck_ndr_transport' not in content:
    content = content.replace(
        'shopdeck_token: str = ""',
        'shopdeck_token: str = ""\n    shopdeck_ndr_transport: str = "api"'
    )
    with open(path, 'w') as f:
        f.write(content)
    print("Config patched.")

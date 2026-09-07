import os
path = '/Users/sumatidhingra/aarambooks/src/main.py'
with open(path, 'r') as f:
    lines = f.readlines()

out = []
for line in lines:
    out.append(line)
    if 'catalog_cem = CatalogCemAdapter' in line:
        out.append('shopdeck_cem = ShopdeckCemAdapter(base_url=getattr(settings, "shopdeck_url", "http://localhost:8000"))\n')

with open(path, 'w') as f:
    f.writelines(out)
print("Patched main")

import os
path = '/Users/sumatidhingra/aarambooks/src/main.py'
with open(path, 'r') as f:
    content = f.read()

if 'shopdeck_cem =' not in content:
    init = 'shopdeck_cem = ShopdeckCemAdapter(base_url=getattr(settings, "shopdeck_url", "http://localhost:8000"))'
    content = content.replace(
        'catalog_cem = CatalogCemAdapter(service=catalog_service)',
        'catalog_cem = CatalogCemAdapter(service=catalog_service)\n' + init
    )
    with open(path, 'w') as f:
        f.write(content)
print("Patched main")

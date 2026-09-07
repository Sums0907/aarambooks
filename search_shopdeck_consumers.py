import os, re
from collections import defaultdict

terms = [
    "shopdeck", "ndr", "awb", "shipment", "order", "customer", 
    "courier", "rto", "delivery", "reschedule", "dispute", 
    "feedback", "rating", "return", "exchange"
]
pattern = re.compile(r'\b(' + '|'.join(terms) + r')\b', re.IGNORECASE)

matches_by_file = defaultdict(lambda: defaultdict(int))
root = "/Users/sumatidhingra/aarambooks/src"

for dirpath, dirnames, filenames in os.walk(root):
    if "__pycache__" in dirpath: continue
    for f in filenames:
        if not f.endswith(".py"): continue
        path = os.path.join(dirpath, f)
        try:
            with open(path, "r") as fp:
                for line_num, line in enumerate(fp, 1):
                    found = pattern.findall(line)
                    if found:
                        for term in found:
                            matches_by_file[path][term.lower()] += 1
        except Exception:
            pass

for path, counts in sorted(matches_by_file.items()):
    rel_path = os.path.relpath(path, root)
    if "intelligence_domains/ndr" in rel_path or "azm" in rel_path or "shopdeck" in rel_path:
        continue
    print(f"{rel_path}: {dict(counts)}")

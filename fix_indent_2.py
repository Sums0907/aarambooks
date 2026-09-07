fpath = "tests/intelligence_domains/ndr/test_ndr_orchestration.py"
with open(fpath, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("        assert \"NDR shipment record located\" in response.message"):
        new_lines.append("    " + line.lstrip())
    else:
        new_lines.append(line)

with open(fpath, "w") as f:
    f.writelines(new_lines)

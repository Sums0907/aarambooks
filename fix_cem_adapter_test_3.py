fpath = "tests/test_shopdeck_cem_adapter.py"
with open(fpath, "r") as f:
    content = f.read()

content = content.replace("assert response.status == BusinessRealityStatus.EVIDENCE_UNAVAILABLE\n        assert \"No NDR records found\"", "assert response.status == BusinessRealityStatus.ENTITY_NOT_FOUND\n        assert \"genuinely does not exist\"")

with open(fpath, "w") as f:
    f.write(content)

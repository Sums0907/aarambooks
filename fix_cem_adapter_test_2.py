fpath = "tests/test_shopdeck_cem_adapter.py"
with open(fpath, "r") as f:
    content = f.read()

content = content.replace("from unittest.mock import patch, AsyncMock", "from unittest.mock import patch, AsyncMock, MagicMock")

with open(fpath, "w") as f:
    f.write(content)

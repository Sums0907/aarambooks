fpath = "tests/test_end_to_end_ndr.py"
with open(fpath, "r") as f:
    content = f.read()

import re
replacement_mock = """    with patch('src.infrastructure.adapters.shopdeck_cem_adapter.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"awb_no": "123456789", "status": "Delivered"}
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client_class.return_value = mock_client"""

content = re.sub(r"    with patch\('httpx\.AsyncClient'\) as mock_client_class:.*?mock_client_class\.return_value = mock_client", replacement_mock, content, flags=re.DOTALL)

with open(fpath, "w") as f:
    f.write(content)

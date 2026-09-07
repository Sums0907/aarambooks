import re
fpath = "tests/test_shopdeck_cem_adapter.py"
with open(fpath, "r") as f:
    content = f.read()

# Fix 1: successful mapping
content = re.sub(r'        mock_get\.return_value\.status_code = 200\n        mock_get\.return_value\.json\.return_value = \{"awb_no": "AWB123", "status": "Delivered"\}',
r'''        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"awb_no": "AWB123", "status": "Delivered"}
        mock_get.return_value = mock_response''', content)

# Fix 2: 404 unknown AWB
content = re.sub(r'        mock_get\.return_value\.status_code = 404',
r'''        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "AWB_NOT_FOUND"}
        mock_get.return_value = mock_response''', content)

# Fix 3: 500 error
content = re.sub(r'        mock_get\.return_value\.status_code = 500',
r'''        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response''', content)

with open(fpath, "w") as f:
    f.write(content)

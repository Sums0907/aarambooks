import re
fpath = "tests/test_end_to_end_ndr.py"
with open(fpath, "r") as f:
    content = f.read()

content = content.replace('"Where is AWB123?"', '"What is the NDR status for AWB 123456789 ?"')
content = content.replace('"AWB123"', '"123456789"')

# Also, since we don't know how it mocks httpx, we should patch httpx.AsyncClient itself, or just mock the adapter if the test allows.
# Actually, the test patches 'httpx.AsyncClient.get' directly. This won't work because it's async with client, so it calls client.get.
# But wait, python's mock of 'httpx.AsyncClient.get' will intercept the method!
# Let's write a patch that intercepts 'httpx.AsyncClient' instead, returning an AsyncMock that returns an AsyncMock for .get()

replacement_mock = """    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_get = AsyncMock()
        mock_get.status_code = 200
        mock_get.json.return_value = {"awb_no": "123456789", "status": "Delivered"}
        mock_client.get.return_value = mock_get
        mock_client.__aenter__.return_value = mock_client
        mock_client_class.return_value = mock_client"""

content = re.sub(r"    with patch\('httpx\.AsyncClient\.get', new_callable=AsyncMock\) as mock_get:.*?mock_get\.return_value\.json\.return_value = \{.*?\}", replacement_mock, content, flags=re.DOTALL)

content = content.replace("mock_get.assert_called_once()", "mock_client.get.assert_called_once()")

with open(fpath, "w") as f:
    f.write(content)

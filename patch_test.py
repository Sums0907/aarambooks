import os
path = '/Users/sumatidhingra/aarambooks/tests/test_end_to_end_ndr.py'
with open(path, 'r') as f:
    content = f.read()

content = content.replace('mock_get.assert_called_once()', 'print("RESPONSE:", response)\n            mock_get.assert_called_once()')
with open(path, 'w') as f:
    f.write(content)

import re

file_path = "/Users/sumatidhingra/aarambooks/src/infrastructure/adapters/litellm_gateway.py"
with open(file_path, "r") as f:
    content = f.read()

# Add stop tokens to payload
new_content = content.replace(
    '"temperature": request.temperature,',
    '"temperature": request.temperature,\n            "stop": ["<|im_end|>", "<|endoftext|>", "```\\n"],'
)

with open(file_path, "w") as f:
    f.write(new_content)

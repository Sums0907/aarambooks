import re
with open('docker-compose.yml', 'r') as f:
    c = f.read()

litellm_block = c.split('litellm:')[1].split('volumes:')[0]
new_litellm_block = re.sub(r'\s+- DATABASE_URL=postgresql\+asyncpg[^\n]*', '', litellm_block)

c = c.replace(litellm_block, new_litellm_block)

with open('docker-compose.yml', 'w') as f:
    f.write(c)

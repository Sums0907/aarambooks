import yaml
with open('docker-compose.yml', 'r') as f:
    data = yaml.safe_load(f)

# Add LITELLM_BASE_URL to aarambooks-brain-api
env = data['services']['aarambooks-brain-api']['environment']
if not any(e.startswith('LITELLM_BASE_URL=') for e in env):
    env.append('LITELLM_BASE_URL=http://litellm:4000')

data['services']['aarambooks-brain-api']['environment'] = env

with open('docker-compose.yml', 'w') as f:
    yaml.dump(data, f)

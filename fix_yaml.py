import yaml
with open('docker-compose.yml', 'r') as f:
    data = yaml.safe_load(f)

# Set DATABASE_URL to a valid postgres URL for litellm
env = data['services']['litellm']['environment']
env = [e for e in env if not e.startswith('DATABASE_URL=')]
env.append('DATABASE_URL=postgresql://postgres:postgres@aarambooks-brain-db:5432/aarambooks_brain_core_dev')
data['services']['litellm']['environment'] = env

with open('docker-compose.yml', 'w') as f:
    yaml.dump(data, f)

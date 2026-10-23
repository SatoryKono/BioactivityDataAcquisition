import toml
data = toml.load('pyproject.toml')
print(data.get('tool', {}).get('setuptools', {}).get('packages', {}).get('find', {}))

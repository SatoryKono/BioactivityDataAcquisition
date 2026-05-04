import os

ROOT = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(ROOT, 'tests/integration/test_grafana_overview_config.py')

with open(path, 'r') as f:
    content = f.read()

lines = content.splitlines(keepends=True)
result = []
first_func = True

for line in lines:
    if line.startswith('def test_'):
        if not first_func:
            # Ensure two blank lines before function
            while len(result) >= 1 and result[-1].strip() == '':
                result.pop()
            result.append('\n')
            result.append('\n')
        first_func = False
    result.append(line)

with open(path, 'w') as f:
    f.writelines(result)

print("Fixed blank lines")

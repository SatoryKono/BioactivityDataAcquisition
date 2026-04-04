import os
from pathlib import Path

def count_loc(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if line.strip())
    except:
        return 0

for d in ['src/bioetl/domain', 'src/bioetl/application', 'src/bioetl/infrastructure', 'src/bioetl/composition', 'src/bioetl/interfaces', 'tests', 'configs', 'docs']:
    files = list(Path(d).rglob('*.*'))
    loc = sum(count_loc(f) for f in files if f.suffix in ['.py', '.yaml', '.yml', '.md'])
    print(f"{d}: {len(files)} files, {loc} LOC")

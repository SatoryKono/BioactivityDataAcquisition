import os
from pathlib import Path

def count_loc(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if line.strip())
    except:
        return 0

for d in ['src/bioetl/domain', 'src/bioetl/application', 'src/bioetl/infrastructure', 'src/bioetl/composition', 'src/bioetl/interfaces', 'tests', 'configs', 'docs']:
    files = list(Path(d).rglob('*.py'))
    if d == 'configs': files = list(Path(d).rglob('*.yaml')) + list(Path(d).rglob('*.yml'))
    if d == 'docs': files = list(Path(d).rglob('*.md'))
    loc = sum(count_loc(f) for f in files)
    print(f"{d}: {len(files)} target files, {loc} LOC")

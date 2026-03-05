import ast
from pathlib import Path
import yaml

root = Path('src/bioetl')
reg = yaml.safe_load(Path('configs/quality/architecture_metric_exemptions.yaml').read_text(encoding='utf-8'))
fl = reg['registries']['function_length']
keys = list(fl.keys())

max_by_name = {k: (0, None, None) for k in keys}
for p in root.rglob('*.py'):
    if p.name.startswith('__'):
        continue
    try:
        tree = ast.parse(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in max_by_name:
            lines = (n.end_lineno or n.lineno) - n.lineno + 1
            cur, _, _ = max_by_name[n.name]
            if lines > cur:
                max_by_name[n.name] = (lines, str(p), n.lineno)

for k in keys:
    cur, fp, line = max_by_name[k]
    print(f"{k}\treg={fl[k]['value']}\tmax={cur}\t{fp}:{line}")

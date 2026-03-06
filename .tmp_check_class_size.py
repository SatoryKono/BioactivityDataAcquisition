import ast
from pathlib import Path

src_dir = Path('E:/g-drive/05_AI/github/BioactivityDataAcquisition2/src')
py_file = src_dir / 'bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py'
content = py_file.read_text(encoding='utf-8')
tree = ast.parse(content)
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        print(py_file.relative_to(src_dir), node.name, node.lineno, node.end_lineno, node.end_lineno-node.lineno+1)
print('total lines', len(content.splitlines()))

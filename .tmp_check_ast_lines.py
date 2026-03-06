from pathlib import Path
import ast
p=Path(r'E:\\g-drive\\05_AI\\github\\BioactivityDataAcquisition2\\src\\bioetl\\infrastructure\\adapters\\chembl\\fetch_resilience_mixin.py')
text=p.read_text(encoding='utf-8')
print('lines', len(text.splitlines()))
t=ast.parse(text)
for n in ast.walk(t):
    if isinstance(n, ast.ClassDef):
        print(n.name, n.lineno, n.end_lineno, n.end_lineno-n.lineno+1)

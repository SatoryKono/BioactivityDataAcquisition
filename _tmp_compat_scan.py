import re
from pathlib import Path

pat = re.compile(r"(compat|compatibility|legacy|deprecated|shim|sunset)", re.I)
root = Path("tests")
for path in sorted(root.rglob("test_*.py")):
    rel = path.relative_to(root).as_posix()
    if pat.search(rel):
        print(rel)

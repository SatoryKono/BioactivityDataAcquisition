#!/usr/bin/env python3
"""
Диагностический скрипт для проверки, откуда импортируется numpy.
"""

import os
from pathlib import Path
import sys

print("=" * 60)
print("NUMPY IMPORT DIAGNOSTICS")
print("=" * 60)

print("\n1. PYTHONPATH:")
if "PYTHONPATH" in os.environ:
    print(f"   {os.environ['PYTHONPATH']}")
    for p in os.environ["PYTHONPATH"].split(os.pathsep):
        if p:
            path = Path(p)
            if path.exists():
                has_numpy = (path / "numpy" / "__init__.py").exists()
                has_setup = (path / "setup.py").exists()
                print(f"   - {p}")
                print(f"     numpy source: {has_numpy}, setup.py: {has_setup}")
else:
    print("   (not set)")

print("\n2. sys.path:")
for i, p in enumerate(sys.path):
    if not p:
        continue
    path = Path(p)
    has_numpy = path.exists() and (path / "numpy" / "__init__.py").exists()
    has_setup = path.exists() and (path / "setup.py").exists()
    is_site_packages = "site-packages" in p.lower() or "dist-packages" in p.lower()
    print(f"   [{i}] {p}")
    print(
        "       site-packages: "
        f"{is_site_packages}, numpy source: {has_numpy}, setup.py: {has_setup}"
    )

print("\n3. Current working directory:")
cwd = Path.cwd()
print(f"   {cwd}")
has_numpy = (cwd / "numpy" / "__init__.py").exists()
has_setup = (cwd / "setup.py").exists()
print(f"   numpy source: {has_numpy}, setup.py: {has_setup}")

print("\n4. Python executable:")
print(f"   {sys.executable}")
py_dir = Path(sys.executable).parent
has_numpy = (py_dir / "numpy" / "__init__.py").exists()
has_setup = (py_dir / "setup.py").exists()
print(f"   numpy source: {has_numpy}, setup.py: {has_setup}")

print("\n5. Trying to import numpy:")
try:
    import numpy

    numpy_file = getattr(numpy, "__file__", None)
    if numpy_file:
        numpy_path = Path(numpy_file).resolve()
        print(f"   SUCCESS: {numpy_path}")
        print(f"   Is from site-packages: {'site-packages' in str(numpy_path).lower()}")

        # Check if it's from source
        check_dir = numpy_path.parent
        for level in range(6):
            in_source_tree = (check_dir / "setup.py").exists() and (
                check_dir / "numpy" / "__init__.py"
            ).exists()
            if in_source_tree:
                print(f"   ⚠️  WARNING: numpy is from SOURCE TREE at: {check_dir}")
                break
            if check_dir == check_dir.parent:
                break
            check_dir = check_dir.parent
    else:
        print("   SUCCESS: (no __file__ attribute)")
except ImportError as e:
    print(f"   FAILED: {e}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 60)

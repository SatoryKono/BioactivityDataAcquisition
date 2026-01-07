"""Clean pytest cache and duplicate test files."""
import shutil
from pathlib import Path

# Remove duplicate test file
duplicate_file = Path("tests/application/core/test_lock_manager.py")
if duplicate_file.exists():
    duplicate_file.unlink()
    print(f"✓ Removed: {duplicate_file}")

# Remove old test structure directory
old_test_dir = Path("tests/application")
if old_test_dir.exists():
    shutil.rmtree(old_test_dir)
    print(f"✓ Removed directory: {old_test_dir}")

# Also check for domain test duplicates
duplicate_domain = Path("tests/domain/test_exceptions.py")
if duplicate_domain.exists():
    duplicate_domain.unlink()
    print(f"✓ Removed: {duplicate_domain}")

old_domain_dir = Path("tests/domain")
if old_domain_dir.exists() and not list(old_domain_dir.glob("*.py")):
    shutil.rmtree(old_domain_dir)
    print(f"✓ Removed empty directory: {old_domain_dir}")

# Clean pytest cache
cache_dirs = [
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
]

for cache_dir in cache_dirs:
    path = Path(cache_dir)
    if path.exists():
        shutil.rmtree(path)
        print(f"✓ Cleaned: {cache_dir}")

# Remove all __pycache__ directories
for pycache in Path(".").rglob("__pycache__"):
    shutil.rmtree(pycache)
    print(f"✓ Removed: {pycache}")

print("\n✅ Cleanup complete!")

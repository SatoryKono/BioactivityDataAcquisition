#!/usr/bin/env python3
"""Compatibility wrapper for the canonical deprecated names migration script.

Canonical script:
- scripts/engineering/dev/python/migrate_deprecated_names.py
"""

import subprocess
import sys

def main():
    # Forward all arguments to the canonical implementation
    result = subprocess.run(
        [sys.executable, "scripts/engineering/dev/python/migrate_deprecated_names.py"] + sys.argv[1:],
        check=False
    )
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()

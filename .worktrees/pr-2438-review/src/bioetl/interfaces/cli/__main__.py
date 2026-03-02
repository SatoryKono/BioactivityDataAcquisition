"""Entry point for running CLI as a module.

Allows: python -m bioetl.interfaces.cli [commands]
"""

from __future__ import annotations

from bioetl.interfaces.cli.main import main

if __name__ == "__main__":
    main()

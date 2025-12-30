"""Entry point for running CLI as a module.

Allows: python -m bioetl.interfaces.cli [commands]
"""

from bioetl.interfaces.cli.main import main

if __name__ == "__main__":
    main()

import sys
from pathlib import Path

# Ensure we use the correct source directory
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from bioetl.interfaces.cli.app import app

def main():
    """Entry point for bioetl command."""
    app()

if __name__ == "__main__":
    main()


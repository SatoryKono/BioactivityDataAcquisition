"""Main entry point for MCP Neo4j Memory server"""

import sys
from .server import main


def main_entry():
    """Entry point for console script"""
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main_entry()

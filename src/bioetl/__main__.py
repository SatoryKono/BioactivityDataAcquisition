import sys
from pathlib import Path


def main() -> None:
    """Entry point for bioetl command."""
    src_dir = Path(__file__).parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from bioetl.interfaces.cli.app import app  # noqa: WPS433 local import

    app()


if __name__ == "__main__":
    main()

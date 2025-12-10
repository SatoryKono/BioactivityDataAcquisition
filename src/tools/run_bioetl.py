#!/usr/bin/env python
from pathlib import Path
import sys

sys.path = [p for p in sys.path if "bioactivity_data_acquisition1" not in p.lower()]

src_dir = Path(__file__).resolve().parents[1] / "bioetl"
base_src = Path(__file__).resolve().parents[1]
src_base_str = str(base_src)
if src_base_str in sys.path:
    sys.path.remove(src_base_str)
sys.path.insert(0, str(base_src))


def _main() -> None:
    from bioetl.__main__ import main as cli_main

    cli_main()


if __name__ == "__main__":
    _main()


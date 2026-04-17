#!/usr/bin/env python3
"""Package entrypoint for workbook dictionary generation."""

from __future__ import annotations

from scripts.docs.generate_chembl_matrix_dictionaries import main


if __name__ == "__main__":
    raise SystemExit(main())

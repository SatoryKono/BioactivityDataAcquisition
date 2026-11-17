"""Smoke checks for the offline IUPHAR acceptance CLI entrypoint."""

from __future__ import annotations

import pytest

from scripts.engineering.qa.iuphar_target_acceptance import main

pytestmark = pytest.mark.unit


def test_iuphar_target_acceptance_help_imports_load_profile() -> None:
    with pytest.raises(SystemExit) as exited:
        main(["--help"])
    assert exited.value.code == 0

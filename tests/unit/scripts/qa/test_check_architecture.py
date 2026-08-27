"""Unit coverage for focused architecture check helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.check_architecture import (
    check_composition_contracts_isolation,
)

pytestmark = pytest.mark.unit


def _contracts_dir(base_path: Path) -> Path:
    return base_path / "src" / "bioetl" / "composition" / "contracts"


def test_composition_contracts_isolation_allows_contract_and_domain_imports(
    tmp_path: Path,
) -> None:
    contracts_dir = _contracts_dir(tmp_path)
    contracts_dir.mkdir(parents=True)
    (contracts_dir / "allowed.py").write_text(
        "import bioetl.composition.contracts\n"
        "from bioetl.composition.contracts.models import Contract\n"
        "from bioetl.domain import models\n",
        encoding="utf-8",
    )

    assert check_composition_contracts_isolation(tmp_path) == []


def test_composition_contracts_isolation_reports_each_implementation_import(
    tmp_path: Path,
) -> None:
    contracts_dir = _contracts_dir(tmp_path)
    contracts_dir.mkdir(parents=True)
    target = contracts_dir / "forbidden.py"
    target.write_text(
        "import bioetl.composition.registry\n"
        "from bioetl.composition.bootstrap import runtime\n",
        encoding="utf-8",
    )

    violations = check_composition_contracts_isolation(tmp_path)

    assert violations == [
        f"{target}: composition/contracts imports bioetl.composition.registry",
        f"{target}: composition/contracts imports bioetl.composition.bootstrap",
    ]


def test_composition_contracts_isolation_reports_syntax_errors(tmp_path: Path) -> None:
    contracts_dir = _contracts_dir(tmp_path)
    contracts_dir.mkdir(parents=True)
    target = contracts_dir / "broken.py"
    target.write_text("def broken(:\n", encoding="utf-8")

    assert check_composition_contracts_isolation(tmp_path) == [
        f"{target}: syntax error"
    ]


def test_composition_contracts_isolation_allows_missing_directory(
    tmp_path: Path,
) -> None:
    assert check_composition_contracts_isolation(tmp_path) == []

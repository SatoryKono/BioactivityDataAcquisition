"""Unit coverage for focused architecture check helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.check_architecture import (
    check_composition_contracts_isolation,
    check_domain_type_policy,
    main,
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


def _write_domain_file(root: Path, name: str, content: str) -> None:
    domain = root / "src" / "bioetl" / "domain"
    domain.mkdir(parents=True, exist_ok=True)
    (domain / name).write_text(content, encoding="utf-8")


def test_domain_type_policy_missing_layer_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert check_domain_type_policy(tmp_path) == 1
    assert "Domain layer not found" in capsys.readouterr().out


def test_domain_type_policy_flags_missing_protocol(tmp_path: Path) -> None:
    _write_domain_file(tmp_path, "ports.py", "VALUE = 1\n")

    assert check_domain_type_policy(tmp_path) == 1


def test_domain_type_policy_skips_unparseable_ports(tmp_path: Path) -> None:
    _write_domain_file(tmp_path, "ports.py", "def broken(:\n")

    assert check_domain_type_policy(tmp_path) == 0


def test_domain_type_policy_newtype_notice_does_not_fail(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_domain_file(tmp_path, "ports.py", "from typing import Protocol\n")
    _write_domain_file(tmp_path, "types.py", "Identifier = str\n")

    assert check_domain_type_policy(tmp_path) == 0
    assert "NewType" in capsys.readouterr().out


def test_domain_type_policy_warns_on_executable_any(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_domain_file(tmp_path, "ports.py", "from typing import Protocol\n")
    _write_domain_file(tmp_path, "types.py", "from typing import NewType\n")
    _write_domain_file(
        tmp_path,
        "model.py",
        "from typing import TYPE_CHECKING\n# Any\nvalue: Any\n",
    )

    assert check_domain_type_policy(tmp_path) == 0
    output = capsys.readouterr().out
    assert "model.py:3" in output
    assert "TYPE_CHECKING" not in output
    assert "# Any" not in output


def test_domain_type_policy_cli_uses_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_domain_file(tmp_path, "ports.py", "from typing import Protocol\n")
    monkeypatch.chdir(tmp_path)

    assert main(["domain-type-policy"]) == 0
    assert main(["not-a-mode"]) == 2

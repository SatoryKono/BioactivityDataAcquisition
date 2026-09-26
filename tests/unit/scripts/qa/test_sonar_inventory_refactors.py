"""Focused regression tests for Sonar-driven inventory scanner refactors."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa import report_composition_protocol_inventory as protocols
from scripts.engineering.qa import report_lazy_import_inventory as lazy_imports
from scripts.engineering.qa.report_private_import_inventory import (
    collect_external_private_imports,
)

pytestmark = pytest.mark.unit


def test_collect_lazy_imports_preserves_function_level_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    composition = tmp_path / "src" / "bioetl" / "composition"
    module = composition / "sample.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        "import bioetl.domain\n"
        "def build():\n"
        "    from bioetl.application import services\n"
        "    import bioetl.infrastructure.time\n"
        "    import pathlib\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lazy_imports, "PROJECT_ROOT", tmp_path)

    rows = lazy_imports.collect_lazy_imports(composition)

    assert [(row["function"], row["module"]) for row in rows] == [
        ("build", "bioetl.application"),
        ("build", "bioetl.infrastructure.time"),
    ]


def test_protocol_rows_preserves_direct_and_qualified_protocol_bases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = tmp_path / "src" / "bioetl" / "composition" / "contracts.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        "from typing import Protocol\n"
        "import typing\n"
        "class Direct(Protocol): ...\n"
        "class Qualified(typing.Protocol): ...\n"
        "class Concrete(object): ...\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(protocols, "PROJECT_ROOT", tmp_path)

    rows = protocols._protocol_rows(module)

    assert [row["name"] for row in rows] == ["Direct", "Qualified"]
    assert {row["path"] for row in rows} == {"src/bioetl/composition/contracts.py"}


def test_collect_external_private_imports_keeps_cross_owner_semantics(
    tmp_path: Path,
) -> None:
    src_dir = tmp_path / "src"
    owner_a = src_dir / "bioetl" / "owner_a"
    owner_b = src_dir / "bioetl" / "owner_b"
    owner_a.mkdir(parents=True)
    owner_b.mkdir(parents=True)
    (owner_a / "_private.py").write_text("VALUE = 1\n", encoding="utf-8")
    (owner_a / "consumer.py").write_text(
        "import bioetl.owner_a._private\n",
        encoding="utf-8",
    )
    (owner_b / "consumer.py").write_text(
        "import bioetl.owner_a._private\n",
        encoding="utf-8",
    )
    (owner_b / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    violations = collect_external_private_imports(src_dir)

    assert violations == {
        ("bioetl/owner_b/consumer.py", "bioetl.owner_a._private"): [1]
    }

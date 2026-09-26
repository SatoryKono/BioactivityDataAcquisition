"""Regression coverage for the schema-parity CLI repository-root contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from scripts.engineering.common.repo_paths import REPO_ROOT
from scripts.schema.validation import verify_schema_parity as parity

pytestmark = pytest.mark.unit


def test_blocking_parity_evaluates_every_configured_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []
    original = parity.check_schema_pair

    def _record(pair: parity.SchemaPair, baseline: dict[str, object]):
        seen.append(pair.name)
        return original(pair, baseline)

    monkeypatch.setattr(parity, "check_schema_pair", _record)

    blocking, _warnings = parity._run_parity_checks({})

    assert blocking == []
    assert seen == [pair.name for pair in parity.SCHEMA_PAIRS]


def test_blocking_cli_is_independent_of_current_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert parity.main(["--mode", "blocking"]) == 0


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="FileNotFoundError regex uses host separators; POSIX as_posix match is Linux/WSL",
)
def test_missing_config_error_contains_canonical_resolved_path() -> None:
    relative_path = "configs/entities/__missing__/pipeline.yaml"

    with pytest.raises(
        FileNotFoundError,
        match=re.escape(str(REPO_ROOT / relative_path)),
    ):
        parity.get_primary_keys(relative_path)

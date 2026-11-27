"""Independent contracts for the proof closeout check catalog."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml

from scripts.engineering.qa.run_local_coverage_verify import SHARDS

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]


def test_all_coverage_shards_have_one_owner():
    catalog = yaml.safe_load(
        (ROOT / "configs/quality/proof_closeout_checks.yaml").read_text()
    )
    selected = []
    for name, spec in catalog["checks"].items():
        if name.startswith("coverage-"):
            args = spec["argv"]
            selected.extend(
                args[i + 1] for i, arg in enumerate(args) if arg == "--shard"
            )
    assert Counter(selected) == Counter(s.name for s in SHARDS)
    assert "--merge-dir" in catalog["checks"]["coverage"]["argv"]


def test_catalog_architecture_check_covers_full_suite():
    catalog = yaml.safe_load(
        (ROOT / "configs/quality/proof_closeout_checks.yaml").read_text()
    )
    argv = catalog["checks"]["architecture"]["argv"]
    assert "tests/architecture" in argv
    assert "-m" not in argv[argv.index("pytest") + 1 :]
    assert "--no-cov" in argv

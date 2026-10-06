"""CI closeout consumes complete producer evidence without repeating test commands."""

from pathlib import Path
from collections import Counter

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


def test_proof_waits_for_producers_in_the_same_workflow():
    config = yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))
    for workflow in ("pr-gate", "main-coverage-closeout", "migration-coverage-closeout"):
        jobs = config["workflows"][workflow]["jobs"]
        by_name = {
            next(iter(j)): next(iter(j.values())) for j in jobs if isinstance(j, dict)
        }
        assert set(by_name["proof-closeout"]["requires"]) == {
            "arch-tests",
            "docs-governance" if workflow == "pr-gate" else "proof-docs",
            "proof-governance",
            "proof-debt",
            "proof-quality",
        }
        assert set(by_name["proof-quality"]["requires"]) == {
            "proof-coverage",
            "arch-tests",
        }
        assert by_name["proof-coverage"]["requires"] == ["proof-coverage-shards"]
    closeout = config["jobs"]["proof-closeout"]
    commands = "\n".join(
        s["run"]["command"]
        for s in closeout["steps"]
        if isinstance(s, dict) and "run" in s
    )
    assert "proof-or-stop ci assemble" in commands
    assert "pytest" not in commands
    assert "run_local_coverage_verify" not in commands
    assert "produce --check" not in commands


def test_full_architecture_and_branch_activation_are_preserved():
    config = yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))
    catalog = yaml.safe_load(
        (ROOT / "configs/quality/proof_closeout_checks.yaml").read_text()
    )
    argv = catalog["checks"]["architecture"]["argv"]
    assert "tests/architecture" in argv
    assert "-m" not in argv[argv.index("pytest") + 1 :]
    assert "--no-cov" in argv
    jobs = config["workflows"]["pr-gate"]["jobs"]
    for item in jobs:
        if isinstance(item, dict) and next(iter(item)).startswith("proof-"):
            assert set(next(iter(item.values()))["filters"]["branches"]["only"]) == set(
                catalog["branches"]
            )

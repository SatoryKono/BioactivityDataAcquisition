"""Standalone runtime scenarios; executable with an installed wheel and no pytest."""

from __future__ import annotations

import importlib.abc
import json
import sys
from pathlib import Path
from types import TracebackType


class ScriptsImportGuard(importlib.abc.MetaPathFinder):
    """Fail on every engineering import attempt, including swallowed failures."""

    def __init__(self) -> None:
        self.attempts: list[str] = []

    def find_spec(
        self, fullname: str, path: object = None, target: object = None
    ) -> None:
        if fullname == "scripts" or fullname.startswith("scripts."):
            self.attempts.append(fullname)
            raise ModuleNotFoundError(f"Forbidden runtime import: {fullname}")
        return None

    def __enter__(self) -> ScriptsImportGuard:
        assert not any(n == "scripts" or n.startswith("scripts.") for n in sys.modules)
        sys.meta_path.insert(0, self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        sys.meta_path.remove(self)
        assert not self.attempts, f"Forbidden runtime import attempts: {self.attempts}"


def run_runtime_scenarios(root: Path) -> dict[str, object]:
    """Exercise live scanning, changed inputs, allowlists, diagnostics and lazy CLI."""
    with ScriptsImportGuard() as guard:
        import bioetl
        from bioetl.composition.observability_runtime import collect_metric_inventory
        from bioetl.composition.observability_runtime import validate_metric_inventory
        from bioetl.interfaces.cli.commands.domains.diagnostics.contract_checks import (
            _check_metric_inventory,
            run_observability_contract_checks,
        )

        source = root / "src/bioetl/application/probe.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            'metrics.increment_counter("bioetl_qm07_probe_total")\n', encoding="utf-8"
        )
        config = root / "configs/quality/observability_metric_inventory_allowlist.yaml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text("allowed: {}\n", encoding="utf-8")
        first = collect_metric_inventory(root)
        assert "bioetl_qm07_probe_total" in first["runtime_without_registry"]
        source.write_text(
            'metrics.increment_counter("bioetl_qm07_changed_total")\n', encoding="utf-8"
        )
        second = collect_metric_inventory(root)
        assert "bioetl_qm07_changed_total" in second["runtime_without_registry"]
        assert "bioetl_qm07_probe_total" not in second["runtime_without_registry"]
        violations = validate_metric_inventory(second, allowlist={})
        assert "bioetl_qm07_changed_total" in violations["runtime_without_registry"]
        allowed = validate_metric_inventory(
            second,
            allowlist={"runtime_without_registry": {"bioetl_qm07_changed_total"}},
        )
        assert "runtime_without_registry" not in allowed
        metric_check = _check_metric_inventory(root)
        assert not metric_check.passed
        assert (
            "bioetl_qm07_changed_total"
            in metric_check.details["runtime_without_registry"]
        )
        report = run_observability_contract_checks(root)
        assert not report.passed
        assert len(report.checks) == 3

        import yaml

        approved: dict[str, object] = dict(violations)
        for key in (
            "runtime_cardinality_review_required",
            "declared_risky_label_review_required",
        ):
            if key in violations:
                approved[key] = [
                    {
                        "metric": name,
                        "owner": "QM-07 fixture",
                        "reason": "isolated smoke",
                        "review_date": "2099-01-01",
                    }
                    for name in violations[key]
                ]
        config.write_text(yaml.safe_dump({"allowed": approved}), encoding="utf-8")
        fixtures = {
            "grafana/prometheus-rules/bioetl_observability.yml": {"groups": []},
            "configs/quality/observability_slo_alert_contract.yaml": {
                "slo_contracts": {}
            },
            "configs/quality/mandatory_tracing_coverage.yaml": {"surfaces": {}},
        }
        for name, payload in fixtures.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        assert run_observability_contract_checks(root).passed
        source.write_text(
            'metrics.increment_counter("bioetl_qm07_unapproved_total")\n',
            encoding="utf-8",
        )
        drift = _check_metric_inventory(root)
        assert not drift.passed
        assert (
            "bioetl_qm07_unapproved_total" in drift.details["runtime_without_registry"]
        )

        from click.testing import CliRunner
        from bioetl.interfaces.cli.main import cli

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=root):
            result = runner.invoke(cli, ["diagnostics", "contract-checks", "--json"])
        assert result.exit_code == 1, (result.output, repr(result.exception))
        payload = json.loads(result.output)
        assert payload["passed"] is False
        assert len(payload["checks"]) == 3
        origins = {
            name: str(module.__file__)
            for name, module in tuple(sys.modules.items())
            if name.startswith("bioetl") and getattr(module, "__file__", None)
        }
        return {
            "bioetl_origin": str(bioetl.__file__),
            "origins": origins,
            "attempts": guard.attempts,
            "scenarios": [
                "live_inventory",
                "changed_input_drift",
                "allowlist",
                "contract_checks",
                "passing_contracts",
                "new_unapproved_drift",
                "lazy_cli",
            ],
        }


if __name__ == "__main__":
    print(json.dumps(run_runtime_scenarios(Path(sys.argv[1])), sort_keys=True))

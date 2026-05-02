"""Guardrails for observability dashboard maintenance tooling."""

from pathlib import Path


def test_legacy_fix_grafana_mutation_script_is_removed() -> None:
    """Legacy regex-based dashboard mutator must not remain in the repo."""
    assert not Path(
        "scripts/ops/observability/grafana/fix_grafana_dashboards.py"
    ).exists(), "Legacy fix_grafana_dashboards.py script must be removed"


def test_scripts_ops_cli_does_not_expose_legacy_fix_grafana_command() -> None:
    """scripts.ops must not expose the removed mutable Grafana rewrite entrypoint."""
    content = Path("scripts/ops/__main__.py").read_text(encoding="utf-8")

    assert "fix-grafana" not in content
    assert "fix_grafana_dashboards.py" not in content


def test_observability_dashboard_scripts_do_not_write_dashboard_json() -> None:
    """Observability dashboard tooling must stay validation/render-only."""
    grafana_dir = Path("scripts/ops/observability/grafana")
    offenders: list[str] = []

    for script in sorted(grafana_dir.glob("*.py")):
        content = script.read_text(encoding="utf-8")
        if "write_text(" in content and "dashboards" in content:
            offenders.append(str(script))

    assert not offenders, (
        "Observability dashboard tooling must not mutate shipped dashboard JSON:\n"
        + "\n".join(offenders)
    )

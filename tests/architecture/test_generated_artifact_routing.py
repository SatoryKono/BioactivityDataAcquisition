# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guard for generated artifact output routing."""

from __future__ import annotations

import pytest

from pathlib import Path
from typing import Any

import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
ROUTING_PATH = ROOT / "configs" / "quality" / "generated_artifact_routing.yaml"
FORBIDDEN_ROOT_OUTPUT_SUFFIXES = (".md", ".txt", ".json", ".xml", ".csv", ".zip")


def _load_routing() -> dict[str, Any]:
    payload = yaml.safe_load(ROUTING_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "generated artifact routing must be a mapping"
    return payload


def _allowed_output_roots(payload: dict[str, Any]) -> tuple[str, ...]:
    allowed_roots = payload.get("allowed_output_roots") or {}
    assert isinstance(allowed_roots, dict), "allowed_output_roots must be a mapping"

    flattened_roots: list[str] = []
    for roots in allowed_roots.values():
        assert isinstance(roots, list), "allowed output roots must be lists"
        flattened_roots.extend(root for root in roots if isinstance(root, str))

    return tuple(flattened_roots)


def _is_safe_output_path(
    path: str,
    allowed_roots: tuple[str, ...],
    forbidden_roots: tuple[str, ...],
) -> bool:
    if not path or ".." in Path(path).parts:
        return False
    if not any(
        path.startswith(root) if root.endswith(("/", "-")) else path == root
        for root in allowed_roots
    ):
        return False
    if "/" not in path and path.endswith(FORBIDDEN_ROOT_OUTPUT_SUFFIXES):
        return False
    return not path.startswith(forbidden_roots)


def test_generated_artifact_routing_inventory_is_valid() -> None:
    """Generated artifact routing entries must point to reviewed destinations."""
    payload = _load_routing()

    assert payload["schema_version"] == 1
    routes = payload.get("routes")
    assert isinstance(routes, list) and routes, "routes must be a non-empty list"
    allowed_roots = _allowed_output_roots(payload)
    assert allowed_roots, "allowed_output_roots must declare reviewed destinations"
    forbidden_roots = tuple(payload.get("forbidden_output_roots") or ())
    assert forbidden_roots, "forbidden_output_roots must be declared"

    route_ids: set[str] = set()
    for route in routes:
        assert isinstance(route, dict), "each route must be a mapping"
        route_id = route.get("id")
        assert isinstance(route_id, str) and route_id, "route id is required"
        assert route_id not in route_ids, f"duplicate route id: {route_id}"
        route_ids.add(route_id)

        generator = route.get("generator")
        assert isinstance(generator, str) and generator, (
            f"{route_id}: generator required"
        )
        # Skip generator existence check for fallback routes with non-file generators
        # (e.g., "multiple governed docs and quality generators", "manual closeout",
        # "docs API reference generation workflow", or combined generators with " and ")
        if not (
            "/" not in generator
            or generator.startswith(("multiple", "manual", "docs"))
            or " and " in generator
        ):
            assert (ROOT / generator).exists(), f"{route_id}: generator does not exist"

        outputs = route.get("outputs")
        assert isinstance(outputs, list) and outputs, f"{route_id}: outputs required"
        for output in outputs:
            assert isinstance(output, str), f"{route_id}: output must be a string"
            assert _is_safe_output_path(output, allowed_roots, forbidden_roots), (
                f"{route_id}: unsafe generated artifact output path: {output}"
            )


@pytest.mark.parametrize(
    "unsafe_path",
    (
        "",
        "../reports/generated.json",
        "reports/../generated.json",
        "reports/..",
        "output/generated.json",
        "generated.json",
        "docs/04-reference/config_comparison_matrix.csv.bak",
    ),
)
def test_generated_artifact_routing_rejects_unsafe_paths(
    unsafe_path: str,
) -> None:
    """Traversal, forbidden roots, and root-level outputs must fail closed."""
    payload = _load_routing()

    assert not _is_safe_output_path(
        unsafe_path,
        _allowed_output_roots(payload),
        tuple(payload["forbidden_output_roots"]),
    )


def test_generated_artifact_routing_rejects_forbidden_allowed_overlap() -> None:
    """Forbidden roots take precedence over an overlapping allowed prefix."""
    assert not _is_safe_output_path(
        "output/generated.json",
        ("output/",),
        ("output/",),
    )


def test_generated_artifact_routing_covers_core_generators() -> None:
    """Core maintained generators must remain represented in the routing registry."""
    payload = _load_routing()
    generators = {route["generator"] for route in payload["routes"]}

    expected_generators = {
        "scripts/engineering/common/file_merger.py",
        "scripts/docs/build/generate_docs_export.py",
        "scripts/schema/generation/generate_schema_artifacts.py",
        "scripts/engineering/ci/validate_contract_identity.py",
        "scripts/engineering/ci/validate_contract_registry.py",
        "scripts/engineering/ci/validate_registry_dq_refs.py",
        "scripts/engineering/ci/validate_schema_classifier_gate.py",
        "scripts/engineering/qa/report_domain_io_taint_inventory.py",
        "scripts/engineering/qa/report_flaky_test_burndown_review.py",
    }

    assert expected_generators.issubset(generators), (
        "Generated artifact routing registry is missing core generators: "
        f"{sorted(expected_generators - generators)}"
    )


def test_generated_artifact_routing_classifies_docs_helper_surfaces() -> None:
    """Generated docs helper surfaces must stay explicitly classified."""
    payload = _load_routing()
    allowed_roots = set(_allowed_output_roots(payload))

    assert "docs/site/" in allowed_roots
    assert "docs/exports/" in allowed_roots

    docs_export_route = next(
        route
        for route in payload["routes"]
        if route.get("id") == "docs-export-merged-markdown"
    )
    assert docs_export_route["commit_policy"] == "ignored_local_export"
    assert (
        "docs/exports/full-documentation-no-plans-reports-skills.merged.md"
        in (docs_export_route["outputs"])
    )


def test_contract_governance_workflow_uploads_diagnostics_from_reports_quality() -> (
    None
):
    """Contract governance diagnostics must not be uploaded from repository root."""
    workflow = (
        ROOT / ".github" / "workflows" / "contract-governance-fast-check.yml"
    ).read_text(encoding="utf-8")

    root_diagnostics = {
        "contract-identity-diagnostics.json",
        "contract-schema-classifier-diagnostics.json",
        "contract-registry-dq-diagnostics.json",
    }
    for filename in root_diagnostics:
        assert f"reports/quality/{filename}" in workflow
        assert f"\n            {filename}" not in workflow


def test_provider_contract_drift_workflow_uploads_report_from_reports_quality() -> None:
    """Provider contract drift report must not be uploaded from repository root."""
    workflow = (
        ROOT / ".github" / "workflows" / "provider-contract-drift.yml"
    ).read_text(encoding="utf-8")

    assert "reports/quality/provider-contract-drift-report.json" in workflow
    assert "--output provider-contract-drift-report.json" not in workflow
    assert "\n          path: provider-contract-drift-report.json" not in workflow


def test_coverage_xml_defaults_route_under_reports_coverage() -> None:
    """Coverage XML defaults must avoid repository-root coverage.xml."""
    resilient_runner = (
        ROOT / "scripts" / "engineering" / "ci" / "run_pytest_resilient.py"
    ).read_text(encoding="utf-8")
    sharded_runner = (
        ROOT / "scripts" / "engineering" / "dev" / "run_pytest_sharded.sh"
    ).read_text(encoding="utf-8")
    quality_gate = (
        ROOT / "scripts" / "engineering" / "ci" / "quality_integral_gate.py"
    ).read_text(encoding="utf-8")

    assert "xml:reports/coverage/coverage.xml" in resilient_runner
    assert "xml:coverage.xml" not in resilient_runner
    assert 'DEFAULT_COVERAGE_REPORT_DIR="$REPO_ROOT/reports/coverage"' in sharded_runner
    assert 'coverage xml -o "$COVERAGE_REPORT_DIR/coverage.xml"' in sharded_runner
    assert "coverage xml -o coverage.xml" not in sharded_runner
    assert 'default="reports/coverage/coverage.xml"' in quality_gate
    assert 'default="coverage.xml"' not in quality_gate


def test_html_coverage_defaults_route_under_reports_coverage() -> None:
    """HTML coverage defaults must avoid repository-root htmlcov/."""
    dev_runner = (ROOT / "scripts" / "engineering" / "dev" / "run_tests.py").read_text(
        encoding="utf-8"
    )
    sharded_runner = (
        ROOT / "scripts" / "engineering" / "dev" / "run_pytest_sharded.sh"
    ).read_text(encoding="utf-8")
    coverage_guide = (
        ROOT / "docs" / "03-guides" / "coverage-configuration.md"
    ).read_text(encoding="utf-8")
    testing_guide = (ROOT / "docs" / "03-guides" / "testing.md").read_text(
        encoding="utf-8"
    )
    payload = _load_routing()
    routed_outputs = {
        output for route in payload["routes"] for output in route.get("outputs", [])
    }

    assert "--cov-report=html:reports/coverage/htmlcov" in dev_runner
    assert '--cov-report=html",' not in dev_runner
    assert 'coverage html -d "$COVERAGE_REPORT_DIR/htmlcov"' in sharded_runner
    assert "coverage html -d htmlcov" not in sharded_runner
    assert "HTML report: reports/coverage/htmlcov/index.html" in dev_runner
    assert "HTML report: htmlcov/index.html" not in dev_runner
    assert "coverage html -d reports/coverage/htmlcov" in coverage_guide
    assert "coverage html -d htmlcov" not in coverage_guide
    assert "reports/coverage/htmlcov/index.html" in testing_guide
    assert "reports/coverage/htmlcov" in testing_guide
    assert "reports/coverage/htmlcov/" in routed_outputs


def test_grafana_screenshot_defaults_route_under_reports() -> None:
    """Grafana screenshot rerenders must avoid root output/."""
    script = (
        ROOT
        / "scripts"
        / "ops"
        / "observability"
        / "grafana"
        / "rerender_grafana_screenshots.py"
    ).read_text(encoding="utf-8")

    assert 'Path("reports/observability/grafana/screenshots")' in script
    assert 'Path("output/playwright")' not in script


def test_grafana_live_audit_report_routes_under_reports() -> None:
    """Grafana live datasource audits must write under reports/observability."""
    script = (
        ROOT
        / "scripts"
        / "ops"
        / "observability"
        / "grafana"
        / "audit_live_grafana_panels.py"
    ).read_text(encoding="utf-8")
    routing = _load_routing()
    routed_outputs = {
        output for route in routing["routes"] for output in route.get("outputs", [])
    }

    assert 'Path("reports/observability/grafana/live-panel-audit.json")' in script
    assert "reports/observability/grafana/live-panel-audit.json" in routed_outputs


def test_grafana_panel_fill_report_routes_under_reports() -> None:
    """Panel-fill error reports must write under reports/observability."""
    script = (
        ROOT
        / "scripts"
        / "ops"
        / "observability"
        / "grafana"
        / "check_dashboard_panel_fill.py"
    ).read_text(encoding="utf-8")
    routing = _load_routing()
    routed_outputs = {
        output for route in routing["routes"] for output in route.get("outputs", [])
    }

    assert 'Path("reports/observability/grafana/panel-fill-errors.json")' in script
    assert "reports/observability/grafana/panel-fill-errors.json" in routed_outputs


def test_runtime_log_default_routes_under_reports_logs() -> None:
    """Default local log files must avoid root logs/."""
    script = (
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "observability"
        / "logging_config.py"
    ).read_text(encoding="utf-8")

    assert 'Path("reports") / "logs" / "bioetl.log"' in script
    assert 'Path("logs") / "bioetl.log"' not in script


def test_docker_security_baseline_routes_under_reports_security() -> None:
    """Docker security outputs must remain ignored CI evidence outside root."""
    workflow = (ROOT / ".github" / "workflows" / "docker.yml").read_text(
        encoding="utf-8"
    )
    ci_fix_script = (
        ROOT / "scripts" / "engineering" / "ci" / "apply_ci_fixes.py"
    ).read_text(encoding="utf-8")
    payload = _load_routing()
    routed_outputs = {
        output for route in payload["routes"] for output in route.get("outputs", [])
    }

    assert "reports/security/trivy-results.sarif" in workflow
    assert "reports/security/trivy-results.sarif" in ci_fix_script
    assert "mkdir -p reports/security" in workflow
    assert "mkdir -p reports/security" in ci_fix_script
    assert "output: 'trivy-results.sarif'" not in workflow
    assert "sarif_file: 'trivy-results.sarif'" not in workflow
    assert "output: 'trivy-results.sarif'" not in ci_fix_script
    assert "sarif_file: 'trivy-results.sarif'" not in ci_fix_script
    expected_outputs = {
        "reports/security/trivy-results.sarif",
        "reports/security/trivy-results.json",
        "reports/security/trivy-base-results.json",
        "reports/security/trivy-alerts.csv",
        "reports/security/trivy-version.json",
        "reports/security/github-trivy-alerts.json",
        "reports/security/bioetl.spdx.json",
        "reports/security/bioetl-image-provenance.txt",
        "reports/security/bioetl-image-id.txt",
        "reports/security/bioetl-pip-freeze.txt",
        "reports/security/baseline.sha256",
        "reports/security/bioetl-scanned-image.tar.zst",
    }
    assert expected_outputs <= routed_outputs
    assert all(path in workflow for path in expected_outputs)


def test_contract_junit_xml_routes_under_reports_junit() -> None:
    """Contract JUnit XML artifacts must avoid repository root."""
    port_contracts_workflow = (
        ROOT / ".github" / "workflows" / "port-contracts.yml"
    ).read_text(encoding="utf-8")
    contract_tests_workflow = (
        ROOT / ".github" / "workflows" / "contract-tests.yml"
    ).read_text(encoding="utf-8")
    payload = _load_routing()
    routed_outputs = {
        output for route in payload["routes"] for output in route.get("outputs", [])
    }

    expected_outputs = {
        "reports/junit/port-contracts-results.xml",
        "reports/junit/hypothesis-contracts-results.xml",
        "reports/junit/contract-results.xml",
    }
    for output in expected_outputs:
        assert output in routed_outputs

    assert "mkdir -p reports/junit" in port_contracts_workflow
    assert "mkdir -p reports/junit" in contract_tests_workflow
    assert (
        "--junit-xml=reports/junit/port-contracts-results.xml"
        in port_contracts_workflow
    )
    assert (
        "--junit-xml=reports/junit/hypothesis-contracts-results.xml"
        in port_contracts_workflow
    )
    assert "--junit-xml=reports/junit/contract-results.xml" in contract_tests_workflow
    assert "path: reports/junit/port-contracts-results.xml" in port_contracts_workflow
    assert (
        "path: reports/junit/hypothesis-contracts-results.xml"
        in port_contracts_workflow
    )
    assert "path: reports/junit/contract-results.xml" in contract_tests_workflow

    assert "--junit-xml=port-contracts-results.xml" not in port_contracts_workflow
    assert "--junit-xml=hypothesis-contracts-results.xml" not in port_contracts_workflow
    assert "--junit-xml=contract-results.xml" not in contract_tests_workflow
    assert "path: port-contracts-results.xml" not in port_contracts_workflow
    assert "path: hypothesis-contracts-results.xml" not in port_contracts_workflow
    assert "path: contract-results.xml" not in contract_tests_workflow


def test_architecture_debt_task_outputs_route_under_reports_quality() -> None:
    """Architecture debt task generators must avoid repository root outputs."""
    task_generation = (
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "quality"
        / "architecture_debt_task_generation.py"
    ).read_text(encoding="utf-8")
    debt_reduction = (
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "quality"
        / "architecture_debt_reduction.py"
    ).read_text(encoding="utf-8")
    generator_script = (
        ROOT / "scripts" / "engineering" / "qa" / "generate_architecture_debt_tasks.py"
    ).read_text(encoding="utf-8")
    reduction_script = (
        ROOT / "scripts" / "engineering" / "qa" / "reduce_architecture_debt.py"
    ).read_text(encoding="utf-8")
    payload = _load_routing()
    routed_outputs = {
        output for route in payload["routes"] for output in route.get("outputs", [])
    }

    assert 'project_root / "reports" / "quality" / file_name' in task_generation
    assert "reports/quality/tasks_architecture_metric_exemptions_" in generator_script
    assert "reports/quality, with legacy root fallback" in reduction_script
    assert '(root / "reports" / "quality").glob(' in debt_reduction
    assert (
        "reports/quality/tasks_architecture_metric_exemptions_YYYY-MM-DD-HH-MM.json"
        in routed_outputs
    )
    assert (
        "reports/quality/architecture_debt_execution_plan_YYYY-MM-DD-HH-MM.json"
        in routed_outputs
    )

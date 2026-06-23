"""Architecture tests for documentation drift guardrails."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
from types import ModuleType

import pytest


pytestmark = pytest.mark.architecture


def _load_module() -> ModuleType:
    module = importlib.import_module("scripts.docs.checks.check_links")
    return importlib.reload(module)


@pytest.fixture(scope="module")
def check_doc_links_module() -> ModuleType:
    """Load the docs guardrail module once per test module."""
    return _load_module()


def test_iter_python_fence_lines_extracts_python_blocks_only(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    lines = [
        "```bash",
        "python scripts/check_doc_links.py",
        "```",
        "```python",
        "value = foo_bar()",
        "```",
    ]

    extracted = module._iter_python_fence_lines(lines)

    assert extracted == [(5, "value = foo_bar()")]


def test_python_snippet_guardrails_detect_known_invalid_tokens(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    lines = [
        "```python",
        "compound = pcp.Compound.from-cid(cid)",
        "compounds = pcp.get-compounds(cid_list, namespace='cid')",
        "return await self._run-in-executor(pcp.get_compounds, cids, namespace='cid')",
        "```",
    ]

    violations = module._check_python_snippet_drift(lines)
    rule_names = {name for _, name, _ in violations}

    assert "python_invalid_from_cid_token" in rule_names
    assert "python_invalid_get_compounds_token" in rule_names
    assert "python_invalid_run_in_executor_token" in rule_names


def test_python_snippet_guardrails_detect_renamed_files(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    lines = [
        "```python",
        "with open('src/bioetl/infrastructure/config-loader.py', encoding='utf-8') as f:",
        "    _ = f.read()",
        "```",
    ]

    violations = module._check_python_snippet_drift(lines)
    rule_names = {name for _, name, _ in violations}

    assert "python_renamed_file_token" in rule_names


def test_python_snippet_guardrails_allow_explicit_legacy_marker(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    lines = [
        "```python",
        "compound = pcp.Compound.from-cid(cid)  # doc-lint: allow-legacy",
        "```",
    ]

    violations = module._check_python_snippet_drift(lines)

    assert violations == []


def test_path_contracts_allow_canonical_requirements_link(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    source = module.DOCS_DIR / "00-project" / "RULES.md"
    lines = ["See [Requirements](../01-requirements/REQUIREMENTS.md)."]

    violations = module._check_path_contracts_for_file(source, lines)

    assert violations == []


def test_path_contracts_detect_noncanonical_requirements_link(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    source = module.DOCS_DIR / "00-project" / "RULES.md"
    lines = ["See [Requirements](REQUIREMENTS.md)."]

    violations = module._check_path_contracts_for_file(source, lines)
    rule_names = {name for _, name, _ in violations}

    assert "requirements_path_contract" in rule_names


def test_path_contracts_detect_noncanonical_governance_link(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    source = module.DOCS_DIR / "00-project" / "RULES.md"
    lines = ["Legacy link: [Policy](../99-archive/governance/policy.md)."]

    violations = module._check_path_contracts_for_file(source, lines)
    rule_names = {name for _, name, _ in violations}

    assert "governance_path_contract" in rule_names


def test_runbook_governance_accepts_rollup_rollback_recovery_heading(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    violations: list[tuple[Path, str]] = []
    headings = {section.casefold() for section in module.REQUIRED_RUNBOOK_SECTIONS}

    module._append_runbook_section_violations(
        violations, Path("docs/05-operations/runbooks/example.md"), headings
    )

    assert violations == []


def test_drift_rules_include_legacy_run_flag_and_path_tokens(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    rule_names = {rule.name for rule in module.DRIFT_RULES}

    assert "legacy_run_type_flag" in rule_names
    assert "legacy_system_meta_field_token" in rule_names
    assert "legacy_lineage_log_token" in rule_names
    assert "legacy_docs_pipelines_path" in rule_names
    assert "legacy_quarantine_mark_as_reprocessed_token" in rule_names


def test_legacy_system_meta_field_rule_ignores_cli_double_dash_flags(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    rule = next(
        candidate
        for candidate in module.DRIFT_RULES
        if candidate.name == "legacy_system_meta_field_token"
    )

    assert rule.pattern.search("legacy token `-run-id` should fail")
    assert rule.pattern.search('legacy token "-ingestion-ts" should fail')
    assert not rule.pattern.search("allowed CLI flag --run-type")
    assert not rule.pattern.search("allowed CLI flag --source")


@pytest.mark.slow
def test_guardrails_pass_for_current_nav_docs(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module

    violations = module.check_legacy_paths_in_nav_docs()

    assert not violations, (
        "Documentation drift guardrails found violations in active nav docs:\n"
        + "\n".join(
            f"{path}:{line_no} [{rule}] -> {value}"
            for path, line_no, rule, value in violations[:20]
        )
    )


def test_not_in_nav_baseline_file_exists(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module

    baseline_file = module.NOT_IN_NAV_BASELINE_FILE
    assert baseline_file.exists(), (
        "Missing not-in-nav baseline file: "
        f"{baseline_file.relative_to(module.PROJECT_ROOT)}"
    )


def test_not_in_nav_growth_guard_passes_for_current_repo(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module

    current_count, baseline_count, added, _removed, baseline_exists = (
        module.check_not_in_nav_growth()
    )

    assert baseline_exists, "not-in-nav baseline file is missing"
    assert current_count <= baseline_count, (
        "Detected growth of docs outside mkdocs nav baseline: "
        f"current={current_count}, baseline={baseline_count}, "
        f"added_sample={added[:10]}"
    )


def test_not_in_nav_growth_excludes_reports_prefixes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    baseline_file = tmp_path / "not_in_nav_baseline.txt"
    baseline_file.write_text(
        "\n".join(
            [
                "reports/evidence/example/SUMMARY.md",
                "plans/example-plan.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "get_not_in_nav_docs",
        lambda root=module.DOCS_DIR: [
            "reports/evidence/example/SUMMARY.md",
            "plans/example-plan.md",
        ],
    )

    current_count, baseline_count, added, removed, baseline_exists = (
        module.check_not_in_nav_growth(baseline_file=baseline_file)
    )

    assert baseline_exists is True
    assert current_count == 1
    assert baseline_count == 1
    assert added == []
    assert removed == []


def test_control_plane_contract_governance_detects_compatibility_facade_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    contract_doc = tmp_path / "run-manifest-ledger.md"
    contract_doc.write_text(
        """---
Version: 1.1.0
Class: published
Last verified: "2026-04-13"
---

# Run Manifest and Run Ledger Contract
## Purpose
## Storage layout
## Rollout flags
## Invariants
## Inspection surface

- `src/bioetl/application/services/control_plane/run_manifest_service.py`
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "_control_plane_contract_spec_files",
        lambda: [contract_doc],
    )

    violations = module.check_control_plane_contract_governance()

    assert any(
        "compatibility facade path" in message and "run_manifest_service.py" in message
        for _path, message in violations
    )


def test_collect_link_scan_files_keeps_nav_docs_without_prechecking_existence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    tree_doc = tmp_path / "tree.md"
    nav_doc = tmp_path / "nav.md"
    missing_nav_doc = tmp_path / "missing-nav.md"
    tree_doc.write_text("# Tree\n", encoding="utf-8")
    nav_doc.write_text("# Nav\n", encoding="utf-8")

    monkeypatch.setattr(module, "_iter_markdown_files", lambda root: [tree_doc])
    monkeypatch.setattr(module, "_load_nav_docs", lambda: [nav_doc, missing_nav_doc])

    collected = module._collect_link_scan_files(tmp_path)

    assert collected == [missing_nav_doc, nav_doc, tree_doc]


def test_has_any_heading_accepts_cli_inspection_alias(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module
    headings = {"purpose", "cli inspection", "invariants"}

    assert module._has_any_heading(headings, "Inspection Surface", "CLI Inspection")


def test_control_plane_contract_files_include_run_manifest_ledger(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module

    files = module._control_plane_contract_spec_files()

    assert any(path.name == "run-manifest-ledger.md" for path in files)


def test_control_plane_contract_governance_passes_current_repo(
    check_doc_links_module: ModuleType,
) -> None:
    module = check_doc_links_module

    violations = module.check_control_plane_contract_governance()

    assert violations == []


def test_load_nav_docs_ignores_exclude_docs_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    repo_root = Path(tempfile.gettempdir()) / "example-repo"
    docs_dir = repo_root / "docs"
    mkdocs_file = repo_root / "mkdocs.yml"
    mkdocs_payload = """
site_name: Example
exclude_docs: |
  D-01 Governance & Style Guide документации BioETL.md
nav:
  - Home: 00-project/index.md
  - Governance:
      - D-01: 00-project/governance/01-documentation-governance-style-guide.md
"""
    monkeypatch.setattr(
        module,
        "PROJECT_ROOT",
        repo_root,
    )
    monkeypatch.setattr(
        module,
        "DOCS_DIR",
        docs_dir,
    )
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda self, encoding="utf-8", errors="replace": (
            mkdocs_payload if self == mkdocs_file else ""
        ),
    )
    monkeypatch.setattr(Path, "exists", lambda self: self == mkdocs_file)

    nav_docs = module._load_nav_docs()

    assert docs_dir / "BioETL.md" not in nav_docs
    assert (
        docs_dir / "00-project/governance/01-documentation-governance-style-guide.md"
        in nav_docs
    )


def test_not_in_nav_growth_detects_increase_against_reduced_baseline(
    tmp_path: Path,
) -> None:
    module = _load_module()

    current_not_in_nav = sorted(
        module._filter_not_in_nav_growth_scope(set(module.get_not_in_nav_docs()))
    )
    assert current_not_in_nav, "Expected non-empty not-in-nav set for this test"

    reduced_baseline = tmp_path / "not_in_nav_baseline.txt"
    reduced_baseline.write_text(
        "\n".join(current_not_in_nav[: max(1, len(current_not_in_nav) // 4)]) + "\n",
        encoding="utf-8",
    )

    current_count, baseline_count, added, _removed, baseline_exists = (
        module.check_not_in_nav_growth(baseline_file=reduced_baseline)
    )

    assert baseline_exists is True
    assert current_count > baseline_count
    assert added, "Expected newly-added not-in-nav docs against reduced baseline"


def test_gold_contract_index_matches_exports() -> None:
    module = _load_module()

    missing_in_doc, extra_in_doc = module.check_gold_contract_index()

    assert missing_in_doc == []
    assert extra_in_doc == []


def test_github_actions_workflow_inventory_matches_live_repo() -> None:
    module = _load_module()

    missing_in_doc, extra_in_doc = module.check_github_actions_workflow_inventory()

    assert missing_in_doc == []
    assert extra_in_doc == []


def test_workflow_inventory_keeps_scheduled_only_workflows_out_of_pr_push_section(
) -> None:
    inventory_doc = Path("docs/04-reference/github-actions-workflows.md").read_text(
        encoding="utf-8"
    )
    pr_section = inventory_doc.split("### PR / push verification workflows", maxsplit=1)[
        1
    ].split("### Scheduled / periodic workflows", maxsplit=1)[0]
    scheduled_section = inventory_doc.split(
        "### Scheduled / periodic workflows", maxsplit=1
    )[1].split("### Release, packaging, and repository automation", maxsplit=1)[0]

    for workflow_file in ("`architecture.yml`", "`pr-hygiene.yml`"):
        assert workflow_file not in pr_section
        assert workflow_file in scheduled_section


def test_chembl_provider_overview_matches_active_config_inventory() -> None:
    module = _load_module()

    missing_in_readme, extra_in_readme = module.check_chembl_provider_overview()

    assert missing_in_readme == []
    assert extra_in_readme == []

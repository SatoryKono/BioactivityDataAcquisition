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
from __future__ import annotations

import pytest

from pathlib import Path

from scripts.engineering.qa.import_graph_inventory import (
    collect_bioetl_importers,
    collect_zero_import_bioetl_modules,
)
from scripts.engineering.qa.report_compatibility_importer_census import (
    REMOVED_COMPATIBILITY_SURFACES,
    build_compatibility_importer_census,
    validate_compatibility_metadata_consistency,
)
from scripts.engineering.qa.report_dead_code_inventory import build_dead_code_inventory


pytestmark = pytest.mark.unit


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_import_graph_counts_type_stub_imports_as_static_importers(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "src/bioetl/domain/ports/__init__.py", "")
    _write(
        tmp_path / "src/bioetl/domain/ports/__init__.pyi",
        "from bioetl.domain.ports.sample import SamplePort as SamplePort\n",
    )
    _write(
        tmp_path / "src/bioetl/domain/ports/sample.py",
        "class SamplePort:\n    pass\n",
    )

    importers = collect_bioetl_importers(tmp_path)
    assert importers["bioetl.domain.ports.sample"]["src"] == (
        "src/bioetl/domain/ports/__init__.pyi",
    )
    zero_import_paths = {
        str(row["path"]) for row in collect_zero_import_bioetl_modules(tmp_path)
    }
    assert "src/bioetl/domain/ports/sample.py" not in zero_import_paths


def _write_compatibility_metadata_fixture(tmp_path: Path) -> dict[str, object]:
    _write(
        tmp_path / "configs/quality/compatibility_facade_inventory.yaml",
        """version: 1
policy_scope: compatibility_facades
transition_debt: []
retained_entrypoints:
  - path: src/bioetl/composition/health_api.py
    compatibility_role: Public health facade.
    canonical_target: bioetl.composition.health_api
    status: public-entrypoint
    owner: bioetl.composition
    introduced_in: 2026-05 public export review
    review_date: '2026-09-30'
    external_breaking_change_required: true
    internal_callers_zero: true
    allowed_call_sites: No first-party imports.
    migration_path: Use the owner module.
    exit_criteria: First-party imports stay at zero.
""",
    )
    _write(
        tmp_path / "docs/02-architecture/07-compatibility-facade-inventory.md",
        "| Path | Compatibility role | Canonical target | Status | Owner | "
        "Introduced in | Allowed call sites | Review date | Migration path | "
        "Exit criteria |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| `src/bioetl/composition/health_api.py` | Public health facade. | "
        "`bioetl.composition.health_api` | `public-entrypoint` | "
        "`bioetl.composition` | `2026-05 public export review` | "
        "No first-party imports. | `2026-09-30` | Use the owner module. | "
        "First-party imports stay at zero. |\n",
    )
    return {
        "retained_entrypoints": [
            {
                "path": "src/bioetl/composition/health_api.py",
                "canonical_target": "bioetl.composition.health_api",
                "status": "public-entrypoint",
                "owner": "bioetl.composition",
                "external_breaking_change_required": True,
                "internal_callers_zero": True,
                "usage_classification": "stable_public_api_zero_first_party_src",
                "src_importers": [],
                "src_importer_count": 0,
            }
        ]
    }


def test_compatibility_metadata_consistency_accepts_aligned_artifacts(
    tmp_path: Path,
) -> None:
    census_payload = _write_compatibility_metadata_fixture(tmp_path)

    assert (
        validate_compatibility_metadata_consistency(
            tmp_path,
            census_payload=census_payload,
        )
        == ()
    )


def test_compatibility_metadata_consistency_reports_cross_artifact_drift(
    tmp_path: Path,
) -> None:
    census_payload = _write_compatibility_metadata_fixture(tmp_path)
    inventory_doc = (
        tmp_path / "docs/02-architecture/07-compatibility-facade-inventory.md"
    )
    _write(
        inventory_doc,
        inventory_doc.read_text(encoding="utf-8").replace(
            "Public health facade.",
            "Outdated health role.",
            1,
        ),
    )
    retained_rows = census_payload["retained_entrypoints"]
    assert isinstance(retained_rows, list)
    retained_row = retained_rows[0]
    assert isinstance(retained_row, dict)
    retained_row["usage_classification"] = (
        "stable_public_api_with_reviewed_first_party_usage"
    )
    retained_row["src_importer_count"] = 1

    violations = validate_compatibility_metadata_consistency(
        tmp_path,
        census_payload=census_payload,
    )

    assert any("compatibility_role" in violation for violation in violations)
    assert any("usage_classification" in violation for violation in violations)
    assert any("is internal_callers_zero" in violation for violation in violations)


def test_build_compatibility_importer_census_counts_retained_entrypoints_and_twins(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "configs/quality/compatibility_facade_inventory.yaml",
        "\n".join(
            [
                "version: 1",
                "policy_scope: compatibility_facades",
                "transition_debt: []",
                "retained_entrypoints:",
                "  - path: src/bioetl/interfaces/cli/commands/run.py",
                "    status: public-entrypoint",
                "    canonical_target: bioetl.interfaces.cli.commands.run",
                "    owner: bioetl.interfaces.cli.commands",
                "  - path: src/bioetl/composition/health_api.py",
                "    status: public-entrypoint",
                "    canonical_target: bioetl.composition.health_api",
                "    owner: bioetl.composition",
                "    public_export_contract:",
                "      max_public_exports: 3",
                "      lazy_export_table: _PUBLIC_EXPORTS",
                "      retained_wrappers_outside_all:",
                "        - get_runtime_settings",
            ]
        )
        + "\n",
    )
    _write(tmp_path / "src/bioetl/composition/__init__.py", "")
    _write(
        tmp_path / "src/bioetl/composition/health_api.py",
        "\n".join(
            [
                "__all__ = ['HealthServerDependencies', 'get_runtime_settings', 'get_health_service']",
                "_PUBLIC_EXPORTS = {",
                "    'HealthServerDependencies': 'a',",
                "    'get_health_service': 'b',",
                "}",
                "def get_runtime_settings():",
                "    return {}",
            ]
        )
        + "\n",
    )
    _write(tmp_path / "src/bioetl/interfaces/cli/commands/__init__.py", "")
    _write(tmp_path / "src/bioetl/interfaces/cli/commands/run.py", "RUN = True\n")
    _write(tmp_path / "src/bioetl/application/core/__init__.py", "")
    _write(tmp_path / "src/bioetl/application/core/_helper.py", "VALUE = 1\n")
    _write(
        tmp_path / "src/bioetl/application/core/helper.py",
        "from bioetl.application.core._helper import VALUE\n",
    )
    _write(
        tmp_path / "src/bioetl/application/services/use_helper.py",
        "from bioetl.application.core import helper\n",
    )
    _write(
        tmp_path / "src/bioetl/application/services/use_health_api.py",
        "import bioetl.composition.health_api\n",
    )
    _write(
        tmp_path / "tests/unit/test_cli_imports.py",
        "import bioetl.interfaces.cli.commands.run\n"
        "from bioetl.application.core import helper\n",
    )
    _write(
        tmp_path / "tests/unit/test_removed_surface_imports.py",
        "import bioetl.application.services.checkpoint_compatibility_service_v2\n",
    )

    payload = build_compatibility_importer_census(tmp_path)

    assert payload["summary"]["retained_entrypoint_count"] == 2
    assert payload["summary"]["retained_public_entrypoint_burden"] == 1
    assert payload["summary"]["removed_compatibility_surface_count"] == len(
        REMOVED_COMPATIBILITY_SURFACES
    )
    assert payload["summary"]["removed_compatibility_surfaces_with_src_importers"] == 0
    assert payload["summary"]["removed_compatibility_surfaces_with_test_importers"] == 1
    assert payload["summary"]["removed_compatibility_surfaces_still_present"] == 0
    retained = payload["retained_entrypoints"][0]
    assert retained["module_name"] == "bioetl.interfaces.cli.commands.run"
    assert retained["test_importer_count"] == 1
    public_export_row = payload["retained_public_export_facades"][0]
    assert public_export_row["module_name"] == "bioetl.composition.health_api"
    assert public_export_row["public_export_count"] == 3
    assert public_export_row["duplicate_public_exports"] == []
    assert public_export_row["duplicate_lazy_export_keys"] == []
    assert public_export_row["retained_wrapper_contract"] == ["get_runtime_settings"]
    assert public_export_row["retained_wrappers_outside_all"] == [
        "get_runtime_settings"
    ]
    assert public_export_row["missing_retained_wrappers_outside_all"] == []
    assert public_export_row["unexpected_retained_wrappers_outside_all"] == []
    assert public_export_row["resolution_conflicts"] == {}
    assert public_export_row["src_importer_count"] == 1
    removed_rows = {
        row["module_name"]: row for row in payload["removed_compatibility_surfaces"]
    }
    assert removed_rows[
        "bioetl.application.services.checkpoint_compatibility_service_v2"
    ]["test_importers"] == ["tests/unit/test_removed_surface_imports.py"]
    assert (
        removed_rows[
            "bioetl.infrastructure.storage.silver.operations.metadata_sidecar_adapter"
        ]["src_importer_count"]
        == 0
    )
    twin_rows = payload["twin_pairs"]
    assert len(twin_rows) == 1
    twin = twin_rows[0]
    assert twin["public_module"] == "bioetl.application.core.helper"
    assert twin["public_src_importer_count"] == 1
    assert twin["private_src_importer_count"] == 1


def test_build_compatibility_importer_census_supports_relative_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path / "configs/quality/compatibility_facade_inventory.yaml",
        "\n".join(
            [
                "version: 1",
                "policy_scope: compatibility_facades",
                "transition_debt: []",
                "retained_entrypoints:",
                "  - path: src/bioetl/application/core/helper.py",
                "    status: public-entrypoint",
                "    canonical_target: bioetl.application.core.helper",
                "    owner: bioetl.application.core",
            ]
        )
        + "\n",
    )
    _write(tmp_path / "src/bioetl/application/core/__init__.py", "")
    _write(tmp_path / "src/bioetl/application/core/_helper.py", "VALUE = 1\n")
    _write(
        tmp_path / "src/bioetl/application/core/helper.py",
        "from bioetl.application.core._helper import VALUE\n",
    )
    _write(
        tmp_path / "src/bioetl/application/services/use_helper.py",
        "from bioetl.application.core import helper\n",
    )

    monkeypatch.chdir(tmp_path)

    payload = build_compatibility_importer_census(Path("."))

    assert payload["summary"]["twin_pair_count"] == 1
    assert (
        payload["twin_pairs"][0]["private_module"] == "bioetl.application.core._helper"
    )
    assert payload["twin_pairs"][0]["public_module"] == "bioetl.application.core.helper"


def test_build_dead_code_inventory_flags_zero_import_candidates(tmp_path: Path) -> None:
    _write(
        tmp_path / "configs/quality/compatibility_facade_inventory.yaml",
        "\n".join(
            [
                "version: 1",
                "policy_scope: compatibility_facades",
                "transition_debt: []",
                "retained_entrypoints: []",
            ]
        )
        + "\n",
    )
    _write(
        tmp_path / "configs/quality/retirement_candidate_triage.yaml",
        "\n".join(
            [
                "schema_version: 1",
                "policy:",
                "  review_cycle_days: 90",
                "repo_wide_zero_import_review:",
                "  linked_issue: '#4541'",
                "  mode: fail-fast-zero-untriaged",
                "  max_untriaged_zero_import_candidates: 0",
                "  last_reviewed: '2026-05-22'",
                "  next_review_by: '2026-08-20'",
                "repo_wide_zero_import_classification:",
                "  linked_issue: '#4541'",
                "  review_date: '2026-05-22'",
                "  allowed_dispositions:",
                "    - retain_canonical_owner_module",
                "  entries:",
                "    - module_path: src/bioetl/application/unused.py",
                "      module_name: bioetl.application.unused",
                "      disposition: retain_canonical_owner_module",
                "      reviewed_on: '2026-05-22'",
                "      review_by: '2026-08-20'",
                "      linked_issue: '#4541'",
                "      rationale: Canonical owner module retained intentionally for test coverage.",
                "families:",
                "  - name: sample",
                "    entries:",
                "      - id: unused_active",
                "        disposition: retain_active",
                "        target:",
                "          module_path: src/bioetl/application/unused.py",
                "          module_name: bioetl.application.unused",
                "        verification:",
                "          min_src_importers: 1",
            ]
        )
        + "\n",
    )
    _write(tmp_path / "src/bioetl/application/unused.py", "UNUSED = True\n")

    payload = build_dead_code_inventory(tmp_path)

    assert payload["summary"]["triaged_entry_count"] == 1
    assert payload["summary"]["repo_wide_owner_test_anchored_candidate_count"] == 0
    assert payload["summary"]["repo_wide_candidates_without_owner_tests_count"] == 1
    assert payload["summary"]["repo_wide_non_static_reachability_candidate_count"] == 0
    assert payload["summary"]["triaged_retained_owner_test_anchored_count"] == 0
    assert payload["summary"]["triaged_retained_without_owner_tests_count"] == 1
    review_window = payload["review_window"]
    assert review_window == {
        "linked_issue": "#4541",
        "mode": "fail-fast-zero-untriaged",
        "last_reviewed": "2026-05-22",
        "next_review_by": "2026-08-20",
        "review_cycle_days": 90,
        "max_untriaged_zero_import_candidates": 0,
        "snapshot_matches_last_reviewed": True,
        "guardrail_note": (
            "Zero static importer count is a review signal only; removals must "
            "still verify public entrypoints and dynamic/plugin import paths."
        ),
    }
    triaged = payload["triaged_entries"][0]
    assert triaged["verification_status"] == "below_min"
    assert triaged["evidence_lane"] == "retained_module_owner_suite"
    assert triaged["owner_tests"] == []
    assert triaged["owner_test_count"] == 0
    assert triaged["owner_test_paths_exist_count"] == 0

    zero_candidates = payload["repo_wide_zero_import_candidates"]
    assert zero_candidates == [
        {
            "classification_status": "classified",
            "disposition": "retain_canonical_owner_module",
            "evidence_lane": "canonical_owner_contract",
            "linked_issue": "#4541",
            "module_name": "bioetl.application.unused",
            "path": "src/bioetl/application/unused.py",
            "is_private_module": False,
            "owner_test_count": 0,
            "owner_test_paths_exist_count": 0,
            "owner_tests": [],
            "rationale": "Canonical owner module retained intentionally for test coverage.",
            "review_by": "2026-08-20",
            "reviewed_on": "2026-05-22",
            "src_importer_count": 0,
            "test_importer_count": 0,
        }
    ]


def test_build_dead_code_inventory_excludes_lazy_cli_command_entrypoints(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "configs/quality/compatibility_facade_inventory.yaml",
        "\n".join(
            [
                "version: 1",
                "policy_scope: compatibility_facades",
                "transition_debt: []",
                "retained_entrypoints:",
                "  - path: src/bioetl/interfaces/cli/main.py",
            ]
        )
        + "\n",
    )
    _write(
        tmp_path / "configs/quality/retirement_candidate_triage.yaml",
        "\n".join(
            [
                "schema_version: 1",
                "policy:",
                "  review_cycle_days: 90",
                "repo_wide_zero_import_review:",
                "  linked_issue: '#4541'",
                "  mode: fail-fast-zero-untriaged",
                "  max_untriaged_zero_import_candidates: 0",
                "  last_reviewed: '2026-05-22'",
                "  next_review_by: '2026-08-20'",
                "repo_wide_zero_import_classification:",
                "  linked_issue: '#4541'",
                "  review_date: '2026-05-22'",
                "  allowed_dispositions:",
                "    - retain_dynamic_entrypoint",
                "  entries: []",
                "families: []",
            ]
        )
        + "\n",
    )
    _write(
        tmp_path / "src/bioetl/interfaces/cli/main.py",
        "\n".join(
            [
                "_LAZY_COMMAND_SPECS = {",
                '    "maintenance": (',
                '        "bioetl.interfaces.cli.commands.maintenance",',
                '        "maintenance",',
                '        "Maintenance operations",',
                "    ),",
                "}",
            ]
        )
        + "\n",
    )
    _write(
        tmp_path / "src/bioetl/interfaces/cli/commands/maintenance.py",
        "def maintenance():\n    return None\n",
    )

    payload = build_dead_code_inventory(tmp_path)

    assert payload["summary"]["repo_wide_zero_import_candidate_count"] == 0
    assert payload["repo_wide_zero_import_candidates"] == []

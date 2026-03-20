"""Architecture guardrail for compatibility facade inventory docs."""

from __future__ import annotations

import ast
import re
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_DOC = (
    ROOT / "docs" / "02-architecture" / "07-compatibility-facade-inventory.md"
)
COMPOSITION_DOC = ROOT / "docs" / "02-architecture" / "05-composition-layer.md"
REGISTRY_GUIDE = ROOT / "docs" / "03-guides" / "registry-pattern.md"

ALLOWED_STATUSES = frozenset(
    {
        "deprecated-warn",
        "compat-shim",
        "mixed-module",
        "retained-entrypoint",
    }
)
INVENTORY_ROW_CELL_COUNT = 10

REQUIRED_TRANSITION_DEBT_PATHS: frozenset[str] = frozenset()
REQUIRED_RETAINED_ENTRYPOINT_PATHS = frozenset(
    {
        "src/bioetl/domain/composite/config.py",
        "src/bioetl/domain/value_objects/activity_values.py",
        "src/bioetl/domain/value_objects/publication_field_groups.py",
        "src/bioetl/composition/entrypoints.py",
        "src/bioetl/application/composite/merger.py",
        "src/bioetl/infrastructure/adapters/pubmed/client.py",
        "src/bioetl/infrastructure/adapters/semanticscholar/client.py",
    }
)
REQUIRED_PATHS = REQUIRED_TRANSITION_DEBT_PATHS | REQUIRED_RETAINED_ENTRYPOINT_PATHS

MEASURED_DOCSTRING_PREFIXES = (
    "Backward-compatible ",
    "Compatibility ",
    "Compatibility-",
    "Deprecated compatibility",
    "Composition-level compatibility",
    "Pipeline factory compatibility-only facade",
    "Storage compatibility-only facade",
)


def _extract_inventory_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `src/bioetl/"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        assert len(cells) == INVENTORY_ROW_CELL_COUNT, (
            f"Unexpected inventory row format: {line}"
        )
        path = cells[0].strip("`")
        status = cells[3].strip("`")
        rows.append((path, status))
    return rows


def _iter_inventory_cells(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `src/bioetl/"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        assert len(cells) == INVENTORY_ROW_CELL_COUNT, (
            f"Unexpected inventory row format: {line}"
        )
        rows.append(
            {
                "path": cells[0].strip("`"),
                "role": cells[1],
                "canonical_target": cells[2],
                "status": cells[3].strip("`"),
                "owner": cells[4].strip("`"),
                "introduced_in": cells[5].strip("`"),
                "allowed_call_sites": cells[6],
                "remove_by": cells[7].strip("`"),
                "migration_path": cells[8],
                "exit_criteria": cells[9],
            }
        )
    return rows


def _extract_measured_registry_paths(text: str) -> set[str]:
    return {
        line.split("`")[1]
        for line in text.splitlines()
        if line.startswith("- `src/bioetl/")
    }


def _extract_inventory_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    collected: list[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            in_section = True
            continue
        if in_section and (stripped.startswith("### ") or stripped.startswith("## ")):
            break
        if in_section:
            collected.append(line)

    assert collected, f"Missing inventory section: {heading}"
    return "\n".join(collected)


def _iter_measured_registry_paths() -> set[str]:
    paths = set(REQUIRED_PATHS)

    for path in (ROOT / "src" / "bioetl").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        module_docstring = ast.get_docstring(tree)
        if module_docstring is None:
            continue
        first_line = module_docstring.splitlines()[0].strip()
        if first_line.startswith(MEASURED_DOCSTRING_PREFIXES):
            paths.add(path.relative_to(ROOT).as_posix())

    return paths


@pytest.mark.architecture
def test_inventory_doc_exists_with_required_sections() -> None:
    """Compatibility facade inventory doc must exist with stable headings."""
    assert INVENTORY_DOC.exists(), (
        "Missing compatibility facade inventory doc: "
        "docs/02-architecture/07-compatibility-facade-inventory.md"
    )

    text = INVENTORY_DOC.read_text(encoding="utf-8")
    for heading in (
        "# Compatibility Facade Inventory",
        "## Status Model",
        "## Governance Freeze",
        "## Mandatory Artifact Sync",
        "## Inventory",
        "### Transition Debt Ledger",
        "### Retained Public Entrypoints",
        "## Measured Registry",
    ):
        assert heading in text, f"Missing heading in inventory doc: {heading}"


@pytest.mark.architecture
def test_inventory_doc_declares_canonical_sync_commands() -> None:
    """Inventory doc must expose canonical drift-fix commands for key artifacts."""
    text = INVENTORY_DOC.read_text(encoding="utf-8")

    required_snippets = (
        "docs/02-architecture/generated/module-dependency-map.md",
        "docs/02-architecture/generated/module-dependency-map.json",
        "./.venv/Scripts/python.exe scripts/qa/generate_architecture_dependency_map.py --check",
        "./.venv/Scripts/python.exe scripts/qa/generate_architecture_dependency_map.py --update",
        "./.venv/Scripts/python.exe -m pytest tests/architecture/test_compatibility_facade_inventory.py -q",
        "./.venv/Scripts/python.exe -m pytest tests/architecture/test_config_schema_legacy_status.py -q",
        "./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs",
    )

    for snippet in required_snippets:
        assert snippet in text, (
            "Compatibility facade inventory must keep canonical sync guidance "
            f"for mandatory artifacts: missing {snippet}"
        )


@pytest.mark.architecture
def test_inventory_doc_covers_curated_facade_modules() -> None:
    """Curated compatibility modules must stay listed with allowed statuses."""
    text = INVENTORY_DOC.read_text(encoding="utf-8")
    rows = _extract_inventory_rows(text)

    assert rows, "Compatibility facade inventory table is empty."

    documented_paths = {path for path, _status in rows}
    missing = sorted(REQUIRED_PATHS - documented_paths)
    assert not missing, (
        "Compatibility facade inventory is missing curated modules:\n"
        + "\n".join(missing)
    )

    for path, status in rows:
        assert status in ALLOWED_STATUSES, (
            f"Unexpected compatibility facade status '{status}' for {path}. "
            f"Allowed: {sorted(ALLOWED_STATUSES)}"
        )
        assert (ROOT / path).exists(), (
            f"Inventory references a missing source file: {path}"
        )


@pytest.mark.architecture
def test_inventory_doc_splits_transition_debt_from_retained_entrypoints() -> None:
    """Inventory doc must keep transition debt and retained entrypoints in separate ledgers."""
    text = INVENTORY_DOC.read_text(encoding="utf-8")
    transition_rows = dict(
        _extract_inventory_rows(
            _extract_inventory_section(text, "### Transition Debt Ledger")
        )
    )
    retained_rows = dict(
        _extract_inventory_rows(
            _extract_inventory_section(text, "### Retained Public Entrypoints")
        )
    )

    assert set(transition_rows) == REQUIRED_TRANSITION_DEBT_PATHS, (
        "Transition debt ledger drifted from the expected compat-debt scope.\n"
        + "\n".join(sorted(set(transition_rows) ^ REQUIRED_TRANSITION_DEBT_PATHS))
    )
    assert set(retained_rows) == REQUIRED_RETAINED_ENTRYPOINT_PATHS, (
        "Retained public-entrypoint ledger drifted from the expected sanctioned scope.\n"
        + "\n".join(sorted(set(retained_rows) ^ REQUIRED_RETAINED_ENTRYPOINT_PATHS))
    )

    assert all(
        status in {"deprecated-warn", "compat-shim", "mixed-module"}
        for status in transition_rows.values()
    ), "Transition debt ledger must contain only true compatibility-debt statuses."
    assert all(status == "retained-entrypoint" for status in retained_rows.values()), (
        "Retained public-entrypoint ledger must contain only retained-entrypoint rows."
    )


@pytest.mark.architecture
def test_inventory_rows_capture_owner_call_sites_and_lifecycle_metadata() -> None:
    """Compatibility rows must record ownership and explicit lifecycle metadata."""
    text = INVENTORY_DOC.read_text(encoding="utf-8")
    rows = _iter_inventory_cells(text)

    assert rows, "Compatibility facade inventory table is empty."

    path_pattern = re.compile(r"`((?:src|tests)/[^`]+\.py)`")

    for row in rows:
        assert row["canonical_target"], f"Missing canonical target for {row['path']}"
        assert row["owner"], f"Missing owner for {row['path']}"
        assert row["introduced_in"], f"Missing introduced_in for {row['path']}"
        assert re.search(r"\d{4}|RF-\d+", row["introduced_in"]), (
            f"introduced_in should contain a traceable marker for {row['path']}: "
            f"{row['introduced_in']}"
        )
        assert row["allowed_call_sites"], (
            f"Missing allowed call sites for {row['path']}"
        )
        assert row["migration_path"], f"Missing migration path for {row['path']}"
        assert re.search(r"`[^`]+`", row["migration_path"]), (
            f"Migration path should mention a concrete module or API path for "
            f"{row['path']}: {row['migration_path']}"
        )
        assert "`src`:" in row["allowed_call_sites"], (
            f"Allowed call sites must document src policy for {row['path']}"
        )
        assert "`tests`:" in row["allowed_call_sites"], (
            f"Allowed call sites must document test policy for {row['path']}"
        )

        parsed_date = date.fromisoformat(row["remove_by"])
        assert parsed_date.year >= 2026, (
            f"Unexpected remove-by/review date for {row['path']}: {row['remove_by']}"
        )

        referenced_paths = path_pattern.findall(row["allowed_call_sites"])
        for rel_path in referenced_paths:
            assert (ROOT / rel_path).exists(), (
                f"Inventory allowed-call-site path does not exist for {row['path']}: "
                f"{rel_path}"
            )


@pytest.mark.architecture
def test_retained_adapter_entrypoint_rows_prefer_package_root_imports() -> None:
    """Retained adapter client rows must document package-root imports as policy."""
    rows = {
        row["path"]: row
        for row in _iter_inventory_cells(INVENTORY_DOC.read_text(encoding="utf-8"))
    }
    expected = {
        "src/bioetl/infrastructure/adapters/pubmed/client.py": (
            "bioetl.infrastructure.adapters.pubmed"
        ),
        "src/bioetl/infrastructure/adapters/semanticscholar/client.py": (
            "bioetl.infrastructure.adapters.semanticscholar"
        ),
    }

    for path, package_root in expected.items():
        row = rows[path]
        assert (
            "first-party code imports the provider package root"
            in row["allowed_call_sites"]
        ), f"{path} must document package-root policy in allowed call sites"
        assert package_root in row["migration_path"], (
            f"{path} migration_path must point new code to package root {package_root}"
        )


@pytest.mark.architecture
def test_retained_composition_and_domain_rows_document_dedicated_test_allowlists() -> (
    None
):
    """Retained composition/domain rows must name the dedicated compat coverage files."""
    rows = {
        row["path"]: row
        for row in _iter_inventory_cells(INVENTORY_DOC.read_text(encoding="utf-8"))
    }
    expected_snippets = {
        "src/bioetl/composition/entrypoints.py": (
            "tests/unit/composition/test_entrypoints.py",
            "tests/unit/composition/test_resource_management.py",
            "tests/unit/composition/test_services_entrypoints.py",
        ),
        "src/bioetl/domain/composite/config.py": (
            "tests/unit/domain/composite/test_composite_config_facade.py",
            "tests/unit/domain/composite/test_composite_config_edge_cases.py",
        ),
        "src/bioetl/domain/value_objects/activity_values.py": (
            "tests/unit/domain/value_objects/test_value_object_facade_reexports.py",
        ),
        "src/bioetl/domain/value_objects/publication_field_groups.py": (
            "tests/unit/domain/value_objects/test_value_object_facade_reexports.py",
        ),
    }

    for path, snippets in expected_snippets.items():
        row = rows[path]
        for snippet in snippets:
            assert snippet in row["allowed_call_sites"], (
                f"{path} allowed_call_sites must mention dedicated coverage file "
                f"{snippet}"
            )


@pytest.mark.architecture
def test_retained_merge_row_captures_current_entrypoint_policy() -> None:
    """Retained merge entrypoint row must document the current sanctioned seam."""
    rows = {
        row["path"]: row
        for row in _iter_inventory_cells(INVENTORY_DOC.read_text(encoding="utf-8"))
    }
    expected = {
        "src/bioetl/application/composite/merger.py": {
            "status": "retained-entrypoint",
            "migration_snippets": (
                "bioetl.application.composite.merger",
                "MergeCollaboratorGroup",
            ),
            "allowed_call_site_snippets": (
                "tests/unit/application/composite/test_merger.py",
                "tests/unit/application/composite/merge_test_support.py",
                "tests/unit/composition/bootstrap/runtime/test_composite_support_services_factory.py",
            ),
        },
    }

    for path, constraints in expected.items():
        row = rows[path]
        assert row["status"] == constraints["status"], (
            f"{path} should remain classified as {constraints['status']} during RF-002"
        )
        for snippet in constraints["migration_snippets"]:
            assert snippet in row["migration_path"], (
                f"{path} migration_path must mention transition target {snippet}"
            )
        for snippet in constraints["allowed_call_site_snippets"]:
            assert snippet in row["allowed_call_sites"], (
                f"{path} allowed_call_sites must mention dedicated coverage file "
                f"{snippet}"
            )


@pytest.mark.architecture
def test_inventory_doc_is_linked_from_discovery_docs() -> None:
    """Inventory should be discoverable from composition and registry docs."""
    inventory_name = "07-compatibility-facade-inventory.md"
    for doc_path in (COMPOSITION_DOC, REGISTRY_GUIDE):
        text = doc_path.read_text(encoding="utf-8")
        assert inventory_name in text, (
            f"{doc_path.relative_to(ROOT)} must link to {inventory_name}"
        )


@pytest.mark.architecture
def test_inventory_doc_tracks_measured_compatibility_registry() -> None:
    """Inventory doc must capture the measurable compatibility-surface baseline."""
    text = INVENTORY_DOC.read_text(encoding="utf-8")
    inventory_rows = _extract_inventory_rows(text)
    inventory_paths = {path for path, _status in inventory_rows}
    measured_paths = _extract_measured_registry_paths(text)
    expected_paths = _iter_measured_registry_paths()

    assert measured_paths == expected_paths, (
        "Measured compatibility registry drifted from tracked source modules.\n"
        "Documented:\n"
        + "\n".join(sorted(measured_paths))
        + "\nExpected:\n"
        + "\n".join(sorted(expected_paths))
    )

    measured_only_count = len(expected_paths - inventory_paths)
    assert f"- Curated inventory rows: `{len(inventory_paths)}`" in text
    assert f"- Transition debt rows: `{len(REQUIRED_TRANSITION_DEBT_PATHS)}`" in text
    assert (
        f"- Retained public entrypoints: `{len(REQUIRED_RETAINED_ENTRYPOINT_PATHS)}`"
        in text
    )
    assert f"- Measured tracked modules: `{len(expected_paths)}`" in text
    assert (
        f"- Measured-only modules outside curated inventory: `{measured_only_count}`"
        in text
    )


@pytest.mark.architecture
def test_src_outside_composition_avoids_internal_composition_entrypoint_modules() -> (
    None
):
    """First-party source outside composition should use public composition APIs."""
    internal_modules = frozenset(
        {
            "bioetl.composition._pipeline_execution",
            "bioetl.composition._resource_management",
        }
    )
    violations: list[str] = []

    for path in (ROOT / "src" / "bioetl").rglob("*.py"):
        rel_path = path.relative_to(ROOT)
        rel_text = rel_path.as_posix()
        if rel_text.startswith("src/bioetl/composition/"):
            continue

        text = path.read_text(encoding="utf-8")
        for module in internal_modules:
            token = f"from {module} import"
            import_token = f"import {module}"
            if token in text or import_token in text:
                violations.append(rel_text)
                break

    assert not violations, (
        "First-party src outside composition must use sanctioned public "
        "composition APIs instead of internal composition entrypoint modules:\n"
        + "\n".join(sorted(violations))
    )

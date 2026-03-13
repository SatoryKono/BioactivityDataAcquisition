"""Architecture guardrail for compatibility facade inventory docs."""

from __future__ import annotations

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

REQUIRED_PATHS = frozenset(
    {
        "src/bioetl/composition/entrypoints.py",
        "src/bioetl/composition/factories/pipeline/facade.py",
        "src/bioetl/composition/factories/storage/facade.py",
        "src/bioetl/composition/factories/datasource/factory.py",
        "src/bioetl/composition/runtime_builders/runner_builder.py",
        "src/bioetl/composition/services/metadata_coordinator.py",
        "src/bioetl/composition/services/metadata_assemblers.py",
        "src/bioetl/infrastructure/storage/delta_writer.py",
        "src/bioetl/infrastructure/adapters/pubmed/client.py",
        "src/bioetl/infrastructure/adapters/semanticscholar/client.py",
    }
)


def _extract_inventory_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `src/bioetl/"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        assert len(cells) == 5, f"Unexpected inventory row format: {line}"
        path = cells[0].strip("`")
        status = cells[3].strip("`")
        rows.append((path, status))
    return rows


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
        "## Inventory",
    ):
        assert heading in text, f"Missing heading in inventory doc: {heading}"


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
def test_inventory_doc_is_linked_from_discovery_docs() -> None:
    """Inventory should be discoverable from composition and registry docs."""
    inventory_name = "07-compatibility-facade-inventory.md"
    for doc_path in (COMPOSITION_DOC, REGISTRY_GUIDE):
        text = doc_path.read_text(encoding="utf-8")
        assert inventory_name in text, (
            f"{doc_path.relative_to(ROOT)} must link to {inventory_name}"
        )


@pytest.mark.architecture
def test_src_outside_composition_avoids_internal_composition_entrypoint_modules() -> None:
    """First-party source outside composition should use composition.entrypoints."""
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
        "First-party src outside composition must use bioetl.composition.entrypoints "
        "instead of internal composition entrypoint modules:\n"
        + "\n".join(sorted(violations))
    )

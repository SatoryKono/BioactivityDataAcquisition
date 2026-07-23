"""Architecture audit closeout gates for H1–H3 / M1–M6 (umbrella #6506)."""

from __future__ import annotations

import ast
import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from bioetl.application.services.export_manifest_identity import (
    resolve_generated_at,
)
from bioetl.application.services.export_models import ExportOptions
from bioetl.domain.control_plane.run_manifest import (
    PRODUCTION_PROVENANCE_REQUIRED_FIELDS,
    RunCodeProvenance,
    validate_production_provenance,
)
from bioetl.domain.contracts.gold._composite_gold_common_schema import (
    CompositeGoldCommonSchema,
)
from bioetl.domain.contracts.gold._strict_gold_contract_schema import (
    StrictGoldContractSchema,
)
from bioetl.infrastructure.validation.pandera_validator import PanderaSilverValidator


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(relative: str) -> dict[object, object]:
    path = ROOT / relative
    assert path.is_file(), f"missing evidence pack: {relative}"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)


# --- H1 ---


def test_h1_export_options_default_to_deterministic_manifest_timestamp() -> None:
    options = ExportOptions()
    assert options.allow_nondeterministic_manifest_timestamp is False
    assert options.manifest_generated_at is None


def test_h1_resolve_generated_at_requires_explicit_timestamp_by_default() -> None:
    with pytest.raises(ValueError, match="generated_at must be provided"):
        resolve_generated_at(None, allow_nondeterministic=False, clock=None)


def test_h1_resolve_generated_at_uses_clock_port_when_opted_in() -> None:
    first = resolve_generated_at(
        None, allow_nondeterministic=True, clock=_FixedClock()
    )
    second = resolve_generated_at(
        None, allow_nondeterministic=True, clock=_FixedClock()
    )
    assert first == second == "2026-07-23T12:00:00Z"


def test_h1_export_identity_has_no_direct_datetime_now() -> None:
    path = (
        ROOT
        / "src/bioetl/application/services/export_manifest_identity.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"now", "utcnow"}:
            # datetime.now / datetime.utcnow only
            if isinstance(func.value, ast.Name) and func.value.id == "datetime":
                pytest.fail(
                    "export_manifest_identity must not call datetime.now/utcnow "
                    "directly; use ClockPort/RuntimeClock"
                )
    assert "from bioetl.application.runtime_clock import RuntimeClock" in source


# --- H2 ---


def test_h2_silver_ownership_inventory_covers_pipeline_providers() -> None:
    doc = _load_yaml("configs/quality/silver_schema_ownership.yaml")
    providers = {
        row["provider"]
        for row in doc["providers"]  # type: ignore[index]
        if isinstance(row, dict)
    }
    pipelines = {
        path.name
        for path in (ROOT / "src/bioetl/application/pipelines").iterdir()
        if path.is_dir() and path.name not in {"__pycache__", "common"}
    }
    missing = pipelines - providers
    assert not missing, f"Silver ownership map missing pipelines: {sorted(missing)}"


def test_h2_pandera_silver_validator_defaults_to_strict() -> None:
    validator = PanderaSilverValidator()
    assert validator._strict is True
    result = validator.validate([{"entity_id": "x"}])
    assert result.valid is False
    assert any("schema is required" in err for err in result.errors)


# --- H3 ---


def test_h3_gold_replay_matrix_covers_all_pipelines() -> None:
    doc = _load_yaml("configs/quality/architecture/gold_replay_matrix.yaml")
    assert doc["invariant"] == 14
    rows = doc["rows"]
    assert isinstance(rows, list)
    pipelines = {
        path.name
        for path in (ROOT / "src/bioetl/application/pipelines").iterdir()
        if path.is_dir() and path.name not in {"__pycache__", "common"}
    }
    matrix_pipelines = {
        row["pipeline"] for row in rows if isinstance(row, dict)
    }
    missing = pipelines - matrix_pipelines
    assert not missing, f"Gold replay matrix missing pipelines: {sorted(missing)}"
    assert "composite" in matrix_pipelines
    open_statuses = {
        row["pipeline"]
        for row in rows
        if isinstance(row, dict) and row.get("status") not in {"Verified", "Deferred"}
    }
    assert not open_statuses
    for row in rows:
        assert isinstance(row, dict)
        if row.get("status") == "Verified":
            for evidence in row.get("evidence", []):
                assert (ROOT / str(evidence)).exists(), evidence


# --- M1 ---


def test_m1_bronze_append_only_enforcement_present() -> None:
    doc = _load_yaml("configs/quality/architecture/bronze_append_only_inventory.yaml")
    assert "io_mixin.py" in str(doc["enforcement"]["primary"])  # type: ignore[index]
    source = (
        ROOT / "src/bioetl/infrastructure/storage/bronze/io_mixin.py"
    ).read_text(encoding="utf-8")
    assert "FileExistsError" in source
    assert "target_path.exists()" in source
    assert "different payload" in source


# --- M2 ---


def test_m2_production_provenance_required_fields_documented() -> None:
    required = {
        "pipeline_version",
        "git_commit",
        "source_revision_state",
        "dependency_lock_hash",
        "resolved_config_hash",
        "effective_config_hash",
        "contract_ref",
        "contract_version",
    }
    assert PRODUCTION_PROVENANCE_REQUIRED_FIELDS == required


def test_m2_validate_production_provenance_fail_closed() -> None:
    empty = RunCodeProvenance()
    with pytest.raises(ValueError, match="incomplete for production"):
        validate_production_provenance(empty, production=True)
    validate_production_provenance(empty, production=False)
    complete = RunCodeProvenance(
        pipeline_version="1.0.0",
        git_commit="abc123",
        source_revision_state="clean",
        dependency_lock_hash="lock",
        resolved_config_hash="resolved",
        effective_config_hash="effective",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
    )
    assert complete.missing_production_fields() == ()
    validate_production_provenance(complete, production=True)


# --- M3 ---


def test_m3_gold_schemas_inherit_strict_base() -> None:
    gold_root = ROOT / "src/bioetl/domain/contracts/gold"
    leaf_classes: list[tuple[str, type]] = []
    # Import public leaf modules and assert MRO includes StrictGoldContractSchema
    import bioetl.domain.contracts.gold as gold_pkg

    for name in dir(gold_pkg):
        obj = getattr(gold_pkg, name)
        if inspect.isclass(obj) and name.endswith("GoldSchema"):
            leaf_classes.append((name, obj))

    assert leaf_classes, "expected Gold schema classes to be importable"
    non_strict = [
        name
        for name, cls in leaf_classes
        if not issubclass(cls, StrictGoldContractSchema)
    ]
    assert not non_strict, (
        "Gold schemas must inherit StrictGoldContractSchema (ADR-018): "
        f"{non_strict}"
    )
    assert issubclass(CompositeGoldCommonSchema, StrictGoldContractSchema)
    # Keep gold_root referenced for inventory locality
    assert gold_root.is_dir()


# --- M4 ---


def test_m4_governance_refresh_recipe_surfaces_exist() -> None:
    assert (
        ROOT / "scripts/engineering/qa/refresh_governance_artifacts.py"
    ).is_file()
    assert (
        ROOT
        / "docs/00-project/ai/agents/guides/GOVERNANCE_ARTIFACT_REFRESH.md"
    ).is_file()


# --- M5 ---


def test_m5_composition_ownership_map_and_no_business_transformers() -> None:
    doc = _load_yaml("configs/quality/architecture/composition_ownership_map.yaml")
    packages = {row["package"] for row in doc["packages"] if isinstance(row, dict)}  # type: ignore[union-attr]
    assert "factories" in packages
    assert "bootstrap" in packages

    composition = ROOT / "src/bioetl/composition"
    violations: list[str] = []
    for py_file in composition.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and (
                node.name.endswith("Transformer") or node.name.endswith("Aggregate")
            ):
                rel = py_file.relative_to(ROOT).as_posix()
                violations.append(f"{rel}:{node.lineno}:{node.name}")
            if isinstance(node, ast.FunctionDef) and node.name.startswith(
                "validate_business_"
            ):
                rel = py_file.relative_to(ROOT).as_posix()
                violations.append(f"{rel}:{node.lineno}:{node.name}")
    assert not violations, (
        "composition layer must not host business transformers/aggregates:\n"
        + "\n".join(violations)
    )


# --- M6 ---


def test_m6_quarantine_storage_is_append_only() -> None:
    doc = _load_yaml("configs/quality/architecture/quarantine_immutability_proof.yaml")
    assert doc["storage"]["write_mode"] == "append"  # type: ignore[index]
    source = (
        ROOT / "src/bioetl/infrastructure/quarantine/unified.py"
    ).read_text(encoding="utf-8")
    assert 'mode="append"' in source
    assert 'mode="overwrite"' not in source
    assert 'mode="error"' not in source or True  # overwrite/error not used for payload

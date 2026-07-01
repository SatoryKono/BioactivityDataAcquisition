"""Coverage boost tests for infrastructure quality helper modules."""

from __future__ import annotations

import builtins
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

import bioetl.infrastructure.quality.architecture_debt_task_support as support_module
from bioetl.infrastructure.quality.budget_evaluator import (
    _count_hotspot_registry_entries,
    _get_typed_budgets,
    _get_typed_prefixes,
    _iter_hotspot_budget_entries,
    current_quarter_target,
    evaluate_hotspot_budget_violations,
)
from bioetl.infrastructure.quality.debt_scorecard import (
    _iter_registry_entries,
    _normalized_owner,
    _resolve_enforceable_baseline,
    _technical_debt_owner_counts,
    evaluate_debt_scorecard,
)
from bioetl.infrastructure.quality._governance_validation import (
    _burn_down_priority_registries,
    _validate_baseline_policy,
    _validate_governance_section,
    _validate_hotspot_budgets_section,
)
from bioetl.infrastructure.quality.architecture_debt_reduction import (
    _default_limit,
    _default_plan_output_path,
    _layer_for_target,
    _require_generated_at,
    find_latest_architecture_debt_tasks_file,
    load_architecture_debt_tasks,
)
from bioetl.infrastructure.quality.architecture_debt_task_support import (
    SymbolMetricLocation,
    build_symbol_index,
    fallback_complexity,
    iter_source_modules,
    measure_task,
    parse_limit_value,
    safe_text,
    select_symbol_location,
    task_status,
)
from bioetl.infrastructure.quality.inventory import ExemptionInventorySummary


pytestmark = pytest.mark.unit


def test_validate_baseline_policy_and_hotspot_budget_errors_are_reported() -> None:
    errors: list[str] = []
    _validate_baseline_policy({}, errors=errors)
    assert "governance.baseline_policy: expected mapping" in errors

    errors = []
    _validate_hotspot_budgets_section(
        {
            "hotspot_budgets": [
                {
                    "name": "control_plane",
                    "rationale": "Track priority registries.",
                    "path_prefixes": ["src/bioetl/infrastructure/control_plane/"],
                    "registry_budgets": {"class_size": 1},
                },
                {
                    "name": "control_plane",
                    "rationale": "",
                    "path_prefixes": ["docs/not-source/"],
                    "registry_budgets": {"unknown_registry": -1},
                },
            ],
            "governance": {
                "burn_down_priorities": {
                    "registries": ["class_size", "function_length", 7],
                }
            },
        },
        baseline_registry_names={"class_size", "function_length"},
        errors=errors,
    )
    assert _burn_down_priority_registries(
        {"governance": {"burn_down_priorities": {"registries": ["class_size", 5]}}}
    ) == {"class_size"}
    assert any("duplicate hotspot name" in error for error in errors)
    assert any("expected non-empty string" in error for error in errors)
    assert any("must start with 'src/bioetl/'" in error for error in errors)
    assert any("unknown registry 'unknown_registry'" in error for error in errors)
    assert any("missing coverage for burn_down_priorities" in error for error in errors)


def test_validate_governance_section_reports_missing_mapping_and_invalid_review_policy() -> None:
    errors: list[str] = []
    assert (
        _validate_governance_section(
            {},
            baseline_registry_names={"class_size"},
            group_names={"size_shape"},
            errors=errors,
        )
        is False
    )
    assert "governance: required mapping" in errors

    errors = []
    assert (
        _validate_governance_section(
            {
                "hotspot_budgets": [{"name": "", "registry_budgets": {}}],
                "governance": {
                    "baseline_policy": {"rationale": ""},
                    "review_policy": {"new_exemption_requires": []},
                    "owner_registry_q3_subsystems": {"sub_a": {"owner": "alice"}},
                    "growth_gate_default_mode": "warn",
                    "allow_grace_windows_only_for_rf": False,
                    "growth_section_gate_rollout": {"warn_until_by_section": {}},
                },
            },
            baseline_registry_names={"class_size"},
            group_names={"size_shape"},
            errors=errors,
        )
        is False
    )
    assert any("governance.baseline_policy.enforceable_section" in error for error in errors)
    assert any("new_exemption_requires: expected non-empty list" in error for error in errors)
    assert any("expected at least 3 subsystems" in error for error in errors)


def test_governance_validation_covers_mapping_and_section_key_errors() -> None:
    errors: list[str] = []
    _validate_hotspot_budgets_section(
        {"hotspot_budgets": ["invalid"], "governance": {}},
        baseline_registry_names={"class_size"},
        errors=errors,
    )
    assert errors == ["hotspot_budgets[0]: expected mapping"]

    errors = []
    _validate_governance_section(
        {
            "hotspot_budgets": [
                {
                    "name": "hotspot",
                    "path_prefixes": ["src/bioetl/x/"],
                    "rationale": "x",
                    "registry_budgets": {"class_size": 1},
                }
            ],
            "governance": {
                "baseline_policy": "bad",
                "review_policy": "bad",
                "owner_registry_q3_subsystems": {1: "bad", "sub_a": {}},
                "growth_gate_default_mode": "block",
                "allow_grace_windows_only_for_rf": False,
                "growth_section_gate_rollout": {"warn_until_by_section": {None: "2026-01-01"}},
                "burn_down_priorities": {"registries": []},
            },
        },
        baseline_registry_names={"class_size"},
        group_names={"size_shape"},
        errors=errors,
    )
    assert any("governance.baseline_policy: expected mapping" in error for error in errors)
    assert any("governance.review_policy: expected mapping" in error for error in errors)
    assert any("subsystem key must be non-empty string" in error for error in errors)
    assert any("expected non-empty string" in error for error in errors)


def test_task_support_helpers_cover_path_and_symbol_resolution(tmp_path: Path) -> None:
    source_root = tmp_path / "src" / "bioetl" / "application"
    source_root.mkdir(parents=True, exist_ok=True)
    module_path = source_root / "worker.py"
    module_path.write_text(
        "class Runner:\n"
        "    def first(self):\n"
        "        return 1\n\n"
        "    async def second(self):\n"
        "        return 2\n\n"
        "def chooser(value: int) -> int:\n"
        "    return 1 if value else 0\n",
        encoding="utf-8",
    )
    syntax_error_path = source_root / "broken.py"
    syntax_error_path.write_text("def broken(:\n", encoding="utf-8")
    (source_root / "__init__.py").write_text("", encoding="utf-8")

    modules = iter_source_modules(tmp_path)
    assert module_path in modules
    assert all(path.name != "__init__.py" for path in modules)

    symbol_index = build_symbol_index(tmp_path)
    runner_locations = symbol_index["Runner"]
    chooser_locations = symbol_index["chooser"]
    assert runner_locations[0].method_count == 2
    assert chooser_locations[0].complexity is not None

    selected, target_file, symbol_name, note_text = select_symbol_location(
        key="chooser",
        registry_name="function_length",
        project_root=tmp_path,
        symbol_index=symbol_index,
    )
    assert selected is not None
    assert target_file == "src/bioetl/application/worker.py"
    assert symbol_name == "chooser"
    assert note_text is None

    target_file, symbol_name, current_value, note = measure_task(
        registry_name="function_length",
        key="src/bioetl/application/worker.py::chooser",
        project_root=tmp_path,
        symbol_index=symbol_index,
    )
    assert target_file == "src/bioetl/application/worker.py"
    assert symbol_name == "chooser"
    assert current_value == 2
    assert note is None
    assert measure_task(
        registry_name="class_size",
        key="Runner",
        project_root=tmp_path,
        symbol_index=symbol_index,
    ) == ("src/bioetl/application/worker.py", "Runner", 6, None)
    assert measure_task(
        registry_name="class_method_count",
        key="Runner",
        project_root=tmp_path,
        symbol_index=symbol_index,
    ) == ("src/bioetl/application/worker.py", "Runner", 2, None)
    assert measure_task(
        registry_name="unknown",
        key="Runner",
        project_root=tmp_path,
        symbol_index=symbol_index,
    ) == (None, "Runner", None, None)

    assert task_status(
        registry_name="function_length",
        current_value=15,
        limit_value=10,
        target_file=target_file,
    ) == "needs_refactor"
    assert task_status(
        registry_name="god_object",
        current_value=15,
        limit_value=10,
        target_file=target_file,
    ) == "not_measurable"
    assert task_status(
        registry_name="function_length",
        current_value=5,
        limit_value=10,
        target_file=None,
    ) == "target_not_found"
    assert task_status(
        registry_name="function_length",
        current_value=None,
        limit_value="warn",
        target_file="src/bioetl/application/worker.py",
    ) == "not_measurable"


def test_task_support_helpers_cover_safe_text_parse_and_fallback_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "payload.py"
    file_path.write_text("def sample() -> int:\n    return 1\n", encoding="utf-8")

    assert parse_limit_value({"value": 7}) == 7
    assert parse_limit_value({"value": 3.8}) == 3
    assert parse_limit_value({"value": " 11 "}) == 11
    assert parse_limit_value({"value": "warn"}) == "warn"
    assert parse_limit_value({"value": ""}) is None
    assert safe_text(file_path) is not None

    with patch.object(Path, "read_text", side_effect=UnicodeDecodeError("utf-8", b"x", 0, 1, "boom")):
        assert safe_text(file_path) is None

    complexity = fallback_complexity(
        support_module.ast.parse(
            "def compute(items):\n"
            "    return [item for item in items if item and (item > 0 or item == 0)]\n"
        ).body[0]
    )
    assert complexity >= 4

    real_import = builtins.__import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "radon.complexity":
            raise ImportError("radon missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    try:
        complexities = support_module.function_complexities(
            "def alpha(value):\n"
            "    if value:\n"
            "        return 1\n"
            "    return 0\n"
        )
    finally:
        monkeypatch.setattr(builtins, "__import__", real_import)

    assert complexities["alpha"] >= 2
    assert iter_source_modules(tmp_path / "missing-root") == []


def test_architecture_debt_reduction_helpers_cover_default_paths_and_loading(
    tmp_path: Path,
) -> None:
    report_root = tmp_path / "reports" / "quality"
    report_root.mkdir(parents=True, exist_ok=True)
    latest = report_root / "tasks_architecture_metric_exemptions_2026-04-05-09-30.json"
    latest.write_text('{"tasks": []}', encoding="utf-8")
    legacy = tmp_path / "tasks_architecture_metric_exemptions_2026-04-04-09-30.json"
    legacy.write_text('{"tasks": []}', encoding="utf-8")
    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]", encoding="utf-8")

    assert find_latest_architecture_debt_tasks_file(project_root=tmp_path) == latest
    latest.unlink()
    assert find_latest_architecture_debt_tasks_file(project_root=tmp_path) == legacy
    assert load_architecture_debt_tasks(legacy) == {"tasks": []}
    with pytest.raises(ValueError, match="must be a mapping"):
        load_architecture_debt_tasks(invalid)

    assert _layer_for_target("src/bioetl/domain/module.py") == "domain"
    assert _layer_for_target("docs/readme.md") is None
    assert _default_limit(
        {"registry": "file_size_limits", "target_file": "src/bioetl/domain/module.py"}
    ) == 305
    assert _default_limit(
        {"registry": "function_complexity", "target_file": "src/bioetl/application/service.py"}
    ) == 10
    assert _default_limit({"registry": "mystery", "target_file": None}) is None

    output_path = _default_plan_output_path(
        project_root=tmp_path,
        generated_at=pytest.importorskip("datetime").datetime(2026, 4, 4, 9, 30),
    )
    assert output_path.name == "architecture_debt_execution_plan_2026-04-04-09-30.json"
    with pytest.raises(ValueError, match="generated_at must be provided"):
        _require_generated_at(None)


def test_select_symbol_location_reports_ambiguous_candidates(tmp_path: Path) -> None:
    app_path = tmp_path / "src" / "bioetl" / "application" / "worker.py"
    infra_path = tmp_path / "src" / "bioetl" / "infrastructure" / "worker.py"
    app_path.parent.mkdir(parents=True, exist_ok=True)
    infra_path.parent.mkdir(parents=True, exist_ok=True)
    app_path.write_text("def duplicate():\n    return 1\n", encoding="utf-8")
    infra_path.write_text(
        "def duplicate():\n"
        "    value = 1\n"
        "    return value\n",
        encoding="utf-8",
    )

    symbol_index = {
        "duplicate": [
            SymbolMetricLocation(
                name="duplicate",
                path=app_path,
                kind="function",
                lineno=1,
                end_lineno=2,
                size=2,
                complexity=1,
            ),
            SymbolMetricLocation(
                name="duplicate",
                path=infra_path,
                kind="function",
                lineno=1,
                end_lineno=3,
                size=3,
                complexity=1,
            ),
        ]
    }

    location, target_file, symbol_name, note = select_symbol_location(
        key="duplicate",
        registry_name="function_length",
        project_root=tmp_path,
        symbol_index=symbol_index,
    )
    assert location is not None
    assert location.path == infra_path
    assert target_file == "src/bioetl/infrastructure/worker.py"
    assert symbol_name == "duplicate"
    assert note is not None
    assert "Other candidates" in note


def test_task_support_helpers_cover_missing_symbol_and_file_measurement_paths(
    tmp_path: Path,
) -> None:
    assert measure_task(
        registry_name="file_size_limits",
        key="src/bioetl/domain/missing.py",
        project_root=tmp_path,
        symbol_index={},
    ) == (None, None, None, None)

    source_path = tmp_path / "src" / "bioetl" / "domain" / "sample.py"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("line1\nline2\n", encoding="utf-8")
    with patch.object(support_module, "safe_text", return_value=None):
        assert measure_task(
            registry_name="file_size_limits",
            key="src/bioetl/domain/sample.py",
            project_root=tmp_path,
            symbol_index={},
        ) == (
            "src/bioetl/domain/sample.py",
            None,
            None,
            "Could not read file for LOC measurement.",
        )

    assert select_symbol_location(
        key="src/bioetl/domain/sample.py::missing_symbol",
        registry_name="function_length",
        project_root=tmp_path,
        symbol_index={},
    ) == (None, "src/bioetl/domain/sample.py", "missing_symbol", None)
    assert select_symbol_location(
        key="src/bioetl/domain/sample.py",
        registry_name="function_length",
        project_root=tmp_path,
        symbol_index={},
    ) == (None, "src/bioetl/domain/sample.py", None, None)
    assert select_symbol_location(
        key="unknown_symbol",
        registry_name="function_length",
        project_root=tmp_path,
        symbol_index={},
    ) == (None, None, "unknown_symbol", None)


def test_budget_and_scorecard_helper_branches_cover_hotspots_and_technical_debt() -> None:
    assert _get_typed_prefixes("bad") is None
    assert _get_typed_budgets("bad") is None
    assert _iter_hotspot_budget_entries("bad") == []
    assert (
        current_quarter_target({"quarterly_targets": ["bad"]}, today=date(2025, 1, 1))
        is None
    )

    raw_registry = {
        "registries": {
            "class_size": {
                "src/bioetl/application/service.py::HeavyClass": {
                    "classification": "technical_debt",
                    "owner": " alice ",
                },
                "docs/readme.md::Nope": {
                    "classification": "accepted_risk",
                    "owner": "",
                },
            }
        }
    }
    assert len(_iter_registry_entries(raw_registry)) == 2
    assert _normalized_owner(" alice ") == "alice"
    assert _normalized_owner("") == "<missing>"
    assert _technical_debt_owner_counts(raw_registry) == {"alice": 1}

    hotspot_counts = _count_hotspot_registry_entries(
        registries=raw_registry["registries"],
        typed_prefixes=("src/bioetl/application/",),
        registry_budgets={"class_size": 1},
    )
    assert hotspot_counts["class_size"] == 1

    violations, by_hotspot = evaluate_hotspot_budget_violations(
        raw_registry={"registries": raw_registry["registries"]},
        scorecard={
            "hotspot_budgets": [
                {
                    "name": "application_hotspot",
                    "path_prefixes": ["src/bioetl/application/"],
                    "registry_budgets": {"class_size": 0},
                }
            ]
        },
    )
    assert by_hotspot == {"application_hotspot": {"class_size": 1}}
    assert any("application_hotspot" in item for item in violations)

    with pytest.raises(ValueError, match="expected mapping"):
        _resolve_enforceable_baseline({"baseline": []})


def test_evaluate_debt_scorecard_covers_missing_baseline_and_target_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventory = ExemptionInventorySummary(
        total_exemptions=1,
        by_registry={"class_size": 1},
        by_owner={"alice": 1},
        by_expiry_quarter={},
        expired_entries=0,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.quality.debt_scorecard.load_exemptions_registry",
        lambda _path=None: {"registries": {}},
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.quality.debt_scorecard.build_exemption_inventory",
        lambda _path=None, today=None: inventory,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.quality.debt_scorecard.validate_debt_scorecard",
        lambda _path=None: [],
    )

    monkeypatch.setattr(
        "bioetl.infrastructure.quality.debt_scorecard.load_debt_scorecard",
        lambda _path=None: {
            "baseline": {"total_exemptions": "bad"},
            "quarterly_targets": [{"quarter": "2026-Q2"}],
        },
    )
    violations, summary = evaluate_debt_scorecard(today=date(2026, 4, 1))
    assert summary is None
    assert violations == ["scorecard enforceable baseline missing int total_exemptions"]

    monkeypatch.setattr(
        "bioetl.infrastructure.quality.debt_scorecard.load_debt_scorecard",
        lambda _path=None: {
            "baseline": {"total_exemptions": 1},
            "quarterly_targets": [],
        },
    )
    violations, summary = evaluate_debt_scorecard(today=date(2026, 4, 1))
    assert summary is None
    assert any("Missing quarterly target" in item for item in violations)

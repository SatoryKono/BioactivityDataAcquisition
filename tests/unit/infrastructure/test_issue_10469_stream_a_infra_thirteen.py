"""Stream A quality leftovers: scorecard, budgets, debt, exemptions, baseline."""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from bioetl.infrastructure.quality import architecture_debt_artifact_tasks as debt_tasks
from bioetl.infrastructure.quality import architecture_debt_reduction as debt_reduction
from bioetl.infrastructure.quality import (
    architecture_quality_scorecard as scorecard_mod,
)
from bioetl.infrastructure.quality import budget_evaluator as budget_mod
from bioetl.infrastructure.quality import exemptions_registry_policy as policy
from bioetl.infrastructure.quality import exemptions_registry_targets as targets
from bioetl.infrastructure.quality import exemptions_registry_validation as validation
from bioetl.infrastructure.quality.architecture_debt_artifact_tasks import (
    artifact_defaults,
    build_dead_code_review_tasks,
    build_duplication_tasks,
    build_hotspot_family_tasks,
)
from bioetl.infrastructure.quality.architecture_debt_reduction import (
    find_latest_architecture_debt_tasks_file,
    load_architecture_debt_tasks,
)
from bioetl.infrastructure.quality.architecture_debt_task_support import (
    SymbolMetricLocation,
    build_symbol_index,
    measure_task,
    safe_text,
)
from bioetl.infrastructure.quality.architecture_quality_scorecard import (
    write_architecture_quality_scorecard,
)
from bioetl.infrastructure.quality.budget_evaluator import (
    evaluate_hotspot_budget_violations,
)
from bioetl.infrastructure.quality.exemptions_registry_policy import (
    validate_exemption_key_normalization,
    validate_exemptions_registry,
)
from bioetl.infrastructure.quality.exemptions_registry_validation import (
    validate_exemption_entry,
)
from bioetl.infrastructure.quality.report_formatter import (
    _resolve_rollout_mode_for_section,
)
from bioetl.infrastructure.quality._baseline_validation import (
    _normalize_registry_groups,
    _validate_historical_baseline_metadata,
    _validate_historical_baseline_section,
)
from bioetl.infrastructure.quality._governance_validation import (
    _burn_down_priority_registries,
    _validate_owner_registry_subsystems,
    _validate_warn_until_by_section,
)

pytestmark = pytest.mark.unit


class TestScorecardAndBudgetEvaluator:
    def test_scorecard_metric_helpers_and_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert scorecard_mod._current_compatibility_debt_metrics("bad") == {}
        assert (
            scorecard_mod._current_compatibility_debt_metrics({"metrics": "no"}) == {}
        )
        assert scorecard_mod._scorecard_metric_count({"s": "no"}, "s", "m") == 0
        assert (
            scorecard_mod._scorecard_metric_count({"s": {"metrics": "no"}}, "s", "m")
            == 0
        )
        assert (
            scorecard_mod._scorecard_metric_count(
                {"s": {"metrics": {"m": "no"}}}, "s", "m"
            )
            == 0
        )
        monkeypatch.setattr(
            scorecard_mod,
            "build_architecture_quality_scorecard",
            lambda **_kwargs: {"integral_score": 1},
        )
        out = tmp_path / "nested" / "scorecard.json"
        payload = write_architecture_quality_scorecard(out, repo_root=tmp_path)
        assert payload["integral_score"] == 1
        assert out.is_file()

    def test_budget_hotspot_and_owner_decomposition_guards(self) -> None:
        assert (
            budget_mod._is_owner_decomposition_active(
                scorecard={
                    "governance": {
                        "owner_diversification": {"starts_quarter": "not-a-quarter"}
                    }
                },
                quarter="also-bad",
            )
            is True
        )
        assert budget_mod._parse_hotspot_entry({"name": 1}) is None
        assert (
            budget_mod._parse_hotspot_entry({"name": "hot", "path_prefixes": []})
            is None
        )
        assert (
            budget_mod._parse_hotspot_entry(
                {"name": "hot", "path_prefixes": ["src/"], "registry_budgets": "no"}
            )
            is None
        )
        assert budget_mod._iter_hotspot_budget_entries(["not-dict", {"name": 1}]) == []
        counts = budget_mod._count_hotspot_registry_entries(
            registries={"file_size_limits": {1: {}, "src/a.py": "no", "src/b.py": {}}},
            typed_prefixes=("src/",),
            registry_budgets={"file_size_limits": 1},
        )
        assert counts["file_size_limits"] == 1
        assert evaluate_hotspot_budget_violations(raw_registry={}, scorecard={}) == (
            [],
            {},
        )
        violations, _by_hotspot = evaluate_hotspot_budget_violations(
            raw_registry={"registries": "bad"},
            scorecard={
                "hotspot_budgets": [
                    {
                        "name": "hot",
                        "path_prefixes": ["src/"],
                        "registry_budgets": {"file_size_limits": 1},
                    }
                ]
            },
        )
        assert violations == ["exemptions.registries: expected mapping"]


class TestBaselineGovernanceAndDebtTasks:
    def test_baseline_historical_and_registry_group_guards(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        errors: list[str] = []
        assert (
            _validate_historical_baseline_section(
                {},
                enforceable_total=1,
                enforceable_registry_counts={},
                errors=errors,
            )
            is None
        )
        monkeypatch.setattr(
            "bioetl.infrastructure.quality._baseline_validation._validate_baseline_mapping",
            lambda **_kwargs: (1, {}),
        )
        assert (
            _validate_historical_baseline_section(
                {"historical_baseline": "not-dict"},
                enforceable_total=1,
                enforceable_registry_counts={},
                errors=errors,
            )
            is None
        )
        meta_errors: list[str] = []
        _validate_historical_baseline_metadata(historical={}, errors=meta_errors)
        assert any("snapshot_date" in item for item in meta_errors)
        assert any("source_report" in item for item in meta_errors)
        group_errors: list[str] = []
        groups, listed = _normalize_registry_groups(
            registry_groups={"": {"registries": ["a"]}, "g": []},
            errors=group_errors,
        )
        assert groups == {}
        assert listed == []
        assert group_errors

    def test_governance_owner_rollout_and_burndown_guards(self) -> None:
        errors: list[str] = []
        _validate_owner_registry_subsystems("bad", errors=errors)
        assert errors
        rollout_errors: list[str] = []
        _validate_warn_until_by_section(
            "bad",
            baseline_registry_names=set(),
            group_names=set(),
            errors=rollout_errors,
        )
        assert rollout_errors
        assert (
            _burn_down_priority_registries(
                {"governance": {"burn_down_priorities": {"registries": "x"}}}
            )
            == set()
        )

    def test_artifact_task_builders_skip_invalid_rows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        paths = artifact_defaults(tmp_path)
        monkeypatch.setattr(
            debt_tasks,
            "load_json_if_present",
            lambda path: {
                "targets": "nope" if path == paths["duplication_baseline"] else [],
                "families": "nope" if path == paths["hotspot_baseline"] else [],
            },
        )
        assert build_duplication_tasks(artifact_paths=paths) == []
        assert build_hotspot_family_tasks(artifact_paths=paths) == []

        def load_rows(path: Path) -> dict[str, object]:
            if path == paths["duplication_baseline"]:
                return {
                    "targets": [
                        "skip",
                        {"target": "src/a.py", "duplicate_count": 0},
                        {
                            "target": "src/b.py",
                            "duplicate_count": 2,
                            "actionability": "no",
                        },
                    ]
                }
            if path == paths["hotspot_baseline"]:
                return {
                    "families": [
                        "skip",
                        {"budget_warnings": []},
                        {
                            "budget_warnings": ["too-big"],
                            "path_prefixes": ["src/bioetl/"],
                        },
                    ]
                }
            if path == paths["dead_code_inventory"]:
                return {
                    "summary": {"repo_wide_untriaged_zero_import_candidate_count": 9},
                    "review_window": {"max_untriaged_zero_import_candidates": "n/a"},
                }
            return {}

        monkeypatch.setattr(debt_tasks, "load_json_if_present", load_rows)
        monkeypatch.setattr(debt_tasks, "load_yaml_if_present", lambda _path: {})
        dup = build_duplication_tasks(artifact_paths=paths)
        assert dup[0]["id"] == "ARD-DUP-003"
        hot = build_hotspot_family_tasks(artifact_paths=paths)
        assert hot[0]["id"] == "ARD-HOT-003"
        assert build_dead_code_review_tasks(artifact_paths=paths) == []


class TestExemptionsDebtReductionAndFormatter:
    def test_exemptions_policy_outside_src_and_required_registry_shapes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src_file = tmp_path / "src" / "bioetl" / "mod.py"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("x = 1\n", encoding="utf-8")
        monkeypatch.setattr(policy, "_project_root", lambda: tmp_path)
        original_relative = Path.is_relative_to

        def fake_relative(self: Path, other: Path) -> bool:
            if self == src_file:
                return False
            return original_relative(self, other)

        monkeypatch.setattr(Path, "is_relative_to", fake_relative)
        monkeypatch.setattr(
            policy,
            "load_exemptions_registry",
            lambda _path=None: {
                "registries": {"file_size_limits": {"src/bioetl/mod.py": {}}}
            },
        )
        errors = validate_exemption_key_normalization()
        assert any("inside src/ tree" in item for item in errors)

        monkeypatch.setattr(
            policy, "REQUIRED_EXEMPTION_REGISTRIES", ("file_size_limits", "custom")
        )
        monkeypatch.setattr(policy, "EXEMPTION_REGISTRIES_ALLOW_EMPTY", frozenset())
        metadata: list[str] = []
        policy._validate_required_registries(
            {"file_size_limits": [], "custom": {}},
            metadata,
        )
        assert any("expected mapping" in item for item in metadata)
        assert any("must not be empty" in item for item in metadata)
        monkeypatch.setattr(
            policy,
            "load_exemptions_registry",
            lambda _path=None: {
                "registries": {
                    "file_size_limits": {},
                    "extra": "not-map",
                }
            },
        )
        meta, _expired = validate_exemptions_registry(today=None)
        assert any("expected mapping" in item for item in meta)

    def test_exemptions_validation_classification_and_linked_rf(self) -> None:
        entry_errors: list[str] = []
        expired: list[str] = []
        validate_exemption_entry(
            "class_size",
            "LiveClass",
            {
                "owner": "team-a",
                "classification": "",
                "linked_rf": "",
                "expires_on": "2026-12-01",
                "reason": "x",
                "value": 1,
                "removal_step": "split",
            },
            (
                "owner",
                "classification",
                "linked_rf",
                "expires_on",
                "reason",
                "value",
                "removal_step",
            ),
            date(2026, 9, 17),
            entry_errors,
            expired,
        )
        assert any("classification must be non-empty" in item for item in entry_errors)
        assert any("linked_rf must be non-empty" in item for item in entry_errors)
        validation._validate_classification(
            "p", {"classification": "nope"}, entry_errors
        )
        assert any("must be one of" in item for item in entry_errors)

    def test_exemptions_targets_skip_non_mapping_and_non_str_keys(self) -> None:
        errors: list[str] = []
        targets._validate_registry_entries(
            registry_name="class_size",
            entries="bad",
            classes_by_module={},
            functions_by_module={},
            class_counts=Counter(),
            function_counts=Counter(),
            errors=errors,
        )
        assert errors == []
        targets._validate_registry_entries(
            registry_name="class_size",
            entries={1: {}, 2: {}},
            classes_by_module={},
            functions_by_module={},
            class_counts=Counter(),
            function_counts=Counter(),
            errors=errors,
        )
        assert errors == []

    def test_debt_reduction_and_task_support(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        quality = tmp_path / "reports" / "quality"
        quality.mkdir(parents=True)
        (quality / "tasks_architecture_metric_exemptions_2026.json").write_text(
            "{}", encoding="utf-8"
        )
        found = find_latest_architecture_debt_tasks_file(project_root=tmp_path)
        assert found is not None
        listed = tmp_path / "tasks.json"
        listed.write_text("[1]", encoding="utf-8")
        with pytest.raises(ValueError, match="must be a mapping"):
            load_architecture_debt_tasks(listed)
        assert debt_reduction._layer_for_target("src/only") is None
        assert (
            debt_reduction._within_limit_category(
                status="within_limit",
                current_value="n/a",
                delta_to_limit="n/a",
                default_limit=10,
            )
            is None
        )
        assert (
            debt_reduction._within_limit_category(
                status="within_limit",
                current_value=20,
                delta_to_limit=-20,
                default_limit=10,
            )
            == "SAFE_MARGIN"
        )
        monkeypatch.setattr(
            "bioetl.infrastructure.quality.architecture_debt_task_support.iter_source_modules",
            lambda _root: [tmp_path / "broken.py"],
        )
        monkeypatch.setattr(
            "bioetl.infrastructure.quality.architecture_debt_task_support.safe_text",
            lambda _path: "def oops(:\n",
        )
        assert build_symbol_index(tmp_path) == {}
        location = SymbolMetricLocation(
            name="Cls",
            path=tmp_path / "mod.py",
            kind="class",
            lineno=1,
            end_lineno=10,
            size=10,
            method_count=3,
            complexity=4,
        )
        monkeypatch.setattr(
            "bioetl.infrastructure.quality.architecture_debt_task_support.select_symbol_location",
            lambda **_kwargs: (location, "src/mod.py", "Cls", None),
        )
        _target, name, value, _note = measure_task(
            registry_name="class_size",
            key="Cls",
            project_root=tmp_path,
            symbol_index={},
        )
        assert name == "Cls"
        assert value == 10
        _target, _name, fallback_value, _note = measure_task(
            registry_name="god_object",
            key="Cls",
            project_root=tmp_path,
            symbol_index={},
        )
        assert fallback_value is None
        assert safe_text(tmp_path / "missing.py") is None

    def test_report_formatter_rollout_mode_fallbacks(self) -> None:
        today = date(2026, 9, 17)
        assert (
            _resolve_rollout_mode_for_section(
                scorecard={"governance": "bad"},
                section_key="file_size_limits",
                today=today,
                fallback_mode="block",
            )
            == "block"
        )
        assert (
            _resolve_rollout_mode_for_section(
                scorecard={"governance": {"growth_section_gate_rollout": "bad"}},
                section_key="file_size_limits",
                today=today,
                fallback_mode="block",
            )
            == "block"
        )
        assert (
            _resolve_rollout_mode_for_section(
                scorecard={
                    "governance": {
                        "growth_section_gate_rollout": {
                            "default_mode": "nope",
                            "warn_until_by_section": "bad",
                        }
                    }
                },
                section_key="file_size_limits",
                today=today,
                fallback_mode="block",
            )
            == "block"
        )

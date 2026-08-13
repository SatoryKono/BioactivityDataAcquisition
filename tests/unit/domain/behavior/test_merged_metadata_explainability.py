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
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for merged metadata explainability behavior."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from bioetl.domain.behavior.merged_metadata_explainability import (
    MergedMetadataExplainer,
    _safe_ratio,
    create_merged_metadata_explainability_service,
)
from bioetl.domain.models.metadata import CompositeOutputExt

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_ROOT = _REPO_ROOT / "src"
# Keep Windows/process essentials only. Inheriting full PyCharm/pytest env is a
# common source of child-process hangs (debugger hooks, plugin path injection).
_SUBPROCESS_ENV_KEYS = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
)
_SUBPROCESS_TIMEOUT_SECONDS = 30


def _clean_subprocess_env(*, hash_seed: str) -> dict[str, str]:
    env = {key: value for key in _SUBPROCESS_ENV_KEYS if (value := os.environ.get(key))}
    # -I ignores PYTHON* env vars; keep these for non-isolated fallbacks and
    # explicit documentation of intended isolation policy.
    env["PYTHONHASHSEED"] = hash_seed
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONUTF8"] = "1"
    return env


def _run_record_id_subprocess(code: str, *, hash_seed: str = "0") -> str:
    """Run pure record-id code in an isolated interpreter.

    Uses ``python -I`` so parent PYTHONPATH / PyCharm / pytest env cannot stall
    child startup. Source tree is injected explicitly via ``sys.path``.
    """
    bootstrap = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(_SRC_ROOT)!r})
        """
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", bootstrap + code],
        capture_output=True,
        cwd=_REPO_ROOT,
        env=_clean_subprocess_env(hash_seed=hash_seed),
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "record_id subprocess failed "
            f"(rc={completed.returncode}, seed={hash_seed}):\n"
            f"stdout={completed.stdout!r}\n"
            f"stderr={completed.stderr!r}"
        )
    record_id = completed.stdout.strip()
    if not record_id:
        raise AssertionError(
            "record_id subprocess produced empty stdout "
            f"(seed={hash_seed}): stderr={completed.stderr!r}"
        )
    return record_id


def _metadata() -> CompositeOutputExt:
    return CompositeOutputExt(
        composite_run_id="run-1",
        source_providers=["chembl", "pubmed"],
        enrichment_status={"mesh": "applied", "openalex": "skipped"},
    )


def test_field_explanation_uses_priority_and_applied_enrichments() -> None:
    explainer = create_merged_metadata_explainability_service()

    explanation = explainer.generate_field_explanation(
        "title",
        {"title": "Aspirin"},
        _metadata(),
        {"title": {"priority": ["pubmed", "chembl"]}},
    )

    assert explanation.field_name == "title"
    assert explanation.source_providers == ["chembl", "pubmed"]
    assert explanation.priority_order == ["pubmed", "chembl"]
    # Priority order is highest-first, so "pubmed" should be the final value source
    assert explanation.final_value_source == "pubmed"
    assert explanation.conflict_resolution == "priority_based"
    assert explanation.enrichment_applied == ["mesh"]


def test_field_explanation_handles_missing_priority_and_enrichment() -> None:
    explanation = MergedMetadataExplainer().generate_field_explanation(
        "title",
        {"title": "Aspirin"},
        CompositeOutputExt(source_providers=[]),
        {"title": {"priority": "pubmed"}},
    )

    assert explanation.priority_order == []
    assert explanation.final_value_source is None
    assert explanation.conflict_resolution is None
    assert explanation.enrichment_applied is None


def test_record_explanation_ignores_private_fields_and_counts_conflicts() -> None:
    explanation = MergedMetadataExplainer().generate_record_explanation(
        "record-1",
        {"title": "Aspirin", "_internal": "hidden"},
        _metadata(),
        {"title": {"priority": ["chembl"]}},
        merge_strategy="custom",
    )

    assert explanation.record_id == "record-1"
    assert explanation.composite_run_id == "run-1"
    assert [field.field_name for field in explanation.field_explanations] == ["title"]
    assert explanation.conflict_count == 1
    assert explanation.enrichment_count == 1
    assert explanation.merge_strategy == "custom"


def test_generate_explainability_metadata_resolves_record_ids() -> None:
    explanations = MergedMetadataExplainer().generate_explainability_metadata(
        [
            {"_record_id": "explicit", "title": "A"},
            {"id": "id-field", "title": "B"},
            {"molecule_id": "CHEMBL25", "title": "C"},
            {"title": "D"},
        ],
        _metadata(),
    )

    assert [item.record_id for item in explanations[:3]] == [
        "explicit",
        "id-field",
        "CHEMBL25",
    ]
    assert explanations[3].record_id


def test_record_id_fallback_is_stable_for_equivalent_record_order() -> None:
    explainer = MergedMetadataExplainer()

    first = explainer.generate_explainability_metadata(
        [{"title": "D", "doi": "10.1/example"}],
        _metadata(),
    )
    second = explainer.generate_explainability_metadata(
        [{"doi": "10.1/example", "title": "D"}],
        _metadata(),
    )

    assert first[0].record_id == second[0].record_id
    assert len(first[0].record_id) == 64


@pytest.mark.unit
@pytest.mark.subprocess_backed
@pytest.mark.timeout(45)
def test_record_id_fallback_is_stable_across_python_processes() -> None:
    """Fallback record_id must not depend on interpreter PYTHONHASHSEED.

    Spawns isolated children (``python -I`` + scrubbed env) so PyCharm/pytest
    parent env cannot hang pipe readers or inject import side-effects.
    """
    code = textwrap.dedent(
        """
        from bioetl.domain.behavior.merged_metadata_explainability import (
            MergedMetadataExplainer,
        )
        from types import SimpleNamespace

        explanation = MergedMetadataExplainer().generate_explainability_metadata(
            [{"doi": "10.1/example", "title": "D"}],
            SimpleNamespace(
                composite_run_id="run-1",
                source_providers=[],
                enrichment_status={},
            ),
        )[0]
        print(explanation.record_id, end="")
        """
    )

    # Distinct hash seeds prove determinism beyond "same process twice".
    first = _run_record_id_subprocess(code, hash_seed="0")
    second = _run_record_id_subprocess(code, hash_seed="1")

    assert first == second
    assert len(first) == 64
    assert all(ch in "0123456789abcdef" for ch in first)


def test_summary_reports_empty_and_non_empty_distributions() -> None:
    explainer = MergedMetadataExplainer()

    assert explainer.generate_explainability_summary([]) == {
        "record_count": 0,
        "field_count": 0,
        "avg_fields_per_record": 0.0,
        "source_provider_distribution": {},
        "merge_strategy_distribution": {},
        "conflict_summary": {
            "total_conflicts": 0,
            "conflict_rate": 0.0,
            "records_with_conflicts": 0,
        },
        "enrichment_summary": {
            "total_enrichments": 0,
            "enrichment_rate": 0.0,
            "records_with_enrichments": 0,
        },
    }

    explanations = explainer.generate_explainability_metadata(
        [{"title": "A"}, {"title": "B"}],
        _metadata(),
        {"title": {"priority": ["chembl"]}},
    )
    summary = explainer.generate_explainability_summary(explanations)

    assert summary["record_count"] == 2
    assert summary["field_count"] == 2
    assert summary["avg_fields_per_record"] == 1.0
    assert summary["source_provider_distribution"] == {"chembl": 2, "pubmed": 2}
    assert summary["merge_strategy_distribution"] == {"prioritize": 2}
    assert summary["conflict_summary"]["records_with_conflicts"] == 2
    assert summary["enrichment_summary"]["records_with_enrichments"] == 2


def test_field_priority_explanation_defaults_are_stable() -> None:
    explanation = MergedMetadataExplainer().generate_field_priority_explanation(
        {"title": {"priority": ["pubmed"], "source": "config"}}
    )

    assert explanation == [
        {
            "field_name": "title",
            "priority_order": ["pubmed"],
            "source": "config",
            "fallback_strategy": "keep_first",
            "conflict_resolution": "priority_based",
        }
    ]
    assert _safe_ratio(1, 0) == 0.0

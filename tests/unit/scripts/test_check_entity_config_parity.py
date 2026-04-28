"""Unit tests for the active config/spec parity gate."""

from __future__ import annotations

from pathlib import Path

import scripts.check_entity_config_parity as parity_module


def _write_entity_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "version: 1.0.0",
                "provider: chembl",
                "entity: activity",
                "status: active",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_spec(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_check_spec_status_fails_for_historical_page_role_markers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    entities_dir = tmp_path / "configs" / "entities"
    pipelines_dir = tmp_path / "docs" / "04-reference" / "pipelines"
    _write_entity_config(entities_dir / "chembl" / "activity.yaml")
    _write_spec(
        pipelines_dir / "chembl" / "05-activity-spec.md",
        "\n".join(
            [
                "# Activity",
                "> **Status**: Historical deep spec. Current canonical contract lives in",
                "| Published-page role | Pass | Historical deep spec or summary"
                " is explicitly bounded by current canonical sources |,",
            ]
        ),
    )

    monkeypatch.setattr(parity_module, "ENTITIES_DIR", entities_dir)
    monkeypatch.setattr(parity_module, "PIPELINES_DIR", pipelines_dir)

    checker = parity_module.ParityChecker()
    checker.check_spec_status()

    assert checker.issues == [
        "Active pipeline spec still advertises itself as a historical/legacy "
        "surface for chembl/activity: "
        f"{pipelines_dir / 'chembl' / '05-activity-spec.md'}"
    ]


def test_check_spec_status_allows_canonical_compact_summary_language(
    tmp_path: Path,
    monkeypatch,
) -> None:
    entities_dir = tmp_path / "configs" / "entities"
    pipelines_dir = tmp_path / "docs" / "04-reference" / "pipelines"
    _write_entity_config(entities_dir / "chembl" / "activity.yaml")
    _write_spec(
        pipelines_dir / "chembl" / "05-activity-spec.md",
        "\n".join(
            [
                "# Activity",
                "> **Status**: Canonical compact spec summary. Current detailed contract lives in",
                "| Published-page role | Pass | Canonical compact summary"
                " is explicitly bounded by current canonical sources |",
                "Legacy hyphenated field names remain historical only and should not be used in new configs.",
            ]
        ),
    )

    monkeypatch.setattr(parity_module, "ENTITIES_DIR", entities_dir)
    monkeypatch.setattr(parity_module, "PIPELINES_DIR", pipelines_dir)

    checker = parity_module.ParityChecker()
    checker.check_spec_status()

    assert checker.issues == []

"""The opt-in presentation must preserve evidence and reject stale builds."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts.ops.observability.grafana.dashboard_presentation import dashboard_directory
from scripts.ops.observability.grafana.generate_adaptive_dashboards import generate
from scripts.ops.observability.grafana.start_adaptive_monitoring import verify_bundle

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[5]


def _panels(payload: dict) -> dict:
    result = {}
    pending = list(payload["panels"])
    while pending:
        panel = pending.pop()
        result[panel["id"]] = panel
        pending.extend(panel.get("panels", []))
    return result


@pytest.fixture
def profile(tmp_path):
    for directory in ("dashboards", "provisioning/dashboards"):
        shutil.copytree(ROOT / "grafana" / directory, tmp_path / "grafana" / directory)
    assert generate(tmp_path)
    return tmp_path


def test_generated_presentation_preserves_queries_identity_links_and_native_inputs(
    profile,
):
    for source in (profile / "grafana/dashboards").glob("*.json"):
        assert (
            source.read_bytes()
            == (ROOT / "grafana/dashboards" / source.name).read_bytes()
        )
        native = _panels(json.loads(source.read_text(encoding="utf-8")))
        adaptive = _panels(
            json.loads(
                (profile / "grafana/dashboards-adaptive" / source.name).read_text(
                    encoding="utf-8"
                )
            )
        )
        assert native.keys() == adaptive.keys()
        for identity, panel in native.items():
            for key in (
                "targets",
                "transformations",
                "fieldConfig",
                "datasource",
                "links",
                "gridPos",
            ):
                assert panel.get(key) == adaptive[identity].get(key), (
                    source.name,
                    identity,
                    key,
                )
        assert all(
            panel["type"] != "bioetl-selectorshell-panel" for panel in native.values()
        )


@pytest.mark.parametrize("surface", ["source", "derived", "provider"])
def test_check_detects_drift_without_rewriting_it(profile, surface):
    directory = {
        "source": "dashboards",
        "derived": "dashboards-adaptive",
        "provider": "provisioning/dashboards-adaptive",
    }[surface]
    target = next((profile / "grafana" / directory).glob("*"))
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    before = target.read_bytes()
    assert not generate(profile, check=True)
    assert target.read_bytes() == before


def test_native_default_needs_no_optional_plugin(profile, monkeypatch):
    monkeypatch.delenv("BIOETL_GRAFANA_PRESENTATION_PROFILE", raising=False)
    assert dashboard_directory(profile) == profile / "grafana/dashboards"
    monkeypatch.setenv("BIOETL_GRAFANA_PRESENTATION_PROFILE", "unknown")
    with pytest.raises(ValueError, match="native or adaptive"):
        dashboard_directory(profile)


@pytest.fixture
def bundle(tmp_path):
    path = tmp_path / "grafana/plugins/bioetl-selectorshell-panel/dist-adaptive"
    path.mkdir(parents=True)
    (path / "plugin.json").write_text(
        json.dumps(
            {
                "id": "bioetl-selectorshell-panel",
                "type": "panel",
                "info": {"keywords": ["adaptive-table-v1"]},
            }
        )
    )
    (path / "module.js").write_text("source-bound output")
    inputs = {}
    for name in (
        "src/components/AdaptiveTable.tsx",
        "src/adaptive-module.ts",
        "package-lock.json",
        "webpack.adaptive.config.ts",
        "adaptive-build-provenance.ts",
    ):
        target = path.parent / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("input")
        inputs[target.relative_to(tmp_path).as_posix()] = hashlib.sha256(
            b"input"
        ).hexdigest()
    receipt = {
        "capability": "adaptive-table-v1",
        "inputs_sha256_lf": inputs,
        "outputs_sha256": {
            file.name: hashlib.sha256(file.read_bytes()).hexdigest()
            for file in path.iterdir()
        },
    }
    (path / "build-provenance.json").write_text(json.dumps(receipt))
    return tmp_path, path


@pytest.mark.parametrize("change", ["input", "output", "extra", "missing"])
def test_compiler_receipt_rejects_changed_source_or_bundle(bundle, change):
    root, path = bundle
    assert verify_bundle(root)["capability"] == "adaptive-table-v1"
    if change == "input":
        (path.parent / "src/adaptive-module.ts").write_text("changed")
    elif change == "output":
        (path / "module.js").write_text("changed")
    elif change == "extra":
        (path / "unexpected.js").write_text("injected")
    else:
        (path / "module.js").unlink()
    with pytest.raises(ValueError):
        verify_bundle(root)


@pytest.mark.parametrize(
    "passport",
    [
        None,
        "",
        "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/configs/workflows/chembl_core.yaml",
    ],
)
def test_missing_workflow_passport_uses_real_reference_instead_of_a_no_value_url(
    passport,
):
    from tests.unit.scripts.ops.observability.test_overview_donor_jsonata import (
        evaluate_donor,
    )

    source = json.loads(
        (ROOT / "grafana/dashboards/bioetl-run-explorer-v1.json").read_text(
            encoding="utf-8"
        )
    )
    expression = _panels(source)[3010]["targets"][0]["root_selector"]
    item = {
        "pipeline": "chembl_assay",
        "run_id": "exact-id",
        "workflow_passport_url": passport,
    }
    actual = evaluate_donor(
        {"index_state": "ok", "items": [item]}, expression=expression
    )
    if isinstance(actual, list):
        actual = actual[0]
    expected = (
        passport.split("BioactivityDataAcquisition/", 1)[1]
        if passport
        else "blob/main/docs/03-guides/workflows.md"
    )
    assert actual["workflow_passport_path"] == expected

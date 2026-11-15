"""Candidate qualification boundaries without Docker, network or service I/O."""

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.ops.observability.grafana import router_candidate as candidate

DIGEST = "a" * 64
HOST = "satorykono/bioetl-grafana-router7-canvas@sha256:" + DIGEST
MANAGED = HOST.replace(DIGEST, "b" * 64)


def case():
    image = {
        "Id": "sha256:" + DIGEST,
        "RepoDigests": [HOST],
        "Architecture": "amd64",
        "Os": "linux",
        "Config": {"User": "grafana"},
        "RootFS": {
            "Type": "layers",
            "Layers": ["sha256:" + "c" * 64, "sha256:" + DIGEST],
        },
    }
    base = {"RootFS": {"Type": "layers", "Layers": ["sha256:" + "c" * 64]}}
    plugins = {
        p: {"module.js": DIGEST, "plugin.json": DIGEST, "module.js.map": DIGEST}
        for p in candidate.PLUGINS
    }
    files = {
        f"usr/share/grafana/data/plugins-bundled/{p}/{name}": [
            "0",
            292,
            0,
            0,
            "",
            0,
            0,
            digest,
            {},
        ]
        for p, values in plugins.items()
        for name, digest in values.items()
    }
    files["usr/share/grafana/public/build/index.js"] = [
        "0",
        292,
        0,
        0,
        "",
        0,
        0,
        DIGEST,
        {},
    ]
    return (
        image,
        copy.deepcopy(image),
        base,
        files,
        copy.deepcopy(files),
        plugins,
        HOST,
    )


class CandidateQualification(unittest.TestCase):
    def test_receipt_replacement_failure_preserves_previous_bytes(self):
        for operation in ("fsync", "replace"):
            with (
                self.subTest(operation=operation),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                target = root / "reports/qa/receipt.json"
                target.parent.mkdir(parents=True)
                target.write_bytes(b"original receipt")
                with (
                    patch.object(candidate, "ROOT", root),
                    patch.object(
                        candidate.os,
                        operation,
                        side_effect=OSError("injected interruption"),
                    ),
                ):
                    with self.assertRaises(OSError):
                        candidate.write_output("receipt.json", b"replacement")
                self.assertEqual(target.read_bytes(), b"original receipt")
                self.assertEqual(list(target.parent.iterdir()), [target])

    def test_existing_image_verifier_routes_candidate_stages_explicitly(self):
        with patch.object(candidate, "main") as verify:
            candidate.native.main(["--candidate-stage", "inputs"])
        verify.assert_called_once_with(["--stage", "inputs"])

    def test_cli_rejects_bad_input_before_inspection_or_export(self):
        with (
            patch.dict(
                os.environ,
                {
                    "BIOETL_QUALIFICATION_TARGET": "candidate",
                    "BIOETL_CANDIDATE_HOST_IMAGE": "--privileged",
                    "BIOETL_CANDIDATE_MANAGED_IMAGE": MANAGED,
                },
            ),
            patch.object(
                candidate.native, "inspect", side_effect=AssertionError("No Docker")
            ),
            patch.object(
                candidate.native, "records", side_effect=AssertionError("No export")
            ),
        ):
            with self.assertRaisesRegex(ValueError, "immutable candidate"):
                candidate.main(["--stage", "host"])

    def test_new_candidate_qualifies_without_relabelling_previous_delivery(self):
        values = case()
        original = copy.deepcopy(values)
        result = candidate.verify_host(*values)
        assert result["qualification_target"] == "candidate"
        assert result["declared_image"] == HOST
        assert result["rebuilt_plugin_files_verified"] == dict.fromkeys(
            candidate.PLUGINS, 3
        )
        assert values == original
        assert set(result["artifacts"]) == candidate.SCOPES

    def test_invalid_inputs_fail_before_any_docker_operation(self):
        for mode, host, managed in [
            ("unknown", HOST, MANAGED),
            ("declared_delivery", HOST, ""),
            ("candidate", HOST, HOST),
            ("candidate", HOST, ""),
            ("candidate", "--privileged", MANAGED),
            ("candidate", HOST + "\n", MANAGED),
            ("candidate", HOST.replace("satorykono", "foreign"), MANAGED),
        ]:
            with self.subTest(mode=mode, host=host, managed=managed):
                with patch.object(
                    candidate.native, "inspect", side_effect=AssertionError("No Docker")
                ):
                    with self.assertRaises(ValueError):
                        candidate.inputs(mode, host, managed)

    def test_declared_delivery_defaults_and_distinct_owned_candidates(self):
        candidate.inputs("declared_delivery", "", "")
        candidate.inputs("candidate", HOST, MANAGED)

    def test_full_filesystem_changes_never_pass(self):
        for defect in ["bytes", "owner", "mode", "symlink", "extra", "missing_map"]:
            with self.subTest(defect=defect):
                values = list(case())
                path = next(p for p in values[4] if p.endswith("module.js.map"))
                row = values[4][path]
                if defect == "extra":
                    values[4]["unexpected"] = row
                elif defect == "missing_map":
                    del values[4][path]
                else:
                    index, value = {
                        "bytes": (7, "d" * 64),
                        "owner": (2, 1000),
                        "mode": (1, 438),
                        "symlink": (0, "2"),
                    }[defect]
                    row[index] = value
                with self.assertRaisesRegex(
                    ValueError, "Complete candidate filesystem"
                ):
                    candidate.verify_host(*values)

    def test_original_ci_plugin_artifacts_must_match_all_image_files(self):
        for defect in ["different_map", "missing_map", "extra_file"]:
            with self.subTest(defect=defect):
                values = list(case())
                plugin = values[5][candidate.PLUGINS[0]]
                if defect == "different_map":
                    plugin["module.js.map"] = "e" * 64
                elif defect == "missing_map":
                    del plugin["module.js.map"]
                else:
                    plugin["unexpected.js"] = DIGEST
                with self.assertRaisesRegex(
                    ValueError, "Complete rebuilt plugin mismatch"
                ):
                    candidate.verify_host(*values)

    def test_candidate_cannot_bypass_trust_or_runtime_boundaries(self):
        for defect in [
            "base",
            "config",
            "digest",
            "empty_layers",
            "image_id",
            "platform",
        ]:
            with self.subTest(defect=defect):
                values = list(case())
                if defect == "base":
                    values[2]["RootFS"]["Layers"] = ["sha256:" + "e" * 64]
                elif defect == "config":
                    values[1]["Config"]["User"] = "root"
                elif defect == "digest":
                    values[1]["RepoDigests"] = []
                elif defect == "empty_layers":
                    values[0]["RootFS"]["Layers"] = []
                elif defect == "image_id":
                    values[0]["Id"] = "--privileged"
                else:
                    values[0]["Os"] = values[1]["Os"] = "windows"
                with self.assertRaises(ValueError):
                    candidate.verify_host(*values)

    def test_managed_recipe_rebind_is_a_generated_copy_only(self):
        recipe = (
            "# Original\nFROM "
            + HOST
            + "\nUSER root\nRUN remove-scenes\nUSER grafana\n"
        ).encode()
        manifest = {
            "parent_image": HOST,
            "dockerfile_sha256": hashlib.sha256(recipe).hexdigest(),
        }
        before = copy.deepcopy(manifest)
        result = candidate.candidate_recipe(recipe, manifest, MANAGED)
        assert result.replace(MANAGED.encode(), HOST.encode()) == recipe
        assert manifest == before
        with self.assertRaisesRegex(ValueError, "recipe source"):
            candidate.candidate_recipe(recipe + b"USER root\n", manifest, MANAGED)

    def test_candidate_plugin_capture_requires_module_metadata_and_release_date(self):
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            (tmp_path / "module.js").write_bytes(b"candidate")
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                candidate.build_files(tmp_path, "2026-10-03")
            (tmp_path / "plugin.json").write_text(
                json.dumps({"info": {"updated": "2026-10-03"}})
            )
            (tmp_path / "module.js.map").write_bytes(b"full debug map")
            assert set(candidate.build_files(tmp_path, "2026-10-03")) == {
                "module.js",
                "plugin.json",
                "module.js.map",
            }
            with self.assertRaisesRegex(ValueError, "date mismatch"):
                candidate.build_files(tmp_path, "2099-01-01")


if __name__ == "__main__":
    unittest.main()
import pytest

pytestmark = pytest.mark.unit


def test_workflow_routes_default_and_candidate_through_complete_existing_gates():
    import yaml

    root = Path(__file__).resolve().parents[4]
    workflow = yaml.safe_load(
        (root / ".github/workflows/router-v7-bridge.yml").read_text()
    )
    dispatch = workflow.get("on", workflow.get(True))["workflow_dispatch"]["inputs"]
    assert dispatch["qualification_target"]["default"] == "declared_delivery"
    jobs = workflow["jobs"]
    assert jobs["host-build"]["needs"] == "plugin-tests"
    plugin_steps = jobs["plugin-tests"]["steps"]
    old = next(
        s
        for s in plugin_steps
        if s["name"] == "Verify built bundle against shipped host manifest"
    )
    assert old["if"] == "${{ inputs.qualification_target != 'candidate' }}"
    for required in [
        "npm audit",
        "npm run typecheck",
        "npm run lint",
        "npm run test:ci",
    ]:
        assert any(required in s.get("run", "") and "if" not in s for s in plugin_steps)
    host_steps = jobs["host-build"]["steps"]
    candidate_step = next(
        s for s in host_steps if s["name"] == "Verify complete candidate host parity"
    )
    assert candidate_step["if"] == "${{ inputs.qualification_target == 'candidate' }}"
    assert "--candidate-stage host" in candidate_step["run"]
    managed = next(
        s
        for s in host_steps
        if s["name"] == "Build and verify managed image from the qualified parent"
    )["run"]
    assert (
        "--candidate-stage managed" in managed
        and "verify-router-managed-image" in managed
    )

"""Candidate qualification boundaries without Docker, network or service I/O."""

import copy
import hashlib
import json
import os
import subprocess
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


class BuildMetadataFormats(unittest.TestCase):
    """Both trusted Buildx driver formats must bind to the actual inspected ID."""

    def test_metadata_schema_never_substitutes_a_manifest_or_conflicting_config(self):
        config = "sha256:" + "a" * 64
        manifest = "sha256:" + "b" * 64
        cases = (
            ({"containerimage.config.digest": config}, True),
            (
                {
                    "containerimage.config.digest": config,
                    "containerimage.digest": manifest,
                },
                True,
            ),
            ({"containerimage.digest": config}, True),
            ({"containerimage.digest": manifest}, False),
            (
                {
                    "containerimage.config.digest": manifest,
                    "containerimage.digest": config,
                },
                False,
            ),
            (
                {"containerimage.config.digest": None, "containerimage.digest": config},
                False,
            ),
            ({}, False),
        )
        for metadata, expected in cases:
            with self.subTest(metadata=metadata):
                before = copy.deepcopy(metadata)
                self.assertEqual(
                    candidate.build_matches_config(metadata, config), expected
                )
                self.assertEqual(metadata, before)
        self.assertFalse(
            candidate.build_matches_config(
                {"containerimage.digest": "invalid"}, "invalid"
            )
        )

    def test_inspected_build_supports_both_schemas_without_mutating_raw_metadata(self):
        config = "sha256:" + "a" * 64
        other = "sha256:" + "b" * 64
        for metadata, accepted in (
            ({"containerimage.config.digest": config}, True),
            ({"containerimage.digest": config}, True),
            (
                {
                    "containerimage.config.digest": other,
                    "containerimage.digest": config,
                },
                False,
            ),
            ({"containerimage.digest": other}, False),
        ):
            with (
                self.subTest(metadata=metadata),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary).resolve()
                target = root / "reports/qa/build.json"
                target.parent.mkdir(parents=True)
                raw = json.dumps(metadata).encode()
                target.write_bytes(raw)
                with (
                    patch.object(candidate, "ROOT", root),
                    patch.object(candidate, "docker_path", return_value="MOCK_DOCKER"),
                    patch.object(
                        candidate.subprocess, "check_output", return_value=config + "\n"
                    ),
                    patch.object(
                        candidate.native, "inspect", return_value={"Id": config}
                    ),
                ):
                    if accepted:
                        self.assertEqual(
                            candidate.inspect_build("synthetic:build", "build.json"),
                            {"Id": config},
                        )
                    else:
                        with self.assertRaisesRegex(
                            ValueError, "Build metadata image mismatch"
                        ):
                            candidate.inspect_build("synthetic:build", "build.json")
                self.assertEqual(target.read_bytes(), raw)


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
                    "BIOETL_PRODUCER_SOURCE_SHA": "",
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


class ProducerBoundaries(unittest.TestCase):
    """Producer outputs cannot substitute for published-image qualification."""

    def test_source_bound_producer_rejects_registry_inputs_and_bad_sha(self):
        candidate.inputs("produce_candidate", "", "", "c" * 40)
        invalid = [
            ("produce_candidate", HOST, "", "c" * 40),
            ("produce_candidate", "", MANAGED, "c" * 40),
            ("produce_candidate", "", "", ""),
            ("produce_candidate", "", "", "c" * 39),
            ("produce_candidate", "", "", "C" * 40),
            ("produce_candidate", "", "", "c" * 40 + "\n"),
            ("declared_delivery", "", "", "c" * 40),
            ("candidate", HOST, MANAGED, "c" * 40),
        ]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                candidate.inputs(*values)

    def test_producer_never_enters_image_qualification_or_writes_parity(self):
        with (
            patch.dict(
                os.environ,
                {
                    "BIOETL_QUALIFICATION_TARGET": "produce_candidate",
                    "BIOETL_PRODUCER_SOURCE_SHA": "c" * 40,
                    "BIOETL_CANDIDATE_HOST_IMAGE": "",
                    "BIOETL_CANDIDATE_MANAGED_IMAGE": "",
                },
            ),
            patch.object(
                candidate.native, "inspect", side_effect=AssertionError("No Docker")
            ),
            patch.object(
                candidate.native, "records", side_effect=AssertionError("No Docker")
            ),
            patch.object(
                candidate,
                "write_output",
                side_effect=AssertionError("No parity receipt"),
            ),
        ):
            candidate.main(["--stage", "inputs"])
            for stage in ("host", "managed", "recipe"):
                with (
                    self.subTest(stage=stage),
                    self.assertRaisesRegex(ValueError, "explicit candidate mode"),
                ):
                    candidate.main(["--stage", stage])

    def test_producer_plugin_validation_still_requires_original_build_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            owner = root / "owner"
            owner.mkdir()
            (owner / "host-image.json").write_text(
                json.dumps({"plugin_release_date": "2026-10-03"})
            )
            plugin = candidate.PLUGINS[0]
            with (
                patch.object(candidate, "ROOT", root),
                patch.object(candidate, "OWNER", owner),
                patch.dict(
                    os.environ,
                    {
                        "BIOETL_QUALIFICATION_TARGET": "produce_candidate",
                        "BIOETL_PRODUCER_SOURCE_SHA": "c" * 40,
                        "BIOETL_CANDIDATE_HOST_IMAGE": "",
                        "BIOETL_CANDIDATE_MANAGED_IMAGE": "",
                        "BIOETL_PLUGIN": plugin,
                    },
                ),
            ):
                with self.assertRaisesRegex(ValueError, "Missing/redirected"):
                    candidate.main(["--stage", "plugin"])
                dist = root / "grafana/plugins" / plugin / "dist"
                dist.mkdir(parents=True)
                (dist / "module.js").write_bytes(b"synthetic plugin")
                (dist / "plugin.json").write_text(
                    json.dumps({"info": {"updated": "2026-10-03"}})
                )
                candidate.main(["--stage", "plugin"])


class ProducerExport(unittest.TestCase):
    """Execute the workflow exporter against tiny fixtures with all commands mocked."""

    def exporter(self):
        import textwrap

        root = Path(__file__).resolve().parents[4]
        workflow = (root / ".github/workflows/router-v7-bridge.yml").read_text()
        marker = "      - name: Export immutable build products as explicitly unqualified evidence\n"
        tail = workflow.split(marker, 1)[1]
        body = tail.split("          python3 - <<'PY'\n", 1)[1].split(
            "\n          PY", 1
        )[0]
        return compile(textwrap.dedent(body), "workflow-producer-export", "exec")

    def run_export(self, defect=None, metadata_key="containerimage.config.digest"):
        from scripts.ops.observability.grafana import trusted_docker

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            qa = root / "reports/qa"
            qa.mkdir(parents=True)
            context = qa / "router-v7-image-context"
            context.mkdir()
            (context / "Dockerfile.host").write_bytes(b"FROM synthetic-base\n")
            (context / "host-build").mkdir()
            (context / "host-build/main.js").write_bytes(b"synthetic frontend")
            recipe = qa / "router-v7-managed-context/Dockerfile"
            recipe.parent.mkdir()
            recipe.write_bytes(b"FROM bioetl-router-host:acceptance\n")
            for plugin in candidate.PLUGINS:
                for parent in (context / plugin, root / "grafana/plugins" / plugin):
                    parent.mkdir(parents=True)
                for name in ("module.js", "module.js.map", "plugin.json"):
                    (context / plugin / name).write_bytes(b"synthetic output")
                for name in ("package.json", "package-lock.json"):
                    (root / "grafana/plugins" / plugin / name).write_bytes(b"{}\n")
            ids = {"host": "sha256:" + "a" * 64, "managed": "sha256:" + "b" * 64}
            if defect == "same_images":
                ids["managed"] = ids["host"]
            for kind, name in (("host", "image"), ("managed", "managed-image")):
                (qa / ("router-v7-" + name + "-build.json")).write_text(
                    json.dumps({metadata_key: ids[kind]})
                )
            out = qa / "router-v7-unqualified-products"
            if defect == "destination_exists":
                out.mkdir()
            if defect == "missing_map":
                (context / candidate.PLUGINS[0] / "module.js.map").unlink()
            if defect == "missing_frontend":
                (context / "host-build/main.js").unlink()
            if defect == "missing_recipe":
                recipe.unlink()
            if defect == "hardlink":
                os.link(context / "Dockerfile.host", context / "host-build/linked")
            if defect == "hardlinked_recipe":
                os.link(recipe, recipe.parent / "linked")
            if defect == "missing_package":
                (
                    root
                    / "grafana/plugins"
                    / candidate.PLUGINS[0]
                    / "package-lock.json"
                ).unlink()
            calls = []
            head_calls = 0

            def check_output(argv, **kwargs):
                nonlocal head_calls
                calls.append(list(argv))
                if argv[:3] == ["git", "rev-parse", "HEAD"]:
                    head_calls += 1
                    return (
                        "d" if defect == "source_changed" and head_calls > 1 else "c"
                    ) * 40 + "\n"
                if argv[:2] == ["git", "ls-files"]:
                    return b"unexpected" if defect == "untracked" else b""
                if argv[:2] == ["git", "ls-tree"]:
                    return b"100644 blob synthetic\t.github/workflows/router-v7-bridge.yml\0"
                if argv[:3] == ["MOCK_DOCKER", "image", "inspect"]:
                    kind = "managed" if "managed" in argv[-1] else "host"
                    return (
                        "sha256:" + "e" * 64 if defect == "wrong_image" else ids[kind]
                    ) + "\n"
                raise AssertionError("Unexpected external command: " + repr(argv))

            def run(argv, **kwargs):
                calls.append(list(argv))
                if argv[:2] == ["git", "diff"]:
                    if defect == "dirty_source":
                        raise subprocess.CalledProcessError(1, argv)
                elif argv[:3] == ["MOCK_DOCKER", "image", "save"]:
                    if defect != "empty_save":
                        kwargs["stdout"].write(b"MOCK_ARCHIVE_NOT_A_REAL_IMAGE")
                else:
                    raise AssertionError("Unexpected external command: " + repr(argv))
                return subprocess.CompletedProcess(argv, 0)

            code = self.exporter()
            with (
                patch.dict(
                    os.environ,
                    {
                        "BIOETL_PRODUCER_SOURCE_SHA": "c" * 40,
                        "GITHUB_SHA": ("d" if defect == "wrong_ref" else "c") * 40,
                        "GITHUB_RUN_ID": "synthetic-run",
                        "GITHUB_RUN_ATTEMPT": "1",
                    },
                ),
                patch.object(Path, "cwd", return_value=root),
                patch.object(candidate, "ROOT", root),
                patch.object(trusted_docker, "docker_path", return_value="MOCK_DOCKER"),
                patch.object(subprocess, "check_output", side_effect=check_output),
                patch.object(subprocess, "run", side_effect=run),
            ):
                if defect:
                    with self.assertRaises(
                        (
                            AssertionError,
                            ValueError,
                            FileNotFoundError,
                            FileExistsError,
                            subprocess.CalledProcessError,
                        )
                    ):
                        exec(code, {"__name__": "synthetic_export"})
                    self.assertFalse((out / "build-products.json").exists())
                    return
                exec(code, {"__name__": "synthetic_export"})
            receipt = json.loads((out / "build-products.json").read_text())
            self.assertEqual(receipt["state"], "BUILT_UNQUALIFIED")
            self.assertNotIn("status", receipt)
            self.assertIsNone(receipt["published_registry_digests"])
            self.assertFalse(receipt["ci_image_parity_claimed"])
            self.assertFalse(receipt["runtime_acceptance_claimed"])
            self.assertEqual(receipt["local_config_ids"], ids)
            self.assertEqual(len(receipt["package_input_sha256"]), 4)
            self.assertIn("Dockerfile.managed", receipt["artifact_sha256"])
            for name, digest in receipt["artifact_sha256"].items():
                self.assertEqual(
                    hashlib.sha256((out / name).read_bytes()).hexdigest(), digest
                )
            self.assertEqual(head_calls, 2)
            self.assertTrue(calls)

    def test_complete_unqualified_export_preserves_hashes_and_boundaries(self):
        for key in ("containerimage.config.digest", "containerimage.digest"):
            with self.subTest(metadata_key=key):
                self.run_export(metadata_key=key)

    def test_bad_source_build_or_product_never_writes_success_receipt(self):
        for defect in (
            "destination_exists",
            "missing_map",
            "missing_frontend",
            "missing_recipe",
            "hardlink",
            "source_changed",
            "untracked",
            "wrong_image",
            "dirty_source",
            "empty_save",
            "wrong_ref",
            "same_images",
            "hardlinked_recipe",
            "missing_package",
        ):
            with self.subTest(defect=defect):
                self.run_export(defect)

    def test_unqualified_receipt_is_rejected_even_when_renamed_to_parity(self):
        import io
        import zipfile
        from scripts.ops.observability import (
            refresh_router_host_provenance as provenance,
        )

        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("router-v7-image-build.json", "{}")
            archive.writestr(
                "router-v7-image-parity.json",
                json.dumps({"state": "BUILT_UNQUALIFIED"}),
            )
        payloads = provenance._receipt_payloads(stream.getvalue())
        self.assertNotEqual(
            payloads["router-v7-image-parity.json"].get("status"), "PASS"
        )
        # The public validator rejects it after authenticating an original ZIP.
        source = "c" * 40
        run = {
            "id": 11,
            "head_sha": source,
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "success",
            "path": provenance.WORKFLOW,
            "event": "workflow_dispatch",
        }
        jobs = {
            "total_count": len(provenance.JOBS),
            "jobs": [
                {
                    "run_id": 11,
                    "head_sha": source,
                    "run_attempt": 1,
                    "name": name,
                    "status": "completed",
                    "conclusion": "success",
                    "started_at": "2026-10-31T12:00:00Z",
                    "completed_at": "2026-10-31T12:10:00Z",
                }
                for name in provenance.JOBS
            ],
        }
        raw = stream.getvalue()
        artifacts = {
            "total_count": 1,
            "artifacts": [
                {
                    "id": 12,
                    "name": provenance.ARTIFACT,
                    "expired": False,
                    "workflow_run": {"id": 11, "head_sha": source},
                    "created_at": "2026-10-31T12:09:00Z",
                    "size_in_bytes": len(raw),
                    "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "parity did not pass"):
            provenance.validate_capture(run, jobs, artifacts, raw)


class ProducerSourceBinding(unittest.TestCase):
    """Real Git path semantics; no mock substitutes for diff/ls-tree/ls-files."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="producer-binding-",
            dir=os.environ.get("BIOETL_TEST_GIT_FIXTURE_ROOT"),
        )
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.git_environment = dict(os.environ)
        for key in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        ):
            self.git_environment.pop(key, None)
        self.git_environment.update(
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_AUTHOR_NAME="Synthetic fixture",
            GIT_AUTHOR_EMAIL="fixture@example.invalid",
            GIT_COMMITTER_NAME="Synthetic fixture",
            GIT_COMMITTER_EMAIL="fixture@example.invalid",
        )
        empty = self.root / "empty-template"
        empty.mkdir()
        self.git("init", "--quiet", "--template=" + str(empty))
        self.files = {
            ".gitignore": b"ignored-cache/\n",
            ".gitattributes": b"* text=auto\n",
            "grafana/plugins/bioetl-scenes-app/src/module.ts": b"source\n",
            "grafana/plugins/bioetl-scenes-app/package.json": b"{}\n",
            "grafana/plugins/bioetl-scenes-app/package-lock.json": b"{}\n",
            "grafana/plugins/bioetl-scenes-app/webpack.config.ts": b"config\n",
            "grafana/plugins/bioetl-scenes-app/dist-neighbor/module.js": b"source\n",
            "grafana/plugins/unrelated/dist/module.js": b"source\n",
            "grafana/tooling/router-v7-bridge/bridge.ts": b"bridge\n",
            ".github/tooling/build.js": b"tooling\n",
            ".github/workflows/router-v7-bridge.yml": b"workflow\n",
            "scripts/ops/__main__.py": b"facade\n",
            "scripts/ops/observability/grafana/router_managed_image.py": b"verifier\n",
            "scripts/engineering/common/cli_dispatch.py": b"dispatcher\n",
            "tests/unit/scripts/ops/test_router_candidate.py": b"checks\n",
        }
        for plugin in candidate.PLUGINS:
            for name in ("module.js", "module.js.map"):
                self.files[f"grafana/plugins/{plugin}/dist/{name}"] = b"old output\n"
        for name, raw in self.files.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        self.git("add", "--", *self.files)
        self.git("commit", "--quiet", "-m", "Synthetic source only")
        self.source = self.git("rev-parse", "HEAD").strip()
        self.binding_root = patch.object(candidate, "ROOT", self.root)
        self.binding_root.start()
        self.addCleanup(self.binding_root.stop)
        self.clean_environment = patch.dict(
            os.environ, self.git_environment, clear=True
        )
        self.clean_environment.start()
        self.addCleanup(self.clean_environment.stop)

    def git(self, *args):
        return subprocess.check_output(
            [
                "git",
                "-c",
                "core.hooksPath=" + str(self.root / "empty-template"),
                "-c",
                "core.autocrlf=false",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=self.root,
            env=self.git_environment,
            text=True,
            stderr=subprocess.PIPE,
        )

    def test_only_two_generated_dist_trees_can_change_or_gain_untracked_files(self):
        expected = candidate.source_binding(self.source)
        for plugin in candidate.PLUGINS:
            for name in ("module.js", "module.js.map"):
                (self.root / f"grafana/plugins/{plugin}/dist/{name}").write_bytes(
                    b"new build\n"
                )
            (self.root / f"grafana/plugins/{plugin}/dist/new.chunk.js").write_bytes(
                b"chunk\n"
            )
        self.assertEqual(candidate.source_binding(self.source), expected)
        self.git("add", "--", *(f"grafana/plugins/{p}/dist" for p in candidate.PLUGINS))
        self.assertEqual(candidate.source_binding(self.source), expected)
        self.git("commit", "--quiet", "-m", "Only generated dist changed")
        new_source = self.git("rev-parse", "HEAD").strip()
        self.assertNotEqual(new_source, self.source)
        self.assertEqual(candidate.source_binding(new_source), expected)
        with self.assertRaisesRegex(ValueError, "Source changed"):
            candidate.source_binding(self.source)

    def test_tracked_source_workflow_and_facade_changes_are_rejected(self):
        source_paths = [
            name for name in self.files if "/dist/" not in name or "/unrelated/" in name
        ]
        for name in source_paths:
            with self.subTest(path=name):
                (self.root / name).write_bytes(b"changed input\n")
                with self.assertRaises(subprocess.CalledProcessError):
                    candidate.source_binding(self.source)
                self.git("add", "--", name)
                with self.assertRaises(subprocess.CalledProcessError):
                    candidate.source_binding(self.source)
                self.git("reset", "--quiet", "HEAD", "--", name)
                (self.root / name).write_bytes(self.files[name])

    def test_new_source_files_are_rejected_outside_exact_dist_exclusions(self):
        for name in (
            "grafana/plugins/bioetl-scenes-app/src/new.ts",
            "grafana/plugins/bioetl-selectorshell-panel/src/new.ts",
            "grafana/plugins/bioetl-scenes-app/dist-neighbor/new.js",
            "grafana/plugins/unrelated/dist/new.js",
            "grafana/tooling/router-v7-bridge/new.ts",
            ".github/tooling/new.js",
            "scripts/ops/new.py",
            "scripts/engineering/common/new.py",
            "tests/unit/scripts/ops/new.py",
        ):
            with self.subTest(path=name):
                p = self.root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"untracked input\n")
                try:
                    with self.assertRaisesRegex(ValueError, "Unexpected untracked"):
                        candidate.source_binding(self.source)
                finally:
                    p.unlink()

    def test_source_commit_changes_binding_even_with_generated_output_changes(self):
        before = candidate.source_binding(self.source)
        (self.root / "scripts/ops/__main__.py").write_bytes(b"new facade\n")
        self.git("add", "--", "scripts/ops/__main__.py")
        self.git("commit", "--quiet", "-m", "Changed checked source")
        after = candidate.source_binding(self.git("rev-parse", "HEAD").strip())
        self.assertNotEqual(after, before)


class ProducerModeDefaults(unittest.TestCase):
    """An empty event input must preserve strict delivery verification."""

    def test_empty_and_explicit_modes_validate_before_any_image_io(self):
        for raw, expected, host, managed, source in (
            (None, "declared_delivery", "", "", ""),
            ("", "declared_delivery", "", "", ""),
            ("declared_delivery", "declared_delivery", "", "", ""),
            ("candidate", "candidate", HOST, MANAGED, ""),
            ("produce_candidate", "produce_candidate", "", "", "c" * 40),
        ):
            with (
                self.subTest(raw=raw),
                patch.dict(
                    os.environ,
                    {
                        **(
                            {"BIOETL_QUALIFICATION_TARGET": raw}
                            if raw is not None
                            else {}
                        ),
                        "BIOETL_CANDIDATE_HOST_IMAGE": host,
                        "BIOETL_CANDIDATE_MANAGED_IMAGE": managed,
                        "BIOETL_PRODUCER_SOURCE_SHA": source,
                    },
                    clear=True,
                ),
                patch.object(candidate, "inputs", wraps=candidate.inputs) as validate,
                patch.object(
                    candidate.native, "inspect", side_effect=AssertionError("No Docker")
                ),
                patch.object(
                    candidate.native, "records", side_effect=AssertionError("No export")
                ),
                patch.object(
                    candidate, "write_output", side_effect=AssertionError("No receipt")
                ),
            ):
                candidate.main(["--stage", "inputs"])
                validate.assert_called_once_with(expected, host, managed, source)

    def test_unknown_mode_is_rejected_before_any_image_io(self):
        with (
            patch.dict(
                os.environ,
                {
                    "BIOETL_QUALIFICATION_TARGET": "unknown",
                    "BIOETL_CANDIDATE_HOST_IMAGE": "",
                    "BIOETL_CANDIDATE_MANAGED_IMAGE": "",
                    "BIOETL_PRODUCER_SOURCE_SHA": "",
                },
            ),
            patch.object(
                candidate.native, "inspect", side_effect=AssertionError("No Docker")
            ),
            patch.object(
                candidate, "write_output", side_effect=AssertionError("No receipt")
            ),
        ):
            with self.assertRaisesRegex(ValueError, "Invalid qualification target"):
                candidate.main(["--stage", "inputs"])


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
    assert (
        old["if"]
        == "${{ inputs.qualification_target != 'candidate' && inputs.qualification_target != 'produce_candidate' }}"
    )
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


def test_workflow_empty_pr_and_dispatch_mode_selection_preserves_strict_checks():
    """Evaluate actual string/boolean conditions against an independent mode table.

    This bounded evaluator supports only the operators used here. It is not a
    general replacement for GitHub's expression engine or a live workflow run.
    """
    import ast
    import yaml

    root = Path(__file__).resolve().parents[4]
    workflow = yaml.safe_load(
        (root / ".github/workflows/router-v7-bridge.yml").read_text()
    )

    def evaluate(expression, raw):
        text = expression.removeprefix("${{").removesuffix("}}").strip()
        text = (
            text.replace("inputs.qualification_target", "mode")
            .replace("&&", " and ")
            .replace("||", " or ")
        )
        tree = ast.parse(text, mode="eval")

        def visit(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                return node.value
            if isinstance(node, ast.Name) and node.id == "mode":
                return raw
            if isinstance(node, ast.BoolOp):
                result = visit(node.values[0])
                for value in node.values[1:]:
                    if isinstance(node.op, ast.And) and not result:
                        break
                    if isinstance(node.op, ast.Or) and result:
                        break
                    result = visit(value)
                return result
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                left, right = visit(node.left), visit(node.comparators[0])
                if isinstance(node.ops[0], ast.Eq):
                    return left == right
                if isinstance(node.ops[0], ast.NotEq):
                    return left != right
            raise AssertionError("Unsupported workflow expression: " + expression)

        return visit(tree.body)

    rows = (
        ("pull_request", None, "declared_delivery", True, False, False, False),
        ("pull_request", "", "declared_delivery", True, False, False, False),
        (
            "workflow_dispatch",
            "declared_delivery",
            "declared_delivery",
            True,
            False,
            False,
            False,
        ),
        ("workflow_dispatch", "candidate", "candidate", False, True, True, False),
        (
            "workflow_dispatch",
            "produce_candidate",
            "produce_candidate",
            False,
            True,
            False,
            True,
        ),
    )
    steps = {
        s.get("name"): s
        for job in workflow["jobs"].values()
        for s in job["steps"]
        if "name" in s
    }
    for event, raw, normalized, strict, output, image, produce in rows:
        assert (
            evaluate(workflow["env"]["BIOETL_QUALIFICATION_TARGET"], raw) == normalized
        ), event
        for name, expected in (
            ("Verify built bundle against shipped host manifest", strict),
            ("Verify built image against declared delivery image", strict),
            ("Validate complete original candidate plugin output", output),
            ("Verify complete candidate host parity", image),
            (
                "Generate scratch managed recipe from the freshly built local host",
                produce,
            ),
            (
                "Produce managed image without publishing or touching delivery pins",
                produce,
            ),
            (
                "Export immutable build products as explicitly unqualified evidence",
                produce,
            ),
            ("Build and verify managed image from the qualified parent", not produce),
        ):
            assert bool(evaluate(steps[name]["if"], raw)) == expected, (
                event,
                raw,
                name,
            )
    assert (
        evaluate(workflow["env"]["BIOETL_QUALIFICATION_TARGET"], "unknown") == "unknown"
    )
    for job in workflow["jobs"].values():
        index = next(
            i
            for i, s in enumerate(job["steps"])
            if s.get("name", "").startswith("Validate qualification inputs")
        )
        validation = job["steps"][index]
        assert (
            "if" not in validation and "--candidate-stage inputs" in validation["run"]
        )
        assert not validation.get("continue-on-error", False)

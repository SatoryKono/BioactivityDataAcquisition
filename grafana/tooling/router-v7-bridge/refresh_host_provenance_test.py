"""Isolated receipt/source controls; no Docker, network or production data."""

import copy
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "provenance", Path(__file__).with_name("refresh_host_provenance.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DIGEST = "a" * 64
IMAGE = "satorykono/bioetl-grafana-router7-canvas@sha256:" + DIGEST
promotion_spec = importlib.util.spec_from_file_location(
    "promotion", Path(__file__).with_name("promote_host_release.py")
)
promotion = importlib.util.module_from_spec(promotion_spec)
promotion_spec.loader.exec_module(promotion)


def fixture():
    run = {
        "id": 11,
        "head_sha": "b" * 40,
        "run_attempt": 1,
        "html_url": "https://github.com/example/fixture",
        "status": "completed",
        "conclusion": "success",
        "path": module.WORKFLOW,
        "event": "workflow_dispatch",
    }
    jobs = {
        "total_count": 4,
        "jobs": [
            {
                "run_id": 11,
                "head_sha": run["head_sha"],
                "run_attempt": 1,
                "name": name,
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-10-31T12:00:00Z",
                "completed_at": "2026-10-31T12:10:00Z",
            }
            for name in sorted(module.JOBS)
        ],
    }
    parity = {
        "status": "PASS",
        "declared_image": IMAGE,
        "rootfs_sha256": DIGEST,
        "built_image_config_digest": "sha256:" + DIGEST,
        "declared_image_config_digest": "sha256:" + DIGEST,
        "built_layers": ["sha256:" + DIGEST],
        "declared_layers": ["sha256:" + DIGEST],
        "artifacts": {
            scope: {"tree_sha256": DIGEST, "module_sha256": DIGEST}
            for scope in module.SCOPES
        },
    }
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(
            "router-v7-image-build.json",
            json.dumps({"containerimage.config.digest": "sha256:" + DIGEST}),
        )
        output.writestr("router-v7-image-parity.json", json.dumps(parity))
    raw = archive.getvalue()
    artifact = {
        "id": 12,
        "name": module.ARTIFACT,
        "expired": False,
        "workflow_run": {"id": 11, "head_sha": run["head_sha"]},
        "created_at": "2026-10-31T12:09:00Z",
        "size_in_bytes": len(raw),
        "digest": "sha256:" + module.sha256(raw),
    }
    manifest = {
        "image": IMAGE,
        "artifact_sha256": {
            f"grafana/plugins/{plugin}/dist/module.js": DIGEST
            for plugin in ("bioetl-scenes-app", "bioetl-selectorshell-panel")
        },
        "delivery_source": {
            "source_ref": "unchanged-history",
            "inputs": {"historical": DIGEST},
            "host_artifact_parity": {
                "image": IMAGE,
                "rootfs_sha256": DIGEST,
                "registry_config_digest": "sha256:" + DIGEST,
            },
        },
        "previous_revalidation": {"preserve": True},
    }
    return run, jobs, {"total_count": 1, "artifacts": [artifact]}, raw, manifest, parity


def release_case():
    run, _, artifacts, _, host, parity = fixture()
    old = IMAGE.replace(DIGEST, "c" * 64)
    old_managed = IMAGE.replace(DIGEST, "d" * 64)
    host["image"] = old
    host["delivery_source"]["host_artifact_parity"]["image"] = old
    for name in ("528.js.map", "module.js.map"):
        host["artifact_sha256"]["grafana/plugins/bioetl-scenes-app/dist/" + name] = (
            DIGEST
        )
    managed = {"image": old_managed, "parent_image": old}
    original = {
        promotion.HOST_PATH: json.dumps(host).encode(),
        promotion.MANAGED_PATH: json.dumps(managed).encode(),
        promotion.RECIPE_PATH: ("FROM " + old + "\nUSER grafana\n").encode(),
        **{
            path: (
                "services:\n  grafana:\n    image: "
                + (old if path.endswith("/compose.acceptance.yml") else old_managed)
                + "\n"
            ).encode()
            for path in promotion.COMPOSE_PATHS
        },
    }
    parity["qualification_target"] = "candidate"
    dist = dict(host["artifact_sha256"])
    for path in dist:
        if path.endswith(".js.map"):
            dist[path] = "e" * 64
    managed_receipt = {
        "status": "PASS",
        "scenes_installed": False,
        "parent_image": IMAGE,
        "declared_image": IMAGE.replace(DIGEST, "f" * 64),
        "rootfs_sha256": DIGEST,
    }
    return (
        original,
        run,
        artifacts["artifacts"][0],
        parity,
        {"source.js": DIGEST},
        "b" * 40,
        dist,
        managed_receipt,
        DIGEST,
    )


class ProvenanceControls(unittest.TestCase):
    def test_release_promotion_preserves_history_and_all_coupled_pins(self):
        case = release_case()
        outputs = promotion.build_release_files(*case)
        host = json.loads(outputs[promotion.HOST_PATH])
        managed = json.loads(outputs[promotion.MANAGED_PATH])
        original_host = json.loads(case[0][promotion.HOST_PATH])
        self.assertEqual(host["release_history"][0]["host_manifest"], original_host)
        self.assertEqual(host["image"], IMAGE)
        self.assertEqual(managed["parent_image"], IMAGE)
        self.assertEqual(
            managed["dockerfile_sha256"], module.sha256(outputs[promotion.RECIPE_PATH])
        )
        self.assertFalse(host["release_promotion"]["default_delivery_ci_claimed"])
        self.assertFalse(host["release_promotion"]["runtime_rollout_claimed"])
        for path in promotion.COMPOSE_PATHS:
            expected = (
                IMAGE if path.endswith("/compose.acceptance.yml") else managed["image"]
            )
            self.assertIn(expected.encode(), outputs[path])
        self.assertEqual(promotion.build_release_files(outputs, *case[1:]), outputs)
        for path in (*promotion.COMPOSE_PATHS, promotion.RECIPE_PATH):
            with self.subTest(tampered=path):
                corrupted = dict(outputs)
                corrupted[path] = corrupted[path].replace(
                    (
                        IMAGE
                        if path == promotion.RECIPE_PATH
                        or path.endswith("/compose.acceptance.yml")
                        else managed["image"]
                    ).encode(),
                    b"foreign/image:latest",
                )
                with self.assertRaises(ValueError):
                    promotion.build_release_files(corrupted, *case[1:])
        for mode in (
            "wrong_service",
            "duplicate_image",
            "duplicate_service",
            "duplicate_services",
            "commented_services",
            "quoted_services",
            "quoted_grafana",
            "quoted_image",
        ):
            with self.subTest(tampered=mode):
                corrupted = dict(outputs)
                path = promotion.COMPOSE_PATHS[0]
                text = corrupted[path].decode()
                if mode == "wrong_service":
                    text = text.replace("  grafana:", "  unrelated:")
                elif mode == "duplicate_image":
                    text += "    image: " + IMAGE + "\n"
                elif mode == "duplicate_service":
                    text += "  grafana:\n    image: " + IMAGE + "\n"
                elif mode == "commented_services":
                    text += "services: # replacement\n  grafana:\n    image: foreign/image:latest\n"
                elif mode == "quoted_services":
                    text += "'services':\n  grafana:\n    image: foreign/image:latest\n"
                elif mode == "quoted_grafana":
                    text += "  'grafana':\n    image: foreign/image:latest\n"
                elif mode == "quoted_image":
                    text += "    'image': foreign/image:latest\n"
                else:
                    text += "services:\n  grafana:\n    image: " + IMAGE + "\n"
                corrupted[path] = text.encode()
                with self.assertRaises(ValueError):
                    promotion.build_release_files(corrupted, *case[1:])

    def test_release_promotion_rejects_unqualified_sources_and_runtime_changes(self):
        for mode in (
            "failed_ci",
            "declared_mode",
            "foreign_image",
            "managed_parent",
            "scenes",
            "runtime_asset",
            "extra_artifact",
            "missing_source",
            "recipe",
            "compose",
        ):
            with self.subTest(mode=mode):
                case = list(release_case())
                if mode == "failed_ci":
                    case[1]["conclusion"] = "failure"
                elif mode == "declared_mode":
                    case[3]["qualification_target"] = "declared_delivery"
                elif mode == "foreign_image":
                    case[3]["declared_image"] = "foreign/image:latest"
                elif mode == "managed_parent":
                    case[7]["parent_image"] = IMAGE.replace(DIGEST, "1" * 64)
                elif mode == "scenes":
                    case[7]["scenes_installed"] = True
                elif mode == "runtime_asset":
                    case[6]["grafana/plugins/bioetl-scenes-app/dist/module.js"] = (
                        "1" * 64
                    )
                elif mode == "extra_artifact":
                    case[6]["grafana/plugins/bioetl-scenes-app/dist/extra.js.map"] = (
                        DIGEST
                    )
                elif mode == "missing_source":
                    host = json.loads(case[0][promotion.HOST_PATH])
                    host["artifact_sha256"]["required.js"] = DIGEST
                    case[0][promotion.HOST_PATH] = json.dumps(host).encode()
                elif mode == "recipe":
                    case[0][promotion.RECIPE_PATH] = b"FROM foreign/image:latest\n"
                else:
                    case[0][promotion.COMPOSE_PATHS[0]] = (
                        b"image: foreign/image:latest\n"
                    )
                with self.assertRaises(ValueError):
                    promotion.build_release_files(*case)

    def test_positive_original_capture_and_idempotent_history(self):
        run, jobs, artifacts, raw, original, parity = fixture()
        artifact, actual = module.validate_capture(run, jobs, artifacts, raw)
        self.assertEqual(actual, parity)
        inputs = {"grafana/plugins/source.js": DIGEST}
        result = module.refresh(
            original, run, artifact, parity, inputs, "c" * 40, DIGEST
        )
        self.assertEqual(result["delivery_source"], original["delivery_source"])
        self.assertEqual(
            result["previous_revalidation"], original["previous_revalidation"]
        )
        self.assertEqual(result["artifact_sha256"]["grafana/plugins/source.js"], DIGEST)
        self.assertFalse(
            result["ci_source_revalidations"][0]["browser_acceptance_claimed"]
        )
        self.assertEqual(
            module.refresh(result, run, artifact, parity, inputs, "c" * 40, DIGEST),
            result,
        )
        self.assertNotIn("ci_source_revalidations", original)

    def test_failed_missing_skipped_duplicate_foreign_jobs(self):
        for mode in (
            "failed_run",
            "wrong_workflow",
            "missing",
            "duplicate",
            "skipped",
            "foreign",
            "attempt",
        ):
            with self.subTest(mode=mode):
                run, jobs, artifacts, raw, _, _ = fixture()
                if mode == "failed_run":
                    run["conclusion"] = "failure"
                elif mode == "wrong_workflow":
                    run["path"] = ".github/workflows/untrusted.yml"
                elif mode == "missing":
                    jobs["jobs"].pop()
                elif mode == "duplicate":
                    jobs["jobs"][0]["name"] = jobs["jobs"][1]["name"]
                elif mode == "skipped":
                    jobs["jobs"][0]["conclusion"] = "skipped"
                elif mode == "foreign":
                    jobs["jobs"][0]["head_sha"] = "d" * 40
                else:
                    jobs["jobs"][0]["run_attempt"] = 2
                with self.assertRaises(ValueError):
                    module.validate_capture(run, jobs, artifacts, raw)

    def test_original_archive_identity_and_foreign_artifact(self):
        for mode in (
            "digest",
            "size",
            "expired",
            "foreign",
            "duplicate",
            "missing",
            "old_attempt",
            "missing_time",
        ):
            with self.subTest(mode=mode):
                run, jobs, artifacts, raw, _, _ = fixture()
                artifact = artifacts["artifacts"][0]
                if mode == "digest":
                    artifact["digest"] = "sha256:" + "d" * 64
                elif mode == "size":
                    artifact["size_in_bytes"] += 1
                elif mode == "expired":
                    artifact["expired"] = True
                elif mode == "foreign":
                    artifact["workflow_run"]["id"] = 99
                elif mode == "old_attempt":
                    artifact["created_at"] = "2026-10-31T11:59:59Z"
                elif mode == "missing_time":
                    artifact.pop("created_at")
                elif mode == "duplicate":
                    artifacts["artifacts"].append(copy.deepcopy(artifact))
                    artifacts["total_count"] = 2
                else:
                    artifacts["artifacts"] = []
                    artifacts["total_count"] = 0
                with self.assertRaises(ValueError):
                    module.validate_capture(run, jobs, artifacts, raw)

    def test_changed_receipts_cannot_masquerade_as_parity(self):
        for mode in (
            "failed",
            "config",
            "missing_scope",
            "unsafe_path",
            "missing_file",
            "missing_config",
            "missing_scope_tree",
            "missing_layers",
        ):
            with self.subTest(mode=mode):
                run, jobs, artifacts, _, _, parity = fixture()
                if mode == "failed":
                    parity["status"] = "FAIL"
                if mode == "config":
                    parity["built_image_config_digest"] = "sha256:" + "d" * 64
                if mode == "missing_scope":
                    parity["artifacts"].pop(next(iter(parity["artifacts"])))
                if mode == "missing_config":
                    parity.pop("built_image_config_digest")
                if mode == "missing_scope_tree":
                    parity["artifacts"][next(iter(parity["artifacts"]))].pop(
                        "tree_sha256"
                    )
                if mode == "missing_layers":
                    parity.pop("built_layers")
                archive = io.BytesIO()
                with zipfile.ZipFile(archive, "w") as output:
                    output.writestr(
                        "router-v7-image-build.json",
                        json.dumps(
                            {}
                            if mode == "missing_config"
                            else {"containerimage.config.digest": "sha256:" + DIGEST}
                        ),
                    )
                    if mode != "missing_file":
                        output.writestr(
                            ("../" if mode == "unsafe_path" else "")
                            + "router-v7-image-parity.json",
                            json.dumps(parity),
                        )
                raw = archive.getvalue()
                artifacts["artifacts"][0].update(
                    size_in_bytes=len(raw), digest="sha256:" + module.sha256(raw)
                )
                with self.assertRaises(ValueError):
                    module.validate_capture(run, jobs, artifacts, raw)

    def test_changed_delivery_or_shrinking_inventory_is_rejected(self):
        for mode in ("image", "rootfs", "plugin", "shrink"):
            with self.subTest(mode=mode):
                run, _, artifacts, _, manifest, parity = fixture()
                if mode == "image":
                    parity["declared_image"] += "changed"
                elif mode == "rootfs":
                    parity["rootfs_sha256"] = "d" * 64
                elif mode == "plugin":
                    parity["artifacts"][
                        "/usr/share/grafana/data/plugins-bundled/bioetl-scenes-app"
                    ]["module_sha256"] = "d" * 64
                else:
                    manifest["artifact_sha256"]["missing-source.js"] = DIGEST
                with self.assertRaises(ValueError):
                    module.refresh(
                        manifest,
                        run,
                        artifacts["artifacts"][0],
                        parity,
                        {"source.js": DIGEST},
                        "c" * 40,
                        DIGEST,
                    )

    def test_real_git_source_closure_rejects_drift_and_missing_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args):
                return subprocess.check_output(
                    ["git", *args], cwd=root, stderr=subprocess.DEVNULL
                )

            git("init", "-q")
            source = root / "source.js"
            source.write_bytes(b"exact source\n")
            git("add", "source.js")
            plugin = root / "grafana/plugins/bioetl-scenes-app/captured.js"
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b"captured plugin\n")
            git("add", "grafana")
            for relative in module.BUILD_SUPPORT:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"support fixture\n")
            git("add", ".")
            git(
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "fixture",
            )
            commit = git("rev-parse", "HEAD").decode().strip()
            manifest = {"artifact_sha256": {"source.js": DIGEST}}
            inputs, tree = module.source_inputs(root, commit, manifest)
            self.assertEqual(
                inputs,
                {
                    "source.js": module.sha256(b"exact source\n"),
                    "grafana/plugins/bioetl-scenes-app/captured.js": module.sha256(
                        b"captured plugin\n"
                    ),
                    **{
                        path: module.sha256(b"support fixture\n")
                        for path in module.BUILD_SUPPORT
                    },
                },
            )
            self.assertEqual(tree, git("rev-parse", "HEAD^{tree}").decode().strip())
            git("rm", "-q", "grafana/plugins/bioetl-scenes-app/captured.js")
            with self.assertRaisesRegex(ValueError, "inventory added/deleted"):
                module.source_inputs(root, commit, manifest)
            git("restore", "--staged", "grafana")
            plugin.parent.mkdir(parents=True, exist_ok=True)
            plugin.write_bytes(b"captured plugin\n")
            added = plugin.with_name("new.js")
            added.write_bytes(b"uncaptured addition\n")
            with self.assertRaisesRegex(
                ValueError, "Uncommitted build input additions"
            ):
                module.source_inputs(root, commit, manifest)
            git("add", "grafana")
            with self.assertRaisesRegex(ValueError, "inventory added/deleted"):
                module.source_inputs(root, commit, manifest)
            git("rm", "-q", "--cached", "grafana/plugins/bioetl-scenes-app/new.js")
            added.unlink()
            source.write_bytes(b"changed source\n")
            with self.assertRaisesRegex(ValueError, "differs from actual CI"):
                module.source_inputs(root, commit, manifest)
            source.unlink()
            with self.assertRaisesRegex(ValueError, "Missing/redirected"):
                module.source_inputs(root, commit, manifest)


if __name__ == "__main__":
    unittest.main()

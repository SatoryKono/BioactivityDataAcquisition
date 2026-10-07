"""Behavior regressions for the managed image delivery contract."""

from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from scripts.ops.observability.grafana import router_managed_image as managed


class ManagedImageTests(unittest.TestCase):
    def test_relocated_manifest_directory_exists(self):
        self.assertTrue((managed.HERE / "managed-image.json").is_file())
        self.assertTrue((managed.HERE / "host-image.json").is_file())

    def test_ops_dispatch_rejects_mutable_images_before_docker(self):
        from scripts.ops.__main__ import main

        for command in ("fingerprint-router-rootfs", "verify-router-managed-image"):
            with (
                self.subTest(command=command),
                patch.object(
                    managed.subprocess,
                    "check_output",
                    side_effect=AssertionError("Docker must not execute"),
                ),
            ):
                with self.assertRaises(ValueError):
                    main([command, "untrusted:latest"])

    def setUp(self):
        self.declared = "satorykono/bioetl-grafana-router7-canvas@sha256:" + "a" * 64
        self.parent = {
            "Id": "sha256:" + "b" * 64,
            "Config": {"User": "grafana"},
            "Architecture": "amd64",
            "Os": "linux",
            "RootFS": {"Type": "layers", "Layers": ["sha256:" + "c" * 64]},
        }
        self.built = copy.deepcopy(self.parent)
        self.built["RootFS"]["Layers"].append("sha256:" + "d" * 64)
        self.delivered = copy.deepcopy(self.built)
        self.delivered["RepoDigests"] = [self.declared]
        self.parent_files = {
            "run.sh": ["trusted"],
            "usr/share/grafana/bin/grafana": ["backend"],
            managed.SCENES + "/module.js": ["optional"],
            "usr/share/grafana/public/build/frontend.js": ["frontend"],
            "usr/share/grafana/data/plugins-bundled/"
            "bioetl-selectorshell-panel/module.js": ["selector"],
        }
        self.expected = {
            key: value
            for key, value in self.parent_files.items()
            if not key.startswith(managed.SCENES)
        }

    def verify(self, files=None):
        return managed.verify(
            self.parent,
            self.built,
            self.delivered,
            self.parent_files,
            self.expected,
            self.expected if files is None else files,
            self.declared,
        )

    def test_exact_parent_minus_optional_package_passes(self):
        self.assertEqual(self.verify()["status"], "PASS")

    def test_backend_frontend_selector_and_other_bytes_cannot_change(self):
        for key in self.expected:
            with self.subTest(path=key):
                changed = copy.deepcopy(self.expected)
                changed[key] = ["tampered"]
                with self.assertRaisesRegex(ValueError, "Complete filesystem"):
                    self.verify(changed)

    def test_restoring_scenes_or_injecting_new_file_fails(self):
        for key in (managed.SCENES + "/module.js", "extra-file"):
            with (
                self.subTest(path=key),
                self.assertRaisesRegex(ValueError, "Complete filesystem"),
            ):
                self.verify({**self.expected, key: ["unexpected"]})

    def test_parent_digest_and_runtime_user_cannot_change(self):
        self.delivered["RootFS"]["Layers"][0] = "sha256:" + "e" * 64
        with self.assertRaisesRegex(ValueError, "Pinned parent"):
            self.verify()
        self.delivered = copy.deepcopy(self.built)
        self.delivered["RepoDigests"] = [self.declared]
        self.delivered["Config"]["User"] = "root"
        with self.assertRaisesRegex(ValueError, "runtime configuration"):
            self.verify()

    def test_registry_pin_is_required(self):
        self.delivered["RepoDigests"] = []
        with self.assertRaisesRegex(ValueError, "registry digest"):
            self.verify()

    def test_cli_flags_and_mutable_references_are_rejected_before_docker(self):
        for value in (
            "--privileged",
            "--help",
            "grafana:latest",
            self.declared + " --privileged",
        ):
            with (
                self.subTest(reference=value),
                patch.object(managed.subprocess, "check_output") as command,
            ):
                with self.assertRaisesRegex(ValueError, "immutable image reference"):
                    managed.inspect(value)
                with self.assertRaisesRegex(ValueError, "immutable image reference"):
                    managed.records(value)
                command.assert_not_called()

    def test_rebuilt_plugin_maps_missing_and_extra_files_fail(self):
        built = {
            plugin: {"module.js": "a" * 64, "module.js.map": "b" * 64}
            for plugin in ("bioetl-scenes-app", "bioetl-selectorshell-panel")
        }
        parent = {
            "usr/share/grafana/data/plugins-bundled/" + plugin + "/" + name: [
                "0",
                0o444,
                0,
                0,
                "",
                0,
                0,
                digest,
                {},
            ]
            for plugin, files in built.items()
            for name, digest in files.items()
        }
        self.assertEqual(
            managed.verify_plugin_bundles(parent, built), dict.fromkeys(built, 2)
        )
        for plugin in built:
            for defect in ("changed_map", "missing_map", "extra_file"):
                with self.subTest(plugin=plugin, defect=defect):
                    changed = copy.deepcopy(built)
                    if defect == "changed_map":
                        changed[plugin]["module.js.map"] = "c" * 64
                    elif defect == "missing_map":
                        del changed[plugin]["module.js.map"]
                    else:
                        changed[plugin]["unrelated.js"] = "d" * 64
                    with self.assertRaisesRegex(
                        ValueError, "Complete rebuilt plugin mismatch"
                    ):
                        managed.verify_plugin_bundles(parent, changed)


if __name__ == "__main__":
    unittest.main()

# Standalone unittest.main exits before this pytest-only collection metadata.
import pytest

pytestmark = pytest.mark.unit

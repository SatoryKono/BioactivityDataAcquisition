"""Behavior fixtures for the trusted, extraction-free rootfs comparison."""

import io
import tarfile
import unittest
from unittest.mock import patch

from scripts.ops.observability.grafana import router_rootfs as rootfs


def archive(
    *,
    mtime=1,
    name="usr/share/grafana/bin/grafana",
    data=b"backend",
    mode=0o755,
    uid=0,
    gid=0,
    link="target",
    duplicate=False,
):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.PAX_FORMAT) as output:
        file = tarfile.TarInfo(name)
        file.size, file.mode, file.uid, file.gid, file.mtime = (
            len(data),
            mode,
            uid,
            gid,
            mtime,
        )
        file.pax_headers = {
            "mtime": str(mtime),
            "atime": str(mtime),
            "ctime": str(mtime),
        }
        output.addfile(file, io.BytesIO(data))
        if duplicate:
            output.addfile(file, io.BytesIO(data))
        symlink = tarfile.TarInfo("lib/library-link")
        symlink.type, symlink.linkname, symlink.mtime = tarfile.SYMTYPE, link, mtime
        output.addfile(symlink)
    stream.seek(0)
    return stream


class RootfsFingerprintTests(unittest.TestCase):
    def test_cli_rejects_option_injection_without_spawning_docker(self):
        for args in (
            ["--privileged"],
            ["--help"],
            ["bioetl-router-host:acceptance", "--privileged"],
            ["bioetl-router-host:acceptance --privileged"],
            ["sha256:" + "a" * 64 + "\n--privileged"],
        ):
            with (
                self.subTest(args=args),
                patch.object(rootfs.subprocess, "check_output") as command,
            ):
                with self.assertRaisesRegex(ValueError, "Unsupported image reference"):
                    rootfs.main(args)
                command.assert_not_called()

    def test_valid_image_is_one_positional_argument_after_option_terminator(self):
        for image in (
            "bioetl-router-host:acceptance",
            "sha256:" + "a" * 64,
            "satorykono/bioetl-grafana-router7-canvas@sha256:" + "b" * 64,
        ):
            with (
                self.subTest(image=image),
                patch.object(
                    rootfs.subprocess,
                    "check_output",
                    return_value="invalid-container-id",
                ) as command,
            ):
                with self.assertRaisesRegex(ValueError, "Invalid container ID"):
                    rootfs.main([image])
                self.assertEqual(
                    command.call_args.args[0][1:],
                    ["create", "--entrypoint", "/bin/true", "--", image],
                )
                self.assertEqual(command.call_args.kwargs, {"text": True})

    def test_only_timestamp_differences_are_accepted(self):
        self.assertEqual(
            rootfs.fingerprint(archive(mtime=1)),
            rootfs.fingerprint(archive(mtime=2000000000)),
        )

    def test_changed_backend_entrypoint_and_library_bytes_are_detected(self):
        for name in ["usr/share/grafana/bin/grafana", "run.sh", "lib/libc.so"]:
            with self.subTest(name=name):
                self.assertNotEqual(
                    rootfs.fingerprint(archive(name=name)),
                    rootfs.fingerprint(archive(name=name, data=b"tampered")),
                )

    def test_paths_modes_owners_and_link_targets_are_preserved(self):
        baseline = rootfs.fingerprint(archive())
        for changes in [
            {"name": "other"},
            {"mode": 0o777},
            {"uid": 472},
            {"gid": 472},
            {"link": "evil"},
        ]:
            with self.subTest(changes=changes):
                self.assertNotEqual(baseline, rootfs.fingerprint(archive(**changes)))

    def test_duplicate_paths_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            rootfs.fingerprint(archive(duplicate=True))

    def test_empty_exports_fail_closed(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w"):
            pass
        stream.seek(0)
        with self.assertRaisesRegex(ValueError, "Empty"):
            rootfs.fingerprint(stream)


if __name__ == "__main__":
    unittest.main()

# Standalone unittest.main exits before this pytest-only collection metadata.
import pytest

pytestmark = pytest.mark.unit

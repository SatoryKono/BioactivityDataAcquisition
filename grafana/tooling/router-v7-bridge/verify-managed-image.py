"""Verify the managed image is precisely the pinned host with Scenes removed.

Read Docker exports using host Python; never execute a tool supplied by an image.
Creation timestamps are excluded, but all bytes, paths, modes and owners remain.
"""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCENES = "usr/share/grafana/data/plugins-bundled/bioetl-scenes-app"
IMAGE = re.compile(r"satorykono/bioetl-grafana-router7-canvas@sha256:[0-9a-f]{64}")
CONFIG_ID = re.compile(r"sha256:[0-9a-f]{64}")
spec = importlib.util.spec_from_file_location("rootfs_fingerprint", HERE / "fingerprint-rootfs.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def docker_path():
    if sys.platform == "win32":
        return "C:/Program Files/Docker/Docker/resources/bin/docker.exe"
    for candidate in (Path("/usr/bin/docker"), Path("/usr/local/bin/docker")):
        if candidate.is_file():
            resolved = candidate.resolve()
            for path in (resolved, *resolved.parents):
                info = path.stat()
                if info.st_uid != 0 or info.st_mode & 0o022:
                    raise ValueError("Docker executable path must be root-owned and protected")
            return str(resolved)
    raise ValueError("Docker is absent from the fixed trusted locations")


def immutable_reference(image):
    if not (IMAGE.fullmatch(image) or CONFIG_ID.fullmatch(image)):
        raise ValueError("Unsupported immutable image reference")
    return image


def inspect(image):
    reference = immutable_reference(image)
    return json.loads(subprocess.check_output(
        [docker_path(), "image", "inspect", "--", reference], text=True
    ))[0]


def records(image):
    reference = immutable_reference(image)
    container = subprocess.check_output(
        [docker_path(), "create", "--entrypoint", "/bin/true", "--", reference],
        text=True,
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{64}", container):
        raise ValueError("Invalid container ID")
    try:
        with subprocess.Popen([docker_path(), "export", container], stdout=subprocess.PIPE) as process:
            try:
                result = module.filesystem_records(process.stdout)
            except BaseException:
                process.kill()
                process.wait()
                raise
            if process.wait() != 0:
                raise RuntimeError("Docker export failed")
        return result
    finally:
        subprocess.run([docker_path(), "rm", "-v", container], check=True, stdout=subprocess.DEVNULL)


def verify(parent, built, delivered, parent_files, built_files, delivered_files, declared):
    if declared not in delivered.get("RepoDigests", []):
        raise ValueError("Declared registry digest was not inspected")
    for image in (built, delivered):
        for key in ("Config", "Architecture", "Os"):
            if image[key] != parent[key]:
                raise ValueError("Parent runtime configuration mismatch: " + key)
        layers = image.get("RootFS", {})
        base = parent.get("RootFS", {})
        if (layers.get("Type") != "layers" or base.get("Type") != "layers"
                or not base.get("Layers") or not layers.get("Layers")
                or any(not CONFIG_ID.fullmatch(item) for item in (*base["Layers"], *layers["Layers"]))
                or layers["Layers"][:len(base["Layers"])] != base["Layers"]
                or len(layers["Layers"]) <= len(base["Layers"])):
            raise ValueError("Pinned parent layer prefix mismatch")
    expected = {key: value for key, value in parent_files.items()
                if key != SCENES and not key.startswith(SCENES + "/")}
    if len(expected) == len(parent_files):
        raise ValueError("Pinned parent must contain the optional Scenes package")
    if built_files != expected or delivered_files != expected:
        raise ValueError("Complete filesystem must equal parent minus Scenes")
    encoded = json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()
    return {"status": "PASS", "declared_image": declared,
            "built_image_config_digest": built["Id"], "declared_image_config_digest": delivered["Id"],
            "rootfs_sha256": hashlib.sha256(encoded).hexdigest(), "paths_verified": len(expected),
            "scenes_installed": False, "trust_tier": "image_artifact_parity"}


def main():
    if len(sys.argv) != 2 or not CONFIG_ID.fullmatch(sys.argv[1]):
        raise ValueError("Usage: verify-managed-image.py sha256:BUILT_CONFIG_DIGEST")
    manifest = json.loads((HERE / "managed-image.json").read_text())
    parent_manifest = json.loads((HERE / "host-image.json").read_text())
    if not IMAGE.fullmatch(manifest["image"]) or manifest["parent_image"] != parent_manifest["image"]:
        raise ValueError("Managed manifest must bind the pinned host manifest")
    recipe = (HERE / "Dockerfile.managed").read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(recipe).hexdigest() != manifest["dockerfile_sha256"]:
        raise ValueError("Managed Dockerfile source mismatch")
    parent = inspect(manifest["parent_image"])
    built = inspect(sys.argv[1])
    delivered = inspect(manifest["image"])
    result = verify(parent, built, delivered, records(manifest["parent_image"]),
                    records(sys.argv[1]), records(manifest["image"]), manifest["image"])
    target = ROOT / "reports/qa/router-v7-managed-image-parity.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.parent.resolve() != target.parent or (target.exists() and (target.is_symlink() or target.stat().st_nlink != 1)):
        raise ValueError("Receipt path must not redirect writes")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()

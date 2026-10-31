"""Verify the managed image is precisely the pinned host with Scenes removed.

Read Docker exports using host Python; never execute a tool supplied by an image.
Creation timestamps are excluded, but all bytes, paths, modes and owners remain.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from scripts.ops.observability.grafana import router_rootfs as module
from scripts.ops.observability.refresh_router_host_provenance import (
    JsonObject,
    json_list,
    json_object,
    text,
)

ROOT = Path(__file__).resolve().parents[4]
HERE = ROOT / "grafana/tooling/router-v7-bridge"
SCENES = "usr/share/grafana/data/plugins-bundled/bioetl-scenes-app"
IMAGE = re.compile(r"satorykono/bioetl-grafana-router7-canvas@sha256:[0-9a-f]{64}")
CONFIG_ID = re.compile(r"sha256:[0-9a-f]{64}")


def docker_path() -> str:
    if sys.platform == "win32":
        return "C:/Program Files/Docker/Docker/resources/bin/docker.exe"
    else:
        for candidate in (Path("/usr/bin/docker"), Path("/usr/local/bin/docker")):
            if candidate.is_file():
                resolved = candidate.resolve()
                for path in (resolved, *resolved.parents):
                    info = path.stat()
                    if info.st_uid != 0 or info.st_mode & 0o022:
                        raise ValueError(
                            "Docker executable path must be root-owned and protected"
                        )
                return str(resolved)
        raise ValueError("Docker is absent from the fixed trusted locations")


def immutable_reference(image: str) -> str:
    if not (IMAGE.fullmatch(image) or CONFIG_ID.fullmatch(image)):
        raise ValueError("Unsupported immutable image reference")
    return image


def inspect(image: str) -> JsonObject:
    reference = immutable_reference(image)
    captured = json_list(
        json.loads(
            subprocess.check_output(
                [docker_path(), "image", "inspect", "--", reference], text=True
            )
        )
    )
    return json_object(captured[0], "Invalid Docker image inspection")


def records(image: str) -> JsonObject:
    reference = immutable_reference(image)
    container = subprocess.check_output(
        [docker_path(), "create", "--entrypoint", "/bin/true", "--", reference],
        text=True,
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{64}", container):
        raise ValueError("Invalid container ID")
    try:
        with subprocess.Popen(
            [docker_path(), "export", container], stdout=subprocess.PIPE
        ) as process:
            try:
                if process.stdout is None:
                    raise ValueError("Missing Docker export stdout")
                result = module.filesystem_records(process.stdout)
            except BaseException:
                process.kill()
                process.wait()
                raise
            if process.wait() != 0:
                raise RuntimeError("Docker export failed")
        return result
    finally:
        subprocess.run(
            [docker_path(), "rm", "-v", container],
            check=True,
            stdout=subprocess.DEVNULL,
        )


def verify_plugin_bundles(
    parent_files: JsonObject, built_files: dict[str, dict[str, str]]
) -> dict[str, int]:
    """Bind every rebuilt plugin file, including debug maps, to the parent image."""
    counts = {}
    for plugin in ("bioetl-scenes-app", "bioetl-selectorshell-panel"):
        prefix = "usr/share/grafana/data/plugins-bundled/" + plugin + "/"
        expected = {
            path.removeprefix(prefix): json_list(row)[7]
            for path, row in parent_files.items()
            if path.startswith(prefix) and json_list(row)[0] in ("0", "\x00")
        }
        if not expected or built_files.get(plugin) != expected:
            raise ValueError("Complete rebuilt plugin mismatch: " + plugin)
        counts[plugin] = len(expected)
    return counts


def rebuilt_plugin_files() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for plugin in ("bioetl-scenes-app", "bioetl-selectorshell-panel"):
        dist = ROOT / "grafana/plugins" / plugin / "dist"
        if not dist.is_dir() or dist.resolve() != dist:
            raise ValueError("Missing or redirected plugin build: " + plugin)
        files = {}
        for path in dist.rglob("*"):
            if path.is_symlink():
                raise ValueError("Plugin build contains a symlink")
            if path.is_file():
                files[path.relative_to(dist).as_posix()] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
        result[plugin] = files
    return result


def verify(
    parent: JsonObject,
    built: JsonObject,
    delivered: JsonObject,
    parent_files: JsonObject,
    built_files: JsonObject,
    delivered_files: JsonObject,
    declared: str,
) -> JsonObject:
    if declared not in json_list(delivered.get("RepoDigests", [])):
        raise ValueError("Declared registry digest was not inspected")
    for image in (built, delivered):
        for key in ("Config", "Architecture", "Os"):
            if image[key] != parent[key]:
                raise ValueError("Parent runtime configuration mismatch: " + key)
        layers = json_object(image.get("RootFS", {}))
        base = json_object(parent.get("RootFS", {}))
        base_layers = base.get("Layers")
        image_layers = layers.get("Layers")
        if (
            layers.get("Type") != "layers"
            or base.get("Type") != "layers"
            or not isinstance(base_layers, list)
            or not isinstance(image_layers, list)
            or not base_layers
            or not image_layers
            or any(
                not isinstance(item, str) or not CONFIG_ID.fullmatch(item)
                for item in (*base_layers, *image_layers)
            )
            or image_layers[: len(base_layers)] != base_layers
            or len(image_layers) <= len(base_layers)
        ):
            raise ValueError("Pinned parent layer prefix mismatch")
    expected = {
        key: value
        for key, value in parent_files.items()
        if key != SCENES and not key.startswith(SCENES + "/")
    }
    if len(expected) == len(parent_files):
        raise ValueError("Pinned parent must contain the optional Scenes package")
    if built_files != expected or delivered_files != expected:
        raise ValueError("Complete filesystem must equal parent minus Scenes")
    encoded = json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()
    return {
        "status": "PASS",
        "declared_image": declared,
        "built_image_config_digest": built["Id"],
        "declared_image_config_digest": delivered["Id"],
        "rootfs_sha256": hashlib.sha256(encoded).hexdigest(),
        "paths_verified": len(expected),
        "scenes_installed": False,
        "trust_tier": "image_artifact_parity",
    }


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or not CONFIG_ID.fullmatch(args[0]):
        raise ValueError(
            "Usage: python -m scripts.ops verify-router-managed-image sha256:BUILT_CONFIG_DIGEST"
        )
    manifest = json_object(json.loads((HERE / "managed-image.json").read_text()))
    parent_manifest = json_object(json.loads((HERE / "host-image.json").read_text()))
    image = text(manifest["image"], "Invalid managed image reference")
    parent_image = text(manifest["parent_image"], "Invalid parent image reference")
    if not IMAGE.fullmatch(image) or parent_image != parent_manifest["image"]:
        raise ValueError("Managed manifest must bind the pinned host manifest")
    recipe = (HERE / "Dockerfile.managed").read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(recipe).hexdigest() != manifest["dockerfile_sha256"]:
        raise ValueError("Managed Dockerfile source mismatch")
    parent = inspect(parent_image)
    built = inspect(args[0])
    delivered = inspect(image)
    parent_files = records(parent_image)
    plugin_counts = verify_plugin_bundles(parent_files, rebuilt_plugin_files())
    result = verify(
        parent,
        built,
        delivered,
        parent_files,
        records(args[0]),
        records(image),
        image,
    )
    result["rebuilt_plugin_files_verified"] = json_object(plugin_counts)
    target = ROOT / "reports/qa/router-v7-managed-image-parity.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.parent.resolve() != target.parent or (
        target.exists() and (target.is_symlink() or target.stat().st_nlink != 1)
    ):
        raise ValueError("Receipt path must not redirect writes")
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(descriptor, "w") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    sys.stdout.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()

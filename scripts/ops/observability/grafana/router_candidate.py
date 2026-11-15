"""Candidate stages of the existing managed-image verification facade.

The CLI reads local build outputs, inspects/exports existing Docker images and
writes fixed CI receipts (or a candidate managed recipe). It never pushes,
deploys, executes image tools, or claims browser/lifecycle acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from scripts.ops.observability.grafana import router_managed_image as native
from scripts.ops.observability.grafana.trusted_docker import docker_path
from scripts.ops.observability.refresh_router_host_provenance import (
    JsonObject,
    SCOPES,
    json_list,
    json_object,
    require,
    text,
)

ROOT = Path(__file__).resolve().parents[4]
OWNER = ROOT / "grafana/tooling/router-v7-bridge"
PLUGINS = ("bioetl-scenes-app", "bioetl-selectorshell-panel")
BASE = "grafana/grafana@sha256:d84563330dc9d2fd2bc096d0fb96021b5319c75bf6ed555566709998e823dec4"


def inputs(target: str, host: str, managed: str) -> None:
    """Reject ambiguous mode, arbitrary registries and flags before Docker I/O."""
    require(
        target in {"declared_delivery", "candidate"}, "Invalid qualification target"
    )
    if target == "declared_delivery":
        require(not host and not managed, "Candidate images require candidate mode")
        return
    require(
        bool(native.IMAGE.fullmatch(host) and native.IMAGE.fullmatch(managed)),
        "Two owned immutable candidate digests required",
    )
    require(host != managed, "Host and managed candidates must differ")


def digest(value: JsonObject) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def verify_host(
    built: JsonObject,
    delivered: JsonObject,
    base: JsonObject,
    built_files: JsonObject,
    delivered_files: JsonObject,
    plugins: dict[str, dict[str, str]],
    declared: str,
) -> JsonObject:
    """Compare full trusted-host exports and every original plugin artifact."""
    require(bool(native.IMAGE.fullmatch(declared)), "Invalid candidate registry digest")
    require(
        declared in json_list(delivered.get("RepoDigests", [])),
        "Uninspected candidate digest",
    )
    for key in ("Architecture", "Os", "Config"):
        require(
            built.get(key) == delivered.get(key),
            "Candidate configuration mismatch: " + key,
        )
    require(
        built.get("Architecture") == "amd64" and built.get("Os") == "linux",
        "Unsupported candidate platform",
    )
    parent = json_object(base.get("RootFS", {}))
    base_layers = json_list(parent.get("Layers", []))
    require(
        parent.get("Type") == "layers" and bool(base_layers),
        "Missing trusted base layers",
    )
    for image in (built, delivered):
        require(
            bool(native.CONFIG_ID.fullmatch(text(image.get("Id"), "Missing image ID"))),
            "Invalid image ID",
        )
        layers = json_object(image.get("RootFS", {}))
        values = json_list(layers.get("Layers", []))
        require(
            layers.get("Type") == "layers"
            and len(values) > len(base_layers)
            and values[: len(base_layers)] == base_layers
            and all(
                isinstance(x, str) and native.CONFIG_ID.fullmatch(x) for x in values
            ),
            "Trusted base layer prefix mismatch",
        )
    require(
        bool(built_files) and built_files == delivered_files,
        "Complete candidate filesystem mismatch",
    )
    counts = native.verify_plugin_bundles(delivered_files, plugins)
    artifacts: JsonObject = {}
    for scope in sorted(SCOPES):
        prefix = scope.lstrip("/") + "/"
        records = {p: v for p, v in built_files.items() if p.startswith(prefix)}
        require(bool(records), "Missing candidate artifact scope: " + scope)
        artifact: JsonObject = {"tree_sha256": digest(records)}
        if "/plugins-bundled/" in scope:
            plugin = scope.rsplit("/", 1)[-1]
            require(
                "module.js" in plugins[plugin] and "plugin.json" in plugins[plugin],
                "Incomplete candidate plugin",
            )
            artifact["module_sha256"] = plugins[plugin]["module.js"]
        artifacts[scope] = artifact
    return {
        "status": "PASS",
        "qualification_target": "candidate",
        "declared_image": declared,
        "built_image_config_digest": built["Id"],
        "declared_image_config_digest": delivered["Id"],
        "rootfs_sha256": digest(built_files),
        "built_layers": json_object(built["RootFS"])["Layers"],
        "declared_layers": json_object(delivered["RootFS"])["Layers"],
        "artifacts": artifacts,
        "rebuilt_plugin_files_verified": json_object(counts),
    }


def candidate_recipe(recipe: bytes, manifest: JsonObject, host: str) -> bytes:
    """Rebind only FROM in a generated copy; preserve the tracked recipe."""
    require(bool(native.IMAGE.fullmatch(host)), "Invalid candidate parent")
    require(
        hashlib.sha256(recipe).hexdigest() == manifest.get("dockerfile_sha256"),
        "Managed recipe source mismatch",
    )
    parent = text(manifest.get("parent_image"), "Missing declared parent")
    expected = ("FROM " + parent).encode()
    require(
        bool(native.IMAGE.fullmatch(parent))
        and recipe.splitlines().count(expected) == 1,
        "Invalid managed recipe parent",
    )
    return recipe.replace(expected + b"\n", ("FROM " + host + "\n").encode(), 1)


def build_files(directory: Path, release_date: str) -> dict[str, str]:
    require(
        directory.is_dir() and directory.resolve() == directory,
        "Missing/redirected original plugin output",
    )
    files = {}
    for path in directory.rglob("*"):
        require(
            not path.is_symlink() and (path.is_file() or path.is_dir()),
            "Unsafe plugin output entry",
        )
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    require({"module.js", "plugin.json"} <= files.keys(), "Incomplete candidate plugin")
    metadata = json_object(json.loads((directory / "plugin.json").read_bytes()))
    require(
        json_object(metadata.get("info", {})).get("updated") == release_date,
        "Plugin release date mismatch",
    )
    return files


def plugin_files() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    manifest = json_object(json.loads((OWNER / "host-image.json").read_bytes()))
    release_date = text(
        manifest.get("plugin_release_date"), "Missing plugin release date"
    )
    for plugin in PLUGINS:
        directory = ROOT / "reports/qa/router-v7-image-context" / plugin
        result[plugin] = build_files(directory, release_date)
    return result


def write_output(relative: str, raw: bytes) -> None:
    target = ROOT / "reports/qa" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    require(target.parent.resolve() == target.parent, "Redirected receipt directory")
    require(
        not target.is_symlink()
        and (not target.exists() or (target.is_file() and target.stat().st_nlink == 1)),
        "Unsafe receipt file",
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def inspect_build(tag: str, metadata: str) -> JsonObject:
    config = subprocess.check_output(
        [docker_path(), "image", "inspect", "--format", "{{.Id}}", "--", tag],
        text=True,
    ).strip()
    image = native.inspect(config)
    build = json_object(json.loads((ROOT / "reports/qa" / metadata).read_bytes()))
    require(
        build.get("containerimage.config.digest") == image["Id"],
        "Build metadata image mismatch",
    )
    return image


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        required=True,
        choices=("inputs", "plugin", "host", "recipe", "managed"),
    )
    args = parser.parse_args(argv)
    target = os.environ.get("BIOETL_QUALIFICATION_TARGET", "declared_delivery")
    host = os.environ.get("BIOETL_CANDIDATE_HOST_IMAGE", "")
    managed = os.environ.get("BIOETL_CANDIDATE_MANAGED_IMAGE", "")
    inputs(target, host, managed)
    if args.stage == "inputs":
        return
    require(
        target == "candidate", "Image qualification requires explicit candidate mode"
    )
    if args.stage == "plugin":
        plugin = os.environ.get("BIOETL_PLUGIN", "")
        require(plugin in PLUGINS, "Invalid candidate plugin")
        manifest = json_object(json.loads((OWNER / "host-image.json").read_bytes()))
        build_files(
            ROOT / "grafana/plugins" / plugin / "dist",
            text(manifest.get("plugin_release_date"), "Missing plugin release date"),
        )
        return
    if args.stage == "recipe":
        manifest = json_object(json.loads((OWNER / "managed-image.json").read_bytes()))
        recipe = (OWNER / "Dockerfile.managed").read_bytes().replace(b"\r\n", b"\n")
        write_output(
            "router-v7-managed-context/Dockerfile",
            candidate_recipe(recipe, manifest, host),
        )
        return
    parent = native.inspect(host)
    parent_files = native.records(host)
    plugins = plugin_files()
    if args.stage == "host":
        manifest = json_object(json.loads((OWNER / "host-image.json").read_bytes()))
        require(
            manifest.get("base_image") == BASE
            and (OWNER / "Dockerfile.host").read_text().splitlines()[0]
            == "FROM " + BASE,
            "Unqualified candidate base",
        )
        base = json_list(
            json.loads(
                subprocess.check_output(
                    [docker_path(), "image", "inspect", "--", BASE], text=True
                )
            )
        )
        require(
            BASE in json_list(json_object(base[0]).get("RepoDigests", [])),
            "Uninspected trusted base",
        )
        built = inspect_build(
            "bioetl-router-host:acceptance", "router-v7-image-build.json"
        )
        result = verify_host(
            built,
            parent,
            json_object(base[0]),
            native.records(text(built["Id"], "Invalid build ID")),
            parent_files,
            plugins,
            host,
        )
        name = "router-v7-image-parity.json"
    else:
        built = inspect_build(
            "bioetl-router-managed:acceptance", "router-v7-managed-image-build.json"
        )
        result = native.verify(
            parent,
            built,
            native.inspect(managed),
            parent_files,
            native.records(text(built["Id"], "Invalid build ID")),
            native.records(managed),
            managed,
        )
        result["rebuilt_plugin_files_verified"] = json_object(
            native.verify_plugin_bundles(parent_files, plugins)
        )
        result.update(qualification_target="candidate", parent_image=host)
        name = "router-v7-managed-image-parity.json"
    write_output(name, (json.dumps(result, indent=2) + "\n").encode())

"""Record real rebuilt/published Router images, never rebind an old image to new inputs.

Requires the complete source-built Docker context and both immutable registry
images locally available. Check mode performs the same physical checks without
changing tracked files. Existing CI reproduction and runtime acceptance remain
independent gates.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile
import tempfile

from scripts.ops.observability.grafana import router_managed_image as native

PLUGINS = ("bioetl-scenes-app", "bioetl-selectorshell-panel")
FRONTEND = "usr/share/grafana/public/build"
PLUGIN_ROOT = "usr/share/grafana/data/plugins-bundled"
OWNER = "grafana/tooling/router-v7-bridge"
PLUGIN_SOURCE = "grafana/plugins"
TOOLING_SOURCE = ".github/tooling"
HOST_MANIFEST = "host-image.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_input(path: Path, *, within: Path) -> Path:
    """Bound regular, unlinked build inputs to the verified workspace."""
    boundary = within.resolve(strict=True)
    candidate = Path(os.path.abspath(path))
    resolved = path.resolve(strict=True)
    relative = resolved.relative_to(boundary)
    if resolved != candidate or not boundary.is_dir():
        raise ValueError("Input path is redirected")
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("Input must be a regular unlinked file")
    return boundary.joinpath(*relative.parts)


def file_sha(path: Path, *, within: Path) -> str:
    with checked_input(path, within=within).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def commit_id(value: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("Full source commit required")
    return bytes.fromhex(value).hex()


def git(root: Path, *args: str) -> bytes:
    """Expose only the three read-only operations required by this producer."""
    if len(args) == 2 and args[0] == "show":
        ref, separator, name = args[1].partition(":")
        path = PurePosixPath(name)
        if (
            not separator
            or not name
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in name
            or path.as_posix() != name
        ):
            raise ValueError("Expected a repository-relative blob path")
        command = [
            "git",
            "show",
            "--end-of-options",
            commit_id(ref) + ":" + path.as_posix(),
        ]
    elif (
        len(args) == 4
        and args[:2] == ("merge-base", "--is-ancestor")
        and args[3] == "HEAD"
    ):
        command = ["git", "merge-base", "--is-ancestor", commit_id(args[2]), "HEAD"]
    elif (
        len(args) == 8
        and args[:3] == ("ls-tree", "-rz", "--name-only")
        and args[4:] == ("--", PLUGIN_SOURCE, OWNER, TOOLING_SOURCE)
    ):
        command = [
            "git",
            "ls-tree",
            "-rz",
            "--name-only",
            commit_id(args[3]),
            "--",
            PLUGIN_SOURCE,
            OWNER,
            TOOLING_SOURCE,
        ]
    else:
        raise ValueError("Unsupported Git operation")
    return subprocess.check_output(command, cwd=root)


def context_entry(archive: tarfile.TarFile, entry: tarfile.TarInfo) -> tuple[str, list]:
    """Validate one artifact member and derive its audited COPY record."""
    name = entry.name.rstrip("/")
    mapping = {"host-build": FRONTEND, **{p: f"{PLUGIN_ROOT}/{p}" for p in PLUGINS}}
    prefix = name.split("/", 1)[0]
    if (
        prefix not in mapping
        or not (entry.isdir() or entry.isfile())
        or entry.mode & ~0o777
    ):
        raise ValueError("Unexpected build-context entry")
    digest = None
    if entry.isfile():
        with archive.extractfile(entry) as member:
            digest = hashlib.file_digest(member, "sha256").hexdigest()
    return mapping[prefix] + name[len(prefix) :], [
        "5" if entry.isdir() else "0",
        entry.mode & ~0o222,
        0,
        0,
        "",
        0,
        0,
        digest,
        {},
    ]


def context_recipe(
    archive: tarfile.TarFile, entry: tarfile.TarInfo, recipe: bytes
) -> None:
    if not entry.isfile():
        raise ValueError("Build recipe must be a regular file")
    with archive.extractfile(entry) as member:
        if member.read() != recipe:
            raise ValueError("Build-context recipe differs from pinned source")


def validate_context_scopes(records: dict, *, saw_recipe: bool) -> None:
    if not saw_recipe:
        raise ValueError("Missing build recipe")
    for scope in (FRONTEND, *(f"{PLUGIN_ROOT}/{p}" for p in PLUGINS)):
        if not any(n.startswith(scope + "/") and r[7] for n, r in records.items()):
            raise ValueError("Missing complete artifact scope: " + scope)


def context_records(path: Path, recipe: bytes, *, within: Path) -> dict:
    """Read, never extract, the actual build context; apply audited COPY metadata."""
    records = {}
    saw_recipe = False
    source = checked_input(path, within=within)
    with (
        source.open("rb") as stream,
        tarfile.open(fileobj=stream, mode="r|*") as archive,
    ):
        for entry in archive:
            name = entry.name.rstrip("/")
            if (
                ".." in PurePosixPath(name).parts
                or "\\" in name
                or name.startswith("/")
            ):
                raise ValueError("Unsafe build-context path")
            if name == "Dockerfile.host":
                if saw_recipe:
                    raise ValueError("Build-context recipe differs from pinned source")
                context_recipe(archive, entry, recipe)
                saw_recipe = True
                continue
            target, record = context_entry(archive, entry)
            if target in records:
                raise ValueError("Duplicate build-context path")
            records[target] = record
    validate_context_scopes(records, saw_recipe=saw_recipe)
    return records


def expected_host(base_files: dict, artifacts: dict) -> dict:
    """The audited recipe changes only its three trees and parent directory metadata."""
    scopes = (FRONTEND, *(f"{PLUGIN_ROOT}/{p}" for p in PLUGINS))
    result = {
        p: deepcopy(r)
        for p, r in base_files.items()
        if not any(p == s or p.startswith(s + "/") for s in scopes)
    }
    for directory in (
        "usr/share/grafana/public",
        "usr/share/grafana/data",
        PLUGIN_ROOT,
    ):
        row = result.setdefault(directory, ["5", 0o755, 0, 0, "", 0, 0, None, {}])
        row[1], row[2], row[3] = row[1] & ~0o022, 0, 0
    result.update(artifacts)
    return result


def filesystem_view(records: dict) -> dict:
    """PAX path is transport encoding; its value must still equal the actual key.

    Full built/registry comparisons below retain the original native records,
    including every PAX field. Only context-versus-image comparisons remove a
    redundant, validated path encoding; all security xattrs remain checked.
    """
    result = deepcopy(records)
    for path, row in result.items():
        encoded = row[8].pop("path", path)
        if encoded != path:
            raise ValueError("PAX path disagrees with filesystem identity")
    return result


def verify_host(
    base: dict,
    built: dict,
    delivered: dict,
    base_files: dict,
    built_files: dict,
    delivered_files: dict,
    artifacts: dict,
    reference: str,
) -> dict:
    if reference not in delivered.get("RepoDigests", []):
        raise ValueError("Registry manifest digest was not inspected")
    expected_config = {**base["Config"], "User": "grafana"}
    for image in (base, built, delivered):
        layers = image["RootFS"]
        if (
            layers["Type"] != "layers"
            or not layers["Layers"]
            or not all(native.CONFIG_ID.fullmatch(layer) for layer in layers["Layers"])
        ):
            raise ValueError("Invalid immutable layer identities")
    for image in (built, delivered):
        if (
            any(image[k] != base[k] for k in ("Architecture", "Os"))
            or image["Config"] != expected_config
        ):
            raise ValueError("Host runtime configuration differs from audited recipe")
        if (
            image["RootFS"]["Layers"][: len(base["RootFS"]["Layers"])]
            != base["RootFS"]["Layers"]
        ):
            raise ValueError("Trusted official base layer prefix mismatch")
    if built_files != delivered_files:
        raise ValueError("Complete rebuilt/registry filesystem mismatch")
    expected = expected_host(base_files, artifacts)
    if filesystem_view(built_files) != filesystem_view(expected):
        raise ValueError(
            "Image differs from trusted base plus complete source-built artifacts"
        )
    return {
        "built_config_digest": built["Id"],
        "registry_config_digest": delivered["Id"],
        "image": reference,
        "rootfs_sha256": sha(
            json.dumps(built_files, sort_keys=True, separators=(",", ":")).encode()
        ),
    }


def source_inputs(root: Path, source_root: Path, ref: str) -> dict:
    if re.fullmatch(r"[0-9a-f]{40}", ref) is None:
        raise ValueError("Full source commit required")
    git(root, "merge-base", "--is-ancestor", ref, "HEAD")
    paths = (
        git(
            root,
            "ls-tree",
            "-rz",
            "--name-only",
            ref,
            "--",
            PLUGIN_SOURCE,
            OWNER,
            TOOLING_SOURCE,
        )
        .decode()
        .split("\0")
    )
    inputs = {}
    excluded = {
        f"{OWNER}/{p}"
        for p in (
            HOST_MANIFEST,
            "managed-image.json",
            "Dockerfile.managed",
            "compose.acceptance.yml",
            "compose.managed-acceptance.yml",
            "HOST-ACCEPTANCE.md",
        )
    }
    for path in filter(None, paths):
        if path in excluded or "/dist/" in path:
            continue
        expected = git(root, "show", f"{ref}:{path}")
        actual = checked_input(source_root / path, within=source_root).read_bytes()
        working = checked_input(root / path, within=root).read_bytes()
        if actual != expected or working.replace(b"\r\n", b"\n") != expected.replace(
            b"\r\n", b"\n"
        ):
            raise ValueError("Build source differs from pinned/current input: " + path)
        inputs[path] = sha(expected)
    return inputs


def rebuilt_plugins(source_root: Path) -> dict:
    result = {}
    for plugin in PLUGINS:
        directory = source_root / PLUGIN_SOURCE / plugin / "dist"
        if not directory.is_dir() or directory.resolve() != directory:
            raise ValueError("Missing or redirected compiled plugin")
        result[plugin] = {}
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise ValueError("Unexpected plugin symlink")
            if path.is_file():
                result[plugin][path.relative_to(directory).as_posix()] = file_sha(
                    path, within=source_root
                )
    return result


def validate_target(path: Path) -> None:
    if path.resolve() != path or (path.exists() and path.stat().st_nlink != 1):
        raise ValueError("Release output must not redirect writes")


def atomic_write(path: Path, data: bytes) -> None:
    validate_target(path)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            name = stream.name
            stream.write(data)
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def build_workspace(args: argparse.Namespace) -> Path:
    """Normalize a real build root and return its dedicated input boundary."""
    declared_source_root = args.source_root
    args.source_root = Path(os.path.abspath(declared_source_root))
    if (
        declared_source_root.resolve(strict=True) != args.source_root
        or not args.source_root.is_dir()
    ):
        raise ValueError("Build source root must be a real directory")
    workspace = args.source_root.parent
    if workspace == Path(workspace.anchor):
        raise ValueError("A dedicated build workspace is required")
    return workspace


def artifact_hashes(root: Path, ref: str, old_host: dict, artifacts: dict) -> dict:
    hashes = {
        p: sha(git(root, "show", f"{ref}:{p}"))
        for p in old_host["artifact_sha256"]
        if "/dist/" not in p
    }
    for path, row in artifacts.items():
        for plugin in PLUGINS:
            prefix = f"{PLUGIN_ROOT}/{plugin}/"
            if path.startswith(prefix) and row[7]:
                hashes[f"{PLUGIN_SOURCE}/{plugin}/dist/{path.removeprefix(prefix)}"] = (
                    row[7]
                )
    return hashes


def materialize(root: Path, args: argparse.Namespace) -> dict[Path, bytes]:
    """Verify real bytes first; derive all release hashes/pins only afterwards."""
    workspace = build_workspace(args)
    inputs = source_inputs(root, args.source_root, args.source_ref)
    old_host = json.loads(
        git(root, "show", f"{args.source_ref}:{OWNER}/{HOST_MANIFEST}")
    )
    old_managed = json.loads(
        git(root, "show", f"{args.source_ref}:{OWNER}/managed-image.json")
    )
    if (
        old_host["plugin_release_date"]
        != json.loads((root / OWNER / HOST_MANIFEST).read_text())["plugin_release_date"]
    ):
        raise ValueError("Plugin release input changed after build")
    recipe = git(root, "show", f"{args.source_ref}:{OWNER}/Dockerfile.host")
    artifacts = context_records(args.context, recipe, within=workspace)
    base_ref = old_host["base_image"]
    if not re.fullmatch(r"grafana/grafana@sha256:[0-9a-f]{64}", base_ref):
        raise ValueError("Unsupported official base")
    base = json.loads(
        subprocess.check_output(
            [native.docker_path(), "image", "inspect", "--", base_ref], text=True
        )
    )[0]
    if base_ref not in base.get("RepoDigests", []):
        raise ValueError("Official base digest was not inspected")
    host, built = native.inspect(args.host_image), native.inspect(args.built_host)
    host_files, built_files = (
        native.records(args.host_image),
        native.records(args.built_host),
    )
    native.verify_plugin_bundles(host_files, rebuilt_plugins(args.source_root))
    host_proof = verify_host(
        base,
        built,
        host,
        native.records(base["Id"]),
        built_files,
        host_files,
        artifacts,
        args.host_image,
    )
    managed, built_managed = (
        native.inspect(args.managed_image),
        native.inspect(args.built_managed),
    )
    managed_proof = native.verify(
        host,
        built_managed,
        managed,
        host_files,
        native.records(args.built_managed),
        native.records(args.managed_image),
        args.managed_image,
    )
    new_host = deepcopy(old_host)
    hashes = artifact_hashes(root, args.source_ref, old_host, artifacts)
    new_host.update(
        image=args.host_image,
        artifact_sha256=hashes,
        acceptance="Source-built artifact identity verified; CI reproduction and runtime rollout are independent acceptance gates.",
        delivery_source={
            "source_ref": args.source_ref,
            "inputs": inputs,
            "context_sha256": file_sha(args.context, within=workspace),
            "host_artifact_parity": host_proof,
        },
    )
    replacements = {
        old_host["image"]: args.host_image,
        old_managed["image"]: args.managed_image,
    }
    text_paths = (
        f"{OWNER}/Dockerfile.managed",
        f"{OWNER}/compose.acceptance.yml",
        f"{OWNER}/compose.managed-acceptance.yml",
        "docker-compose.monitoring.yml",
    )
    outputs = {}
    for path in text_paths:
        text = git(root, "show", f"{args.source_ref}:{path}").decode()
        for old, new in replacements.items():
            text = text.replace(old, new)
        outputs[root / path] = text.encode()
    test = "tests/integration/test_grafana_datasource_provisioning.py"
    outputs[root / test] = git(root, "show", f"{args.source_ref}:{test}").replace(
        old_managed["image"].split(":")[-1].encode(),
        args.managed_image.split(":")[-1].encode(),
    )
    new_managed = {
        **old_managed,
        "image": args.managed_image,
        "parent_image": args.host_image,
        "dockerfile_sha256": sha(outputs[root / OWNER / "Dockerfile.managed"]),
        "acceptance": "Artifact verified as the declared parent minus Scenes; runtime rollout remains independent.",
        "delivery_source": {
            "source_ref": args.source_ref,
            "artifact_parity": managed_proof,
        },
    }
    for name, payload in (
        (HOST_MANIFEST, new_host),
        ("managed-image.json", new_managed),
    ):
        outputs[root / OWNER / name] = (json.dumps(payload, indent=2) + "\n").encode()
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "host-image",
        "managed-image",
        "built-host",
        "built-managed",
        "source-ref",
    ):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)
    root = native.ROOT.resolve()
    try:
        if not native.IMAGE.fullmatch(args.host_image) or not native.IMAGE.fullmatch(
            args.managed_image
        ):
            raise ValueError("Immutable registry references required")
        if not native.CONFIG_ID.fullmatch(
            args.built_host
        ) or not native.CONFIG_ID.fullmatch(args.built_managed):
            raise ValueError("Immutable built config identities required")
        outputs = materialize(root, args)
        if args.update:
            # Refuse to overwrite concurrent edits; the declared source and a
            # previously materialized identical result are the only valid states.
            for path, data in outputs.items():
                validate_target(path)
                baseline = git(
                    root,
                    "show",
                    f"{args.source_ref}:{path.relative_to(root).as_posix()}",
                )
                actual = path.read_bytes().replace(b"\r\n", b"\n")
                if actual not in (baseline.replace(b"\r\n", b"\n"), data):
                    raise ValueError("Concurrent release output change: " + str(path))
            for path, data in outputs.items():
                atomic_write(path, data)
        stale = [
            str(p.relative_to(root))
            for p, data in outputs.items()
            if p.read_bytes().replace(b"\r\n", b"\n") != data
        ]
        if stale:
            print("Delivery pins are stale: " + ", ".join(stale))
            return 1
        print(
            "PASS: complete physical artifact parity; no runtime/CI acceptance inferred"
        )
        return 0
    except (
        ValueError,
        KeyError,
        OSError,
        RuntimeError,
        tarfile.TarError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"Delivery refresh refused: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

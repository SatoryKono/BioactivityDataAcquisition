"""Generate a coupled release only from successful candidate CI and live images.

No deployment or lifecycle approval is performed. Previous manifests and pins
are retained in release_history. Default-delivery CI remains a separate gate.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from collections.abc import Callable
from typing import TYPE_CHECKING

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if TYPE_CHECKING:
    from scripts.ops.observability import refresh_router_host_provenance as provenance
else:
    spec = importlib.util.spec_from_file_location(
        "host_provenance",
        ROOT / "scripts/ops/observability/refresh_router_host_provenance.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError("Unable to load host provenance module")
    provenance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(provenance)
type JsonObject = provenance.JsonObject
require: Callable[[bool, str], None] = provenance.require
sha256: Callable[[bytes], str] = provenance.sha256
IMAGE = re.compile(r"satorykono/bioetl-grafana-router7-canvas@sha256:[0-9a-f]{64}")
HOST_PATH = "grafana/tooling/router-v7-bridge/host-image.json"
MANAGED_PATH = "grafana/tooling/router-v7-bridge/managed-image.json"
RECIPE_PATH = "grafana/tooling/router-v7-bridge/Dockerfile.managed"
DIST_FRAGMENT = "/dist/"
HOST_COMPOSE_SUFFIX = "/compose.acceptance.yml"
FROM_PREFIX = "FROM "
COMPOSE_PATHS = (
    "grafana/tooling/router-v7-bridge/compose.acceptance.yml",
    "grafana/tooling/router-v7-bridge/compose.managed-acceptance.yml",
    "docker-compose.monitoring.yml",
)


def _canonical_mapping(
    lines: list[str], indent: int
) -> dict[str, tuple[str, list[str]]]:
    """Parse only the owned plain-key block syntax, rejecting duplicate keys."""
    entries: dict[str, tuple[str, list[str]]] = {}
    current: str | None = None
    for line in lines:
        level = len(line) - len(line.lstrip())
        if level == indent:
            key = re.fullmatch(rf" {{{indent}}}([A-Za-z_][A-Za-z0-9_-]*):(.*)", line)
            if key is None:
                raise ValueError("Unsupported Compose mapping key")
            name, value = key.groups()
            require(name not in entries, "Duplicate Compose mapping key")
            entries[name] = (value, [])
            current = name
        else:
            if level <= indent or current is None:
                raise ValueError("Unsupported Compose indentation")
            entries[current][1].append(line)
    return entries


def _grafana_image_binding(text: str) -> str:
    require("\t" not in text, "Unsupported Compose indentation")
    lines = [
        line
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    root = _canonical_mapping(lines, 0)
    require(
        "services" in root and not root["services"][0].strip(),
        "Noncanonical services block",
    )
    services = _canonical_mapping(root["services"][1], 2)
    require("grafana" in services, "Missing Grafana service")
    require(
        all(not value.strip() for value, _ in services.values()),
        "Noncanonical service block",
    )
    grafana = _canonical_mapping(services["grafana"][1], 4)
    require(
        "image" in grafana and not grafana["image"][1],
        "Missing/scalar Grafana image required",
    )
    return grafana["image"][0].strip()


def validate_delivery_bindings(
    outputs: dict[str, bytes], image: str, managed_image: str
) -> None:
    """Fail closed on departures from the owned block-style Compose bindings."""
    for path in COMPOSE_PATHS:
        expected = image if path.endswith(HOST_COMPOSE_SUFFIX) else managed_image
        require(
            _grafana_image_binding(outputs[path].decode()) == expected,
            "Unexpected Grafana service delivery binding: " + path,
        )
    instructions = [
        line.split()
        for line in outputs[RECIPE_PATH].decode().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    parents = [parts[1:] for parts in instructions if parts[0].upper() == "FROM"]
    require(parents == [[image]], "Unexpected managed recipe parent")


def _validate_release_inventory(
    host: JsonObject, dist: dict[str, str], inputs: dict[str, str]
) -> None:
    old_dist = {
        path: value
        for path, value in provenance.string_map(
            host["artifact_sha256"], "Invalid artifact digest map"
        ).items()
        if DIST_FRAGMENT in path
    }
    require(set(dist) == set(old_dist), "Release artifact inventory changed")
    require(
        all(
            value == old_dist[path] or path.endswith(".js.map")
            for path, value in dist.items()
        ),
        "Release would change runtime assets beyond source maps",
    )
    require(
        bool(inputs)
        and all(
            path in inputs
            for path in provenance.json_object(host["artifact_sha256"])
            if DIST_FRAGMENT not in path
        ),
        "Source provenance inventory shrank",
    )


def build_release_files(
    original: dict[str, bytes],
    run: JsonObject,
    artifact: JsonObject,
    parity: JsonObject,
    inputs: dict[str, str],
    source_tree: str,
    dist: dict[str, str],
    managed_receipt: JsonObject,
    generator_digest: str,
) -> dict[str, bytes]:
    """Render owned outputs without inventing image/source/CI identities."""
    require(
        run.get("status") == "completed" and run.get("conclusion") == "success",
        "Release source CI must have succeeded",
    )
    host = provenance.json_object(json.loads(original[HOST_PATH]))
    managed = provenance.json_object(json.loads(original[MANAGED_PATH]))
    image = provenance.text(
        parity.get("declared_image", ""), "Unapproved immutable release image"
    )
    managed_image = provenance.text(
        managed_receipt.get("declared_image", ""), "Unapproved immutable release image"
    )
    require(
        parity.get("status") == "PASS"
        and parity.get("qualification_target") == "candidate",
        "Promotion requires explicit successful candidate image parity",
    )
    require(
        bool(IMAGE.fullmatch(image)) and bool(IMAGE.fullmatch(managed_image)),
        "Unapproved immutable release image",
    )
    require(
        managed_receipt.get("status") == "PASS"
        and managed_receipt.get("scenes_installed") is False,
        "Managed image parity is missing",
    )
    require(
        managed_receipt.get("parent_image") == image, "Managed parent image mismatch"
    )
    _validate_release_inventory(host, dist, inputs)
    result = copy.deepcopy(host)
    outputs = dict(original)
    promotion: JsonObject = {
        "source_commit": run["head_sha"],
        "source_tree": source_tree,
        "ci_run_id": run["id"],
        "ci_run_attempt": run["run_attempt"],
        "ci_run_url": run["html_url"],
        "original_artifact_id": artifact["id"],
        "original_zip_sha256": provenance.text(
            artifact["digest"], "Invalid artifact digest"
        ).removeprefix("sha256:"),
        "generator_sha256": generator_digest,
        "qualification": "CI_CANDIDATE_IMAGE_ARTIFACT_PARITY",
        "default_delivery_ci_claimed": False,
        "runtime_rollout_claimed": False,
    }
    if host["image"] != image:
        require(
            managed["parent_image"] == host["image"],
            "Existing managed parent is inconsistent",
        )
        history = provenance.json_list(copy.deepcopy(host.get("release_history", [])))
        prior_host = copy.deepcopy(host)
        prior_host.pop("release_history", None)
        history.append(
            {
                "host_manifest": prior_host,
                "managed_manifest": copy.deepcopy(managed),
                "managed_recipe": original[RECIPE_PATH].decode(),
                "compose": {path: original[path].decode() for path in COMPOSE_PATHS},
            }
        )
        result["release_history"] = history
        recipe = original[RECIPE_PATH].decode()
        require(
            recipe.count(
                FROM_PREFIX + provenance.text(host["image"], "Invalid host image")
            )
            == 1,
            "Unexpected managed recipe parent",
        )
        outputs[RECIPE_PATH] = recipe.replace(
            FROM_PREFIX + provenance.text(host["image"], "Invalid host image"),
            FROM_PREFIX + image,
        ).encode()
        for path in COMPOSE_PATHS:
            old = (
                provenance.text(host["image"], "Invalid host image")
                if path.endswith(HOST_COMPOSE_SUFFIX)
                else provenance.text(managed["image"], "Invalid managed image")
            )
            new = image if path.endswith(HOST_COMPOSE_SUFFIX) else managed_image
            text = original[path].decode()
            require(
                text.count(old) == 1, "Unexpected compose delivery binding: " + path
            )
            outputs[path] = text.replace(old, new).encode()
        result["acceptance"] = (
            "Candidate artifact parity verified in CI; "
            "default delivery CI and runtime rollout remain separate."
        )
    else:
        require(
            host.get("release_promotion") == promotion,
            "Existing promotion conflicts with this capture",
        )
        require(
            managed["image"] == managed_image and managed["parent_image"] == image,
            "Existing managed release differs",
        )
    validate_delivery_bindings(outputs, image, managed_image)
    result["image"] = image
    provenance.json_object(result["artifact_sha256"]).update(inputs)
    provenance.json_object(result["artifact_sha256"]).update(dist)
    result["release_promotion"] = promotion
    result["delivery_source"] = {
        "source_ref": run["head_sha"],
        "inputs": provenance.json_strings(inputs),
        "context_sha256": sha256(
            json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
        ),
        "context_hash_contract": "sha256 of canonical JSON verified input map",
        "host_artifact_parity": {
            "built_config_digest": parity["built_image_config_digest"],
            "registry_config_digest": parity["declared_image_config_digest"],
            "image": image,
            "rootfs_sha256": parity["rootfs_sha256"],
        },
        "candidate_ci": promotion,
    }
    managed["image"] = managed_image
    managed["parent_image"] = image
    managed["dockerfile_sha256"] = sha256(outputs[RECIPE_PATH])
    managed["delivery_source"] = {
        "source_ref": run["head_sha"],
        "artifact_parity": managed_receipt,
    }
    outputs[HOST_PATH] = (json.dumps(result, indent=2) + "\n").encode()
    outputs[MANAGED_PATH] = (json.dumps(managed, indent=2) + "\n").encode()
    return outputs


def original_plugin_digests(
    run: JsonObject, jobs: JsonObject, artifacts: JsonObject, evidence: Path
) -> dict[str, str]:
    result: dict[str, str] = {}
    for plugin in ("bioetl-scenes-app", "bioetl-selectorshell-panel"):
        rows = [
            row
            for row in provenance.object_rows(
                artifacts["artifacts"], "Incomplete artifact listing"
            )
            if row["name"] == "host-plugin-" + plugin
        ]
        require(len(rows) == 1, "Missing/duplicate original plugin artifact")
        row = rows[0]
        job = next(
            job
            for job in provenance.object_rows(
                jobs["jobs"], "Missing/duplicate Router jobs"
            )
            if job["name"] == "plugin-tests (" + plugin + ")"
        )
        require(
            row.get("expired") is False
            and provenance.json_object(row["workflow_run"])["id"] == run["id"]
            and provenance.json_object(row["workflow_run"])["head_sha"]
            == run["head_sha"]
            and provenance.timestamp(job["started_at"])
            <= provenance.timestamp(row["created_at"])
            <= provenance.timestamp(job["completed_at"]),
            "Foreign/expired plugin artifact attempt",
        )
        raw = provenance.api(f"actions/artifacts/{row['id']}/zip")
        require(
            row["size_in_bytes"] == len(raw)
            and row["digest"] == "sha256:" + sha256(raw),
            "Original plugin ZIP identity mismatch",
        )
        (evidence / (plugin + ".zip")).write_bytes(raw)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                path = PurePosixPath(item.filename)
                require(
                    not path.is_absolute()
                    and ".." not in path.parts
                    and "\\" not in item.filename,
                    "Unsafe plugin artifact member",
                )
                key = "grafana/plugins/" + plugin + DIST_FRAGMENT + item.filename
                require(key not in result, "Duplicate plugin artifact member")
                result[key] = sha256(archive.read(item))
    return result


def live_managed_parity(
    host_image: str,
    managed_image: str,
    parity: JsonObject,
    recipe: bytes,
    run_id: int,
    evidence: Path,
) -> JsonObject:
    """Inspect registered artifacts and independently rebuild the managed recipe."""
    sys.path.insert(0, str(ROOT))
    from scripts.ops.observability.grafana.router_managed_image import verify
    from scripts.ops.observability.grafana.router_rootfs import filesystem_records

    candidates = (
        (
            Path("C:/Program Files/Docker/Docker/resources/bin/docker.exe"),
            Path("E:/Programs/Docker/resources/bin/docker.exe"),
        )
        if sys.platform == "win32"
        else (Path("/usr/bin/docker"),)
    )
    docker = next((path for path in candidates if path.is_file()), None)
    require(docker is not None, "Trusted Docker executable is unavailable")
    commands: list[dict[str, object]] = []

    def execute(*args: str) -> bytes:
        argv = [str(docker), *args]
        process = subprocess.run(argv, cwd=ROOT, capture_output=True, check=False)
        number = len(commands)
        (evidence / f"docker-{number}.stdout").write_bytes(process.stdout)
        (evidence / f"docker-{number}.stderr").write_bytes(process.stderr)
        commands.append(
            {
                "argv": argv,
                "cwd": str(ROOT),
                "exit_code": process.returncode,
                "stdout_sha256": sha256(process.stdout),
                "stderr_sha256": sha256(process.stderr),
            }
        )
        (evidence / "docker-commands.json").write_bytes(
            (json.dumps(commands, indent=2) + "\n").encode("utf-8")
        )
        process.check_returncode()
        return process.stdout

    def records(image: str) -> JsonObject:
        cid = (
            execute("create", "--entrypoint", "/bin/true", "--", image).decode().strip()
        )
        require(
            bool(re.fullmatch(r"[0-9a-f]{64}", cid)), "Invalid temporary container ID"
        )
        try:
            argv = [str(docker), "export", cid]
            number = len(commands)
            stderr_path = evidence / f"docker-{number}.stderr"
            with (
                stderr_path.open("wb") as stderr,
                subprocess.Popen(
                    argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=stderr
                ) as process,
            ):
                try:
                    if process.stdout is None:
                        raise ValueError("Missing Docker export stdout")
                    result = provenance.json_object(
                        filesystem_records(process.stdout), "Invalid filesystem records"
                    )
                except BaseException:
                    process.kill()
                    process.wait()
                    raise
                code = process.wait()
            commands.append(
                {
                    "argv": argv,
                    "cwd": str(ROOT),
                    "exit_code": code,
                    "stderr_sha256": sha256(stderr_path.read_bytes()),
                    "canonical_filesystem_records_sha256": sha256(
                        json.dumps(
                            result, sort_keys=True, separators=(",", ":")
                        ).encode()
                    ),
                    "stdout_contract": "tar consumed by filesystem_records; original tar not retained",
                }
            )
            (evidence / "docker-commands.json").write_bytes(
                (json.dumps(commands, indent=2) + "\n").encode("utf-8")
            )
            require(code == 0, "Docker export failed")
            return result
        finally:
            execute("rm", "-v", cid)

    for image in (host_image, managed_image):
        require(bool(IMAGE.fullmatch(image)), "Unapproved immutable image")
        execute("pull", image)
    host = provenance.object_rows(
        json.loads(execute("image", "inspect", host_image)), "Invalid image inspection"
    )[0]
    delivered = provenance.object_rows(
        json.loads(execute("image", "inspect", managed_image)),
        "Invalid image inspection",
    )[0]
    require(
        host_image in provenance.json_list(host["RepoDigests"])
        and managed_image in provenance.json_list(delivered["RepoDigests"]),
        "Uninspected registry digest",
    )
    require(
        host["Id"] == parity["declared_image_config_digest"]
        and provenance.json_object(host["RootFS"])["Layers"]
        == parity["declared_layers"],
        "Registry host differs from original CI parity",
    )
    parent_files = records(host_image)
    parent_hash = sha256(
        json.dumps(parent_files, sort_keys=True, separators=(",", ":")).encode()
    )
    require(
        parent_hash == parity["rootfs_sha256"],
        "Registry host full rootfs differs from CI",
    )
    recipe_path = evidence / "Dockerfile.managed"
    recipe_path.write_bytes(recipe)
    tag = "bioetl-router-managed:issue12474-ci" + str(run_id)
    execute(
        "build",
        "--provenance=false",
        "--file",
        str(recipe_path),
        "--tag",
        tag,
        str(evidence),
    )
    built = provenance.object_rows(
        json.loads(execute("image", "inspect", tag)), "Invalid image inspection"
    )[0]
    built_files, delivered_files = records(tag), records(managed_image)
    for name, data in (
        ("host", parent_files),
        ("managed-built", built_files),
        ("managed-registry", delivered_files),
    ):
        (evidence / (name + "-filesystem-records.json")).write_bytes(
            (json.dumps(data, sort_keys=True) + "\n").encode("utf-8")
        )
    receipt = provenance.json_object(
        verify(
            host,
            built,
            delivered,
            parent_files,
            built_files,
            delivered_files,
            managed_image,
        ),
        "Invalid managed image receipt",
    )
    receipt["parent_image"] = host_image
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci-run-id", required=True, type=int)
    parser.add_argument("--image", required=True)
    parser.add_argument("--managed-image", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    require(
        args.ci_run_id > 0
        and bool(IMAGE.fullmatch(args.image))
        and bool(IMAGE.fullmatch(args.managed_image)),
        "Positive source CI run and owned immutable images required",
    )
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    snapshots: dict[str, JsonObject] = {}
    prefix = f"actions/runs/{args.ci_run_id}"
    for name, endpoint in (
        ("run", prefix),
        ("jobs", prefix + "/jobs?per_page=100"),
        ("artifacts", prefix + "/artifacts?per_page=100"),
    ):
        raw = provenance.api(endpoint)
        (evidence / (name + ".json")).write_bytes(raw)
        snapshots[name] = provenance.json_object(json.loads(raw))
    run, jobs, artifacts = (snapshots[name] for name in ("run", "jobs", "artifacts"))
    require(run["id"] == args.ci_run_id, "CI run identity mismatch")
    rows = [
        row
        for row in provenance.object_rows(
            artifacts["artifacts"], "Incomplete artifact listing"
        )
        if row["name"] == provenance.ARTIFACT
    ]
    require(len(rows) == 1, "Missing/duplicate image parity artifact")
    raw = provenance.api(f"actions/artifacts/{rows[0]['id']}/zip")
    (evidence / "original-image-receipts.zip").write_bytes(raw)
    artifact, parity = provenance.validate_capture(run, jobs, artifacts, raw)
    require(
        parity.get("qualification_target") == "candidate"
        and parity["declared_image"] == args.image,
        "Requested image was not the qualified CI candidate",
    )
    originals = {
        path: (ROOT / path).read_bytes()
        for path in (HOST_PATH, MANAGED_PATH, RECIPE_PATH, *COMPOSE_PATHS)
    }
    host = provenance.json_object(json.loads(originals[HOST_PATH]))
    captured = provenance.json_object(
        json.loads(
            subprocess.check_output(
                [
                    "git",
                    "show",
                    provenance.text(run["head_sha"], "Invalid source SHA")
                    + ":"
                    + HOST_PATH,
                ],
                cwd=ROOT,
            )
        )
    )
    for key in (
        "plugin_release_date",
        "base_image",
        "grafana_version",
        "router_version",
        "upstream_sha",
    ):
        require(
            host[key] == captured[key], "Host build contract changed after CI: " + key
        )
    inputs, tree = provenance.source_inputs(
        ROOT, provenance.text(run["head_sha"], "Invalid source SHA"), host
    )
    dist = original_plugin_digests(run, jobs, artifacts, evidence)
    recipe = originals[RECIPE_PATH].replace(
        provenance.text(host["image"], "Invalid host image").encode(),
        args.image.encode(),
    )
    managed = live_managed_parity(
        args.image, args.managed_image, parity, recipe, args.ci_run_id, evidence
    )
    outputs = build_release_files(
        originals,
        run,
        artifact,
        parity,
        inputs,
        tree,
        dist,
        managed,
        sha256(Path(__file__).read_bytes()),
    )
    for path, content in originals.items():
        target = evidence / "before" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        require(
            (ROOT / path).read_bytes() == content,
            "Concurrent release file change: " + path,
        )
    if args.check:
        require(outputs == originals, "Coupled release artifacts are stale")
    else:
        for path, content in outputs.items():
            (ROOT / path).write_bytes(content)
    result = {
        "source_commit": run["head_sha"],
        "ci_run_id": run["id"],
        "image": args.image,
        "managed_image": args.managed_image,
        "check": args.check,
        "outputs": {path: sha256(content) for path, content in outputs.items()},
        "default_delivery_ci_claimed": False,
        "admission_claimed": False,
    }
    (evidence / "result.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode("utf-8")
    )
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0

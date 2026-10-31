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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location(
    "host_provenance",
    HERE.parents[3]
    / "scripts/ops/observability/grafana/refresh_router_host_provenance.py",
)
provenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provenance)
require = provenance.require
sha256 = provenance.sha256
IMAGE = re.compile(r"satorykono/bioetl-grafana-router7-canvas@sha256:[0-9a-f]{64}")
HOST_PATH = "grafana/tooling/router-v7-bridge/host-image.json"
MANAGED_PATH = "grafana/tooling/router-v7-bridge/managed-image.json"
RECIPE_PATH = "grafana/tooling/router-v7-bridge/Dockerfile.managed"
COMPOSE_PATHS = (
    "grafana/tooling/router-v7-bridge/compose.acceptance.yml",
    "grafana/tooling/router-v7-bridge/compose.managed-acceptance.yml",
    "docker-compose.monitoring.yml",
)


def validate_delivery_bindings(
    outputs: dict[str, bytes], image: str, managed_image: str
):
    """Fail closed on departures from the owned block-style Compose bindings."""
    for path in COMPOSE_PATHS:
        text = outputs[path].decode()
        require("\t" not in text, "Unsupported Compose indentation: " + path)
        services = 0
        grafana = 0
        in_services = False
        in_grafana = False
        images = []
        top_keys = set()
        service_keys = set()
        grafana_keys = set()
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                key = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(.*)", line)
                require(key is not None, "Unsupported Compose top-level key: " + path)
                name, value = key.groups()
                require(name not in top_keys, "Duplicate Compose key: " + path)
                top_keys.add(name)
                in_services = name == "services"
                require(
                    not in_services or not value.strip(), "Noncanonical services block"
                )
                services += int(in_services)
                in_grafana = False
            elif in_services and indent == 2:
                key = re.fullmatch(r"  ([A-Za-z_][A-Za-z0-9_-]*):", line)
                require(key is not None, "Unsupported Compose service key: " + path)
                name = key.group(1)
                require(name not in service_keys, "Duplicate Compose service: " + path)
                service_keys.add(name)
                in_grafana = name == "grafana"
                grafana += int(in_grafana)
            elif in_grafana and indent == 4:
                key = re.fullmatch(r"    ([A-Za-z_][A-Za-z0-9_-]*):(.*)", line)
                require(key is not None, "Unsupported Grafana mapping key: " + path)
                name, value = key.groups()
                require(name not in grafana_keys, "Duplicate Grafana key: " + path)
                grafana_keys.add(name)
                if name == "image":
                    images.append(value.strip())
        expected = image if path.endswith("/compose.acceptance.yml") else managed_image
        require(
            services == 1 and grafana == 1 and images == [expected],
            "Unexpected Grafana service delivery binding: " + path,
        )
    parents = re.findall(r"(?im)^\s*FROM\s+([^\r\n]+)$", outputs[RECIPE_PATH].decode())
    require(parents == [image], "Unexpected managed recipe parent")


def build_release_files(
    original: dict,
    run: dict,
    artifact: dict,
    parity: dict,
    inputs: dict,
    source_tree: str,
    dist: dict,
    managed_receipt: dict,
    generator_digest: str,
) -> dict[str, bytes]:
    """Render owned outputs without inventing image/source/CI identities."""
    require(
        run.get("status") == "completed" and run.get("conclusion") == "success",
        "Release source CI must have succeeded",
    )
    host = json.loads(original[HOST_PATH])
    managed = json.loads(original[MANAGED_PATH])
    image = parity.get("declared_image", "")
    managed_image = managed_receipt.get("declared_image", "")
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
    old_dist = {
        path: value
        for path, value in host["artifact_sha256"].items()
        if "/dist/" in path
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
        inputs
        and all(
            path in inputs for path in host["artifact_sha256"] if "/dist/" not in path
        ),
        "Source provenance inventory shrank",
    )
    result = copy.deepcopy(host)
    outputs = dict(original)
    promotion = {
        "source_commit": run["head_sha"],
        "source_tree": source_tree,
        "ci_run_id": run["id"],
        "ci_run_attempt": run["run_attempt"],
        "ci_run_url": run["html_url"],
        "original_artifact_id": artifact["id"],
        "original_zip_sha256": artifact["digest"].removeprefix("sha256:"),
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
        history = copy.deepcopy(host.get("release_history", []))
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
            recipe.count("FROM " + host["image"]) == 1,
            "Unexpected managed recipe parent",
        )
        outputs[RECIPE_PATH] = recipe.replace(
            "FROM " + host["image"], "FROM " + image
        ).encode()
        for path in COMPOSE_PATHS:
            old = (
                host["image"]
                if path.endswith("/compose.acceptance.yml")
                else managed["image"]
            )
            new = image if path.endswith("/compose.acceptance.yml") else managed_image
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
    result["artifact_sha256"].update(inputs)
    result["artifact_sha256"].update(dist)
    result["release_promotion"] = promotion
    result["delivery_source"] = {
        "source_ref": run["head_sha"],
        "inputs": inputs,
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
    run: dict, jobs: dict, artifacts: dict, evidence: Path
) -> dict:
    result = {}
    for plugin in ("bioetl-scenes-app", "bioetl-selectorshell-panel"):
        rows = [
            row
            for row in artifacts["artifacts"]
            if row["name"] == "host-plugin-" + plugin
        ]
        require(len(rows) == 1, "Missing/duplicate original plugin artifact")
        row = rows[0]
        job = next(
            job
            for job in jobs["jobs"]
            if job["name"] == "plugin-tests (" + plugin + ")"
        )
        require(
            row.get("expired") is False
            and row["workflow_run"]["id"] == run["id"]
            and row["workflow_run"]["head_sha"] == run["head_sha"]
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
                key = "grafana/plugins/" + plugin + "/dist/" + item.filename
                require(key not in result, "Duplicate plugin artifact member")
                result[key] = sha256(archive.read(item))
    return result


def live_managed_parity(
    host_image: str,
    managed_image: str,
    parity: dict,
    recipe: bytes,
    run_id: int,
    evidence: Path,
) -> dict:
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
    commands = []

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
        (evidence / "docker-commands.json").write_text(
            json.dumps(commands, indent=2) + "\n"
        )
        process.check_returncode()
        return process.stdout

    def records(image: str) -> dict:
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
                    result = filesystem_records(process.stdout)
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
            (evidence / "docker-commands.json").write_text(
                json.dumps(commands, indent=2) + "\n"
            )
            require(code == 0, "Docker export failed")
            return result
        finally:
            execute("rm", "-v", cid)

    for image in (host_image, managed_image):
        require(bool(IMAGE.fullmatch(image)), "Unapproved immutable image")
        execute("pull", image)
    host = json.loads(execute("image", "inspect", host_image))[0]
    delivered = json.loads(execute("image", "inspect", managed_image))[0]
    require(
        host_image in host["RepoDigests"] and managed_image in delivered["RepoDigests"],
        "Uninspected registry digest",
    )
    require(
        host["Id"] == parity["declared_image_config_digest"]
        and host["RootFS"]["Layers"] == parity["declared_layers"],
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
    built = json.loads(execute("image", "inspect", tag))[0]
    built_files, delivered_files = records(tag), records(managed_image)
    for name, data in (
        ("host", parent_files),
        ("managed-built", built_files),
        ("managed-registry", delivered_files),
    ):
        (evidence / (name + "-filesystem-records.json")).write_text(
            json.dumps(data, sort_keys=True) + "\n"
        )
    receipt = verify(
        host,
        built,
        delivered,
        parent_files,
        built_files,
        delivered_files,
        managed_image,
    )
    receipt["parent_image"] = host_image
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci-run-id", required=True, type=int)
    parser.add_argument("--image", required=True)
    parser.add_argument("--managed-image", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    require(
        args.ci_run_id > 0
        and bool(IMAGE.fullmatch(args.image))
        and bool(IMAGE.fullmatch(args.managed_image)),
        "Positive source CI run and owned immutable images required",
    )
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    snapshots = {}
    prefix = f"actions/runs/{args.ci_run_id}"
    for name, endpoint in (
        ("run", prefix),
        ("jobs", prefix + "/jobs?per_page=100"),
        ("artifacts", prefix + "/artifacts?per_page=100"),
    ):
        raw = provenance.api(endpoint)
        (evidence / (name + ".json")).write_bytes(raw)
        snapshots[name] = json.loads(raw)
    run, jobs, artifacts = (snapshots[name] for name in ("run", "jobs", "artifacts"))
    require(run["id"] == args.ci_run_id, "CI run identity mismatch")
    rows = [row for row in artifacts["artifacts"] if row["name"] == provenance.ARTIFACT]
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
    host = json.loads(originals[HOST_PATH])
    captured = json.loads(
        subprocess.check_output(
            ["git", "show", run["head_sha"] + ":" + HOST_PATH], cwd=ROOT
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
    inputs, tree = provenance.source_inputs(ROOT, run["head_sha"], host)
    dist = original_plugin_digests(run, jobs, artifacts, evidence)
    recipe = originals[RECIPE_PATH].replace(host["image"].encode(), args.image.encode())
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
    (evidence / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

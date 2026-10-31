"""Revalidate unchanged image delivery from original successful Router CI receipts.

This updates source bindings only after full image parity, not browser acceptance.
Historical delivery_source and prior revalidations remain unchanged.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

REPOSITORY = "SatoryKono/BioactivityDataAcquisition"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST = "grafana/tooling/router-v7-bridge/host-image.json"
WORKFLOW = ".github/workflows/router-v7-bridge.yml"
ARTIFACT = "router-v7-host-image-receipts"
BUILD_SUPPORT = (
    ".github/workflows/router-v7-bridge.yml",
    "grafana/tooling/router-v7-bridge/package.json",
    "grafana/tooling/router-v7-bridge/package-lock.json",
    "grafana/tooling/router-v7-bridge/index.d.ts",
    "grafana/tooling/router-v7-bridge/README.md",
    "grafana/tooling/router-v7-bridge/bioetl-grafana-router-v7-bridge-0.3.0.tgz",
    "grafana/tooling/router-v7-bridge/verify-host-image.mjs",
    "grafana/tooling/router-v7-bridge/verify-packed-bridge.mjs",
    "scripts/ops/observability/grafana/router_rootfs.py",
    "scripts/ops/observability/grafana/router_managed_image.py",
)
JOBS = {
    "bridge-tests",
    "plugin-tests (bioetl-scenes-app)",
    "plugin-tests (bioetl-selectorshell-panel)",
    "host-build",
}
SCOPES = {
    "/usr/share/grafana/public/build",
    "/usr/share/grafana/data/plugins-bundled/bioetl-scenes-app",
    "/usr/share/grafana/data/plugins-bundled/bioetl-selectorshell-panel",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def timestamp(value: str) -> datetime:
    require(isinstance(value, str) and bool(value), "Missing CI timestamp")
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo is not None, "CI timestamp must include timezone")
    return parsed


def validate_capture(
    run: dict, jobs: dict, artifacts: dict, archive: bytes
) -> tuple[dict, dict]:
    """Authenticate original archive bytes against actual CI metadata."""
    require(
        run.get("status") == "completed" and run.get("conclusion") == "success",
        "Router workflow must have completed successfully",
    )
    require(
        run.get("path") == WORKFLOW and run.get("event") == "workflow_dispatch",
        "Wrong Router workflow/event",
    )
    require(
        bool(re.fullmatch(r"[0-9a-f]{40}", str(run.get("head_sha")))),
        "Invalid source SHA",
    )
    require(
        isinstance(run.get("run_attempt"), int) and run["run_attempt"] > 0,
        "Missing run attempt",
    )
    rows = jobs.get("jobs", [])
    require(
        jobs.get("total_count") == len(rows) == len(JOBS)
        and {row.get("name") for row in rows} == JOBS,
        "Missing/duplicate Router jobs",
    )
    for row in rows:
        require(
            row.get("run_id") == run["id"]
            and row.get("head_sha") == run["head_sha"]
            and row.get("run_attempt") == run["run_attempt"]
            and row.get("status") == "completed"
            and row.get("conclusion") == "success",
            "Unsuccessful or foreign Router job",
        )
    entries = artifacts.get("artifacts", [])
    require(
        artifacts.get("total_count") == len(entries) <= 100,
        "Incomplete artifact listing",
    )
    matches = [row for row in entries if row.get("name") == ARTIFACT]
    require(len(matches) == 1, "Missing/duplicate original image receipt artifact")
    artifact = matches[0]
    require(
        artifact.get("expired") is False
        and artifact.get("workflow_run", {}).get("id") == run["id"]
        and artifact.get("workflow_run", {}).get("head_sha") == run["head_sha"],
        "Expired/foreign image receipt artifact",
    )
    host = next(row for row in rows if row["name"] == "host-build")
    require(
        timestamp(host.get("started_at"))
        <= timestamp(artifact.get("created_at"))
        <= timestamp(host.get("completed_at")),
        "Image artifact belongs to a different host-build attempt",
    )
    require(
        artifact.get("size_in_bytes") == len(archive)
        and artifact.get("digest") == "sha256:" + sha256(archive),
        "Original ZIP digest/size mismatch",
    )
    with zipfile.ZipFile(io.BytesIO(archive)) as source:
        files = [row for row in source.infolist() if not row.is_dir()]
        require(
            len(files) == 2
            and {PurePosixPath(row.filename).name for row in files}
            == {"router-v7-image-build.json", "router-v7-image-parity.json"},
            "Incomplete/duplicate image receipts",
        )
        payloads = {}
        for row in files:
            path = PurePosixPath(row.filename)
            require(
                not path.is_absolute()
                and ".." not in path.parts
                and "\\" not in row.filename,
                "Unsafe receipt archive member",
            )
            payloads[path.name] = json.loads(source.read(row))
    parity = payloads["router-v7-image-parity.json"]
    build = payloads["router-v7-image-build.json"]
    require(parity.get("status") == "PASS", "Full image parity did not pass")
    for field in ("built_image_config_digest", "declared_image_config_digest"):
        require(
            bool(re.fullmatch(r"sha256:[0-9a-f]{64}", str(parity.get(field)))),
            "Missing/invalid image config digest",
        )
    require(
        build.get("containerimage.config.digest")
        == parity.get("built_image_config_digest"),
        "Build/image-parity identity mismatch",
    )
    require(
        set(parity.get("artifacts", {})) == SCOPES, "Incomplete frontend/plugin parity"
    )
    require(
        bool(re.fullmatch(r"[0-9a-f]{64}", str(parity.get("rootfs_sha256")))),
        "Missing/invalid complete rootfs digest",
    )
    for field in ("built_layers", "declared_layers"):
        layers = parity.get(field)
        require(
            isinstance(layers, list)
            and bool(layers)
            and all(
                re.fullmatch(r"sha256:[0-9a-f]{64}", str(layer)) for layer in layers
            ),
            "Missing/invalid image layer evidence",
        )
    for scope, record in parity["artifacts"].items():
        require(
            bool(re.fullmatch(r"[0-9a-f]{64}", str(record.get("tree_sha256")))),
            "Missing/invalid scope tree digest",
        )
        if "/plugins-bundled/" in scope:
            require(
                bool(re.fullmatch(r"[0-9a-f]{64}", str(record.get("module_sha256")))),
                "Missing/invalid plugin module digest",
            )
    return artifact, parity


def refresh(
    manifest: dict,
    run: dict,
    artifact: dict,
    parity: dict,
    inputs: dict[str, str],
    source_tree: str,
    generator_sha256: str,
) -> dict:
    """Retain historical delivery while recording independently rebuilt equality."""
    expected = manifest["delivery_source"]["host_artifact_parity"]
    require(
        parity.get("declared_image") == manifest["image"] == expected["image"],
        "Pinned delivery image changed",
    )
    require(
        parity.get("rootfs_sha256") == expected["rootfs_sha256"],
        "Historical rootfs mismatch",
    )
    require(
        parity.get("declared_image_config_digest")
        == expected["registry_config_digest"],
        "Registry image config mismatch",
    )
    for plugin in ("bioetl-scenes-app", "bioetl-selectorshell-panel"):
        scope = "/usr/share/grafana/data/plugins-bundled/" + plugin
        require(
            parity["artifacts"][scope]["module_sha256"]
            == manifest["artifact_sha256"][f"grafana/plugins/{plugin}/dist/module.js"],
            "Shipped plugin bytes changed",
        )
    require(
        inputs
        and all(re.fullmatch(r"[0-9a-f]{64}", value) for value in inputs.values()),
        "Missing/invalid source input digests",
    )
    require(
        all(
            path in inputs
            for path in manifest["artifact_sha256"]
            if "/dist/" not in path
        ),
        "Source input inventory shrank",
    )
    record = {
        "ci_run_id": run["id"],
        "ci_run_attempt": run["run_attempt"],
        "ci_run_url": run["html_url"],
        "source_commit": run["head_sha"],
        "source_tree": source_tree,
        "original_artifact_id": artifact["id"],
        "original_zip_sha256": artifact["digest"].removeprefix("sha256:"),
        "verified_source_inputs": inputs,
        "generator_sha256": generator_sha256,
        "full_image_parity": parity,
        "qualification": "image_artifact_parity",
        "browser_acceptance_claimed": False,
    }
    result = copy.deepcopy(manifest)
    history = result.setdefault("ci_source_revalidations", [])
    existing = [
        row
        for row in history
        if row.get("ci_run_id") == run["id"]
        and row.get("ci_run_attempt") == run["run_attempt"]
    ]
    if existing:
        require(
            len(existing) == 1 and existing[0] == record,
            "Existing qualification conflicts",
        )
    else:
        history.append(record)
    result["artifact_sha256"].update(inputs)
    return result


def api(path: str) -> bytes:
    return subprocess.check_output(
        ["gh", "api", "--allow-escape-sequences", f"repos/{REPOSITORY}/{path}"]
    )


def source_inputs(
    root: Path, source: str, manifest: dict
) -> tuple[dict[str, str], str]:
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=root)

    paths = {path for path in manifest["artifact_sha256"] if "/dist/" not in path}
    paths.update(BUILD_SUPPORT)
    roots = (
        "grafana/plugins/bioetl-scenes-app",
        "grafana/plugins/bioetl-selectorshell-panel",
        "grafana/plugins/eslint-shared-config.mjs",
        "grafana/tooling/router-v7-bridge/minimatch-legacy-compat",
    )
    captured_paths = set(
        git("ls-tree", "-r", "--name-only", source, "--", *roots).decode().splitlines()
    )
    current_paths = set(git("ls-files", "--", *roots).decode().splitlines())
    require(
        not git("ls-files", "--others", "--exclude-standard", "--", *roots).strip(),
        "Uncommitted build input additions",
    )
    require(
        captured_paths == current_paths, "Build source inventory added/deleted after CI"
    )
    paths.update(captured_paths)
    paths = {path for path in paths if "/dist/" not in path}
    require(bool(paths), "Empty build source inventory")
    result = {}
    for path in sorted(paths):
        relative = PurePosixPath(path)
        require(
            not relative.is_absolute() and ".." not in relative.parts,
            "Unsafe source path",
        )
        file = root / path
        require(
            file.is_file() and not file.is_symlink(), "Missing/redirected source input"
        )
        captured = git("show", source + ":" + path)
        require(
            captured == file.read_bytes(),
            "Source input differs from actual CI: " + path,
        )
        result[path] = sha256(captured)
    tree = git("rev-parse", source + "^{tree}").decode().strip()
    return result, tree


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci-run-id", type=int, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    require(args.ci_run_id > 0, "Positive CI run ID required")
    # A fresh directory keeps every original attempt; never overwrite evidence.
    args.evidence_dir.mkdir(parents=True, exist_ok=False)
    prefix = f"actions/runs/{args.ci_run_id}"
    raw = {
        "run": api(prefix),
        "jobs": api(prefix + "/jobs?per_page=100"),
        "artifacts": api(prefix + "/artifacts?per_page=100"),
    }
    for name, content in raw.items():
        (args.evidence_dir / (name + ".json")).write_bytes(content)
    run, jobs, artifacts = (
        json.loads(raw[name]) for name in ("run", "jobs", "artifacts")
    )
    require(run.get("id") == args.ci_run_id, "CI run identity mismatch")
    matches = [row for row in artifacts["artifacts"] if row["name"] == ARTIFACT]
    require(len(matches) == 1, "Missing/duplicate receipt artifact")
    archive = api(f"actions/artifacts/{matches[0]['id']}/zip")
    (args.evidence_dir / "original.zip").write_bytes(archive)
    artifact, parity = validate_capture(run, jobs, artifacts, archive)
    path = ROOT / MANIFEST
    before = path.read_bytes()
    (args.evidence_dir / "host-image.before.json").write_bytes(before)
    manifest = json.loads(before)
    inputs, tree = source_inputs(ROOT, run["head_sha"], manifest)
    result = refresh(
        manifest,
        run,
        artifact,
        parity,
        inputs,
        tree,
        sha256(Path(__file__).read_bytes()),
    )
    encoded = (json.dumps(result, indent=2) + "\n").encode()
    if args.check:
        require(before == encoded, "Host source provenance is stale")
    else:
        path.write_bytes(encoded)
    (args.evidence_dir / "host-image.after.json").write_bytes(encoded)
    sys.stdout.write(
        json.dumps(
            {
                "ci_run_id": run["id"],
                "source": run["head_sha"],
                "inputs": len(inputs),
                "image": manifest["image"],
                "manifest_sha256": sha256(encoded),
                "check": args.check,
            }
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

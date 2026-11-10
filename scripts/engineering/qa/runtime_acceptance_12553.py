"""Capture issue 12553 commands without conflating test success with acceptance.

Each invocation preserves byte-for-byte stdout/stderr, exit status, argv and
the actual pre-run Git identity. Evidence is separate from the static inventory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from datetime import UTC, datetime

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = Path(
    os.environ.get(
        "BIOETL_12553_BUNDLE", str(ROOT / "reports/audit-runs/12553-runtime-acceptance")
    )
)
ARCHIVE = "evidence.zip"


def evidence_names(root: Path) -> set[str]:
    """List loose and archived evidence without extracting into the checkout."""
    names = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if (root / ARCHIVE).exists():
        with zipfile.ZipFile(root / ARCHIVE) as archive:
            names.update(archive.namelist())
    return names


def evidence_exists(name: str, root: Path) -> bool:
    return name in evidence_names(root)


def read_evidence(name: str, root: Path) -> bytes:
    """Prefer the current run's loose file, then preserved archived bytes."""
    path = root / name
    if path.is_file():
        return path.read_bytes()
    if not (root / ARCHIVE).exists():
        raise FileNotFoundError(path)
    with zipfile.ZipFile(root / ARCHIVE) as archive:
        try:
            return archive.read(name)
        except KeyError as exc:
            raise FileNotFoundError(path) from exc


def pack(baseline_names: set[str] | None = None) -> None:
    """Preserve raw evidence while keeping machine logs out of the docs catalog."""
    excluded = {ARCHIVE, ARCHIVE + ".sha256"}
    names = evidence_names(BUNDLE) - excluded
    payload = {name: read_evidence(name, BUNDLE) for name in names}
    checksums = {
        name: hashlib.sha256(data).hexdigest()
        for name, data in sorted(payload.items())
        if name != "artifact-sha256.json"
    }
    payload["artifact-sha256.json"] = (json.dumps(checksums, indent=2) + "\n").encode()
    with zipfile.ZipFile(
        BUNDLE / ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    digest = hashlib.sha256((BUNDLE / ARCHIVE).read_bytes()).hexdigest()
    (BUNDLE / (ARCHIVE + ".sha256")).write_text(
        f"{digest}  {ARCHIVE}\n", encoding="ascii"
    )
    if baseline_names is None:
        prefix = BUNDLE.relative_to(ROOT).as_posix() + "/"
        baseline_names = {
            p.removeprefix(prefix)
            for p in git(
                "ls-tree", "-r", "--name-only", "origin/main", "--", prefix
            ).splitlines()
        }
    for path in BUNDLE.rglob("*"):
        name = path.relative_to(BUNDLE).as_posix()
        if path.suffix in {".txt", ".json", ".md"} and name not in baseline_names:
            path.unlink()


def verify(root: Path) -> None:
    """Verify the published byte representation, including archived trace targets."""
    archive = root / ARCHIVE
    if archive.exists():
        expected = (root / (ARCHIVE + ".sha256")).read_text().split()[0]
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise ValueError("evidence archive checksum mismatch")
    manifest = json.loads(read_evidence("artifact-sha256.json", root))
    for name, digest in manifest.items():
        if hashlib.sha256(read_evidence(name, root)).hexdigest() != digest:
            raise ValueError(f"evidence checksum mismatch: {name}")
    register = json.loads(read_evidence("coverage-register.json", root))
    if len({row["identity"] for row in register["resources"]}) != 207:
        raise ValueError("evidence register must account for 207 resources")
    for row in register["resources"]:
        for name in row["trace_refs"]:
            if not evidence_exists(name, root):
                raise ValueError(f"missing trace: {name}")
    print(f"verified {len(manifest)} evidence files and 207 resource identities")


def inputs(argv: list[str]) -> dict[str, str]:
    """Bind executed fixtures, harness and source without reading secret files."""
    paths = {
        Path(__file__),
        ROOT / "tests/helpers/runtime_acceptance_12553.py",
        ROOT / "pyproject.toml",
        ROOT / "tests/conftest.py",
    }
    paths.update((ROOT / "src/bioetl").rglob("*.py"))
    paths.update((ROOT / "configs/quality/external_resource_inventory").glob("*.json"))
    paths.add(ROOT / "configs/quality/external_resource_inventory.json")
    paths.update((ROOT / "tests/helpers").rglob("*.py"))
    for arg in argv:
        path = ROOT / arg.split("::")[0]
        if path.is_file() and path.suffix == ".py":
            paths.add(path)
        elif path.is_dir() and path.is_relative_to(ROOT / "tests"):
            paths.update(path.rglob("*.py"))
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
        if p.is_file()
    }


def git(*args: str) -> str:
    """Read Git identity without including environment values."""
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def capture(name: str, argv: list[str], timeout: int = 600) -> int:
    """Persist genuine command streams, including failed or timed-out runs."""
    if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in name):
        raise ValueError("name must be lowercase ASCII letters/digits/hyphens")
    receipt = BUNDLE / f"{name}-command.json"
    if receipt.exists():
        raise FileExistsError(f"preserve previous run; choose another name: {receipt}")
    BUNDLE.mkdir(parents=True, exist_ok=True)
    metadata = {
        "argv": argv,
        "cwd": str(ROOT),
        "head_sha": git("rev-parse", "HEAD"),
        "tree_sha": git("rev-parse", "HEAD^{tree}"),
        "status_before": git("status", "--porcelain=v1", "--untracked-files=normal"),
        "started_utc": datetime.now(UTC).isoformat(),
        "timeout_seconds": timeout,
        "input_sha256": inputs(argv),
    }
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    with (BUNDLE / f"{name}-stdout.txt").open("wb") as out:
        with (BUNDLE / f"{name}-stderr.txt").open("wb") as err:
            try:
                result = subprocess.run(
                    argv,
                    cwd=ROOT,
                    env=env,
                    stdout=out,
                    stderr=err,
                    timeout=timeout,
                    check=False,
                )
                code = result.returncode
                metadata["timed_out"] = False
            except subprocess.TimeoutExpired:
                code = 124
                metadata["timed_out"] = True
    metadata.update(exit_code=code, finished_utc=datetime.now(UTC).isoformat())
    receipt.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (BUNDLE / f"{name}-exit-code.txt").write_text(f"{code}\n", encoding="ascii")
    print(f"{name}: exit={code}", flush=True)
    return code


def hashes() -> None:
    """Hash bundle bytes, excluding this manifest's unavoidable self-reference."""
    rows = {
        p.relative_to(BUNDLE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(BUNDLE.rglob("*"))
        if p.is_file() and p.name != "artifact-sha256.json"
    }
    (BUNDLE / "artifact-sha256.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8"
    )


def qualify() -> int:
    """Replay owning suites on this exact HEAD, with external output in CI."""
    historical = ROOT / "reports/audit-runs/12553-runtime-acceptance"
    codes = []
    for previous in (
        "files-config-final",
        "tasks-executors",
        "storage-export-final",
        "http-telemetry",
        "health-composition",
        "review-controls",
    ):
        name = "qualified-" + previous
        recorded = json.loads(read_evidence(f"{previous}-command.json", historical))
        argv = [sys.executable, *recorded["argv"][1:]]
        argv = [
            "--junitxml=" + str(BUNDLE / f"{name}-junit.xml")
            if arg.startswith("--junitxml=")
            else arg
            for arg in argv
        ]
        os.environ["BIOETL_12553_EVENTS"] = str(BUNDLE / f"{name}-events.json.gz")
        codes.append(capture(name, argv))
    (BUNDLE / "checked-head-sha.txt").write_text(
        git("rev-parse", "HEAD") + "\n", encoding="ascii"
    )
    (BUNDLE / "checked-tree-sha.txt").write_text(
        git("rev-parse", "HEAD^{tree}") + "\n", encoding="ascii"
    )
    codes.append(
        capture(
            "runtime-versions",
            [
                sys.executable,
                "-c",
                "import importlib.metadata as m,json,platform;print(json.dumps({'python':platform.python_version(),'packages':sorted((d.metadata['Name'],d.version) for d in m.distributions())},indent=2))",
            ],
        )
    )
    return int(any(codes))


def main() -> int:
    """Run one named command or refresh the evidence checksum manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.name == "hashes":
        hashes()
        return 0
    if args.name == "qualify":
        return qualify()
    if args.name == "pack":
        pack()
        return 0
    if args.name == "verify":
        verify(BUNDLE)
        return 0
    argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
    if not argv:
        parser.error("command required after --")
    return capture(args.name, argv, args.timeout)


if __name__ == "__main__":
    sys.exit(main())

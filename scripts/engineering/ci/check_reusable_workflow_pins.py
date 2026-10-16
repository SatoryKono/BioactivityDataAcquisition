"""Repo-side pin consistency for `.github/workflows/pr-required.yml`.

This checker is not an independent trust boundary. fast-governance checks out
the PR head, so the same PR can replace the coordinator, this script, and
`configs/quality/reusable_action_pins.yaml` together. Local `action.yml`
existence does not prove the action contents are trusted. #12046 stays open
until workflows are forced from the default branch by an org ruleset.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

REGISTRY_PATH = "configs/quality/reusable_action_pins.yaml"
WORKFLOW_PATHS: tuple[str, ...] = (".github/workflows/pr-required.yml",)
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_LOCAL_ACTION_PREFIX = (".github", "actions")


def _emit(errors: list[str]) -> None:
    for error in errors:
        print(error, file=sys.stderr)


def _read_yaml(path: Path, errors: list[str]) -> object | None:
    if not path.is_file():
        errors.append(f"missing path: {path}")
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"unreadable path: {path}: {exc}")
        return None
    if not text.strip():
        errors.append(f"empty YAML: {path}")
        return None
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        errors.append(f"malformed YAML: {path}: {exc}")
        return None


def _pin_entry(entry: object, index: int, errors: list[str]) -> tuple[str, str] | None:
    if not isinstance(entry, dict):
        errors.append(f"malformed registry pin {index}: entry must be a mapping")
        return None
    path = entry.get("path")
    sha = entry.get("sha")
    if not isinstance(path, str) or not path or path != path.strip():
        errors.append(
            f"malformed registry pin {index}: path must be a non-empty string"
        )
        return None
    if not isinstance(sha, str) or _SHA_RE.fullmatch(sha) is None:
        errors.append(
            f"malformed registry pin {index}: sha must be a 40-hex commit SHA"
        )
        return None
    return path, sha


def _pins_from_document(document: object, errors: list[str]) -> dict[str, str] | None:
    if not isinstance(document, dict):
        errors.append("malformed registry: root must be a mapping")
        return None
    pins = document.get("pins")
    if not isinstance(pins, list):
        errors.append("malformed registry: pins must be a list")
        return None
    resolved: dict[str, str] = {}
    for index, entry in enumerate(pins):
        parsed = _pin_entry(entry, index, errors)
        if parsed is None:
            continue
        path, sha = parsed
        previous = resolved.get(path)
        if previous is None:
            resolved[path] = sha
            continue
        if previous != sha:
            errors.append(f"ambiguous duplicate registry entry: {path}")
            continue
        errors.append(f"duplicate registry entry: {path}")
    return resolved


def _load_registry(path: Path, errors: list[str]) -> dict[str, str] | None:
    before = len(errors)
    document = _read_yaml(path, errors)
    if document is None:
        return None
    resolved = _pins_from_document(document, errors)
    if len(errors) != before or resolved is None:
        return None
    return resolved


def _split_pinned_ref(uses: str) -> tuple[str, str] | None:
    if uses.count("@") != 1:
        return None
    path, sha = uses.split("@", 1)
    if not path or not sha:
        return None
    return path, sha


def _check_registry_pin(
    uses: str,
    registry: dict[str, str],
    errors: list[str],
    kind: str,
) -> None:
    parsed = _split_pinned_ref(uses)
    if parsed is None:
        errors.append(f"{kind} {uses} is not pinned with a single @ref")
        return
    path, sha = parsed
    if _SHA_RE.fullmatch(sha) is None:
        errors.append(f"{kind} {uses} is not pinned to a full 40-hex commit SHA")
        return
    expected = registry.get(path)
    if expected is None:
        errors.append(f"unknown {kind} path {path}")
        return
    if expected != sha:
        errors.append(f"{kind} {path} SHA {sha} != registry {expected}")


def _check_local_action(uses: str, repo_root: Path, errors: list[str]) -> None:
    if not uses.startswith("./"):
        errors.append(f"local action must be a ./ path: {uses}")
        return
    if "@" in uses:
        errors.append(f"local action must not carry a ref: {uses}")
        return
    relative = Path(uses[2:])
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"local action escapes the repository: {uses}")
        return
    if relative.parts[:2] != _LOCAL_ACTION_PREFIX or len(relative.parts) < 3:
        errors.append(f"local action must live under ./.github/actions/: {uses}")
        return
    root = repo_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root / ".github" / "actions")
    except ValueError:
        errors.append(f"local action escapes .github/actions: {uses}")
        return
    manifest_names = ("action.yml", "action.yaml")
    if any((candidate / name).is_file() for name in manifest_names):
        return
    errors.append(f"local action {uses} has no action.yml or action.yaml")


def _check_docker(uses: str, errors: list[str]) -> None:
    errors.append(
        f"docker reference {uses} is not an external action or reusable workflow pin"
    )


def _check_step_uses(
    uses: object,
    where: str,
    registry: dict[str, str],
    repo_root: Path,
    errors: list[str],
) -> None:
    if not isinstance(uses, str) or not uses or uses != uses.strip():
        errors.append(f"{where} uses is not a non-empty string")
        return
    if uses.startswith("docker://"):
        _check_docker(uses, errors)
        return
    if uses.startswith(("./", "../")):
        _check_local_action(uses, repo_root, errors)
        return
    if "/.github/workflows/" in uses:
        errors.append(f"{where} step uses a reusable workflow; put uses on the job")
        return
    _check_registry_pin(uses, registry, errors, "external action")


def _check_steps(
    steps: object,
    job_name: str,
    registry: dict[str, str],
    repo_root: Path,
    errors: list[str],
) -> None:
    if not isinstance(steps, list):
        errors.append(f"job {job_name} steps must be a list")
        return
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"job {job_name} step {index} must be a mapping")
            continue
        if "uses" not in step:
            continue
        _check_step_uses(
            step.get("uses"),
            f"job {job_name} step {index}",
            registry,
            repo_root,
            errors,
        )


def _check_reusable_uses(
    uses: object,
    job_name: str,
    registry: dict[str, str],
    errors: list[str],
) -> None:
    if not isinstance(uses, str) or not uses or uses != uses.strip():
        errors.append(f"job {job_name} uses is not a non-empty string")
        return
    if uses.startswith("docker://"):
        _check_docker(uses, errors)
        return
    if uses.startswith(("./", "../")):
        errors.append(
            f"job {job_name} reusable workflow {uses} must be owner/repo/.github/workflows/"
            "file.yml@<40-hex SHA>"
        )
        return
    if "/.github/workflows/" not in uses:
        errors.append(f"job {job_name} uses is not a reusable workflow path")
        return
    _check_registry_pin(uses, registry, errors, "reusable workflow")


def _check_job(
    job_name: str,
    job: object,
    registry: dict[str, str],
    repo_root: Path,
    errors: list[str],
) -> None:
    if not isinstance(job, dict):
        errors.append(f"job {job_name} must be a mapping")
        return
    has_uses = "uses" in job
    has_steps = "steps" in job
    if has_uses and has_steps:
        errors.append(f"job {job_name} mixes reusable uses with steps")
        return
    if has_uses:
        _check_reusable_uses(job.get("uses"), job_name, registry, errors)
        return
    if not has_steps:
        errors.append(f"job {job_name} has neither uses nor steps")
        return
    _check_steps(job.get("steps"), job_name, registry, repo_root, errors)


def _check_workflow(
    path: Path,
    registry: dict[str, str],
    repo_root: Path,
    errors: list[str],
) -> None:
    document = _read_yaml(path, errors)
    if not isinstance(document, dict):
        if document is not None:
            errors.append(f"malformed workflow: {path} root must be a mapping")
        return
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        errors.append(f"malformed workflow: {path} jobs must be a mapping")
        return
    for job_name, job in jobs.items():
        _check_job(str(job_name), job, registry, repo_root, errors)


def check_pins(
    registry_path: str | Path,
    workflow_paths: Sequence[str | Path],
    *,
    repo_root: Path | None = None,
) -> bool:
    """Return whether every inspected uses reference matches the pin contract."""
    errors: list[str] = []
    root = Path.cwd() if repo_root is None else repo_root
    if not workflow_paths:
        errors.append("no workflow paths to check")
    registry = _load_registry(Path(registry_path), errors)
    if registry is not None:
        for workflow_path in workflow_paths:
            _check_workflow(Path(workflow_path), registry, root, errors)
    _emit(errors)
    return not errors


def main(argv: list[str] | None = None) -> int:
    """Check pins. `--check` is the CI flag; omitting it still checks."""
    parser = argparse.ArgumentParser(
        description=(
            "Fail closed unless pr-required.yml pins match the trusted registry. "
            "This is repo-side consistency, not an independent trust boundary."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run the pin check. The check also runs when this flag is omitted.",
    )
    args = parser.parse_args(argv)
    mode = "--check" if args.check else "default"
    if not check_pins(REGISTRY_PATH, WORKFLOW_PATHS):
        return 1
    print(f"Pin check passed ({mode}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

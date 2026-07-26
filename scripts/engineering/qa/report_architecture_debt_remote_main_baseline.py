#!/usr/bin/env python3
"""Generate clean remote-main architecture debt baseline artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "architecture-debt-remote-main-baseline.json"
)
DEFAULT_MD_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "architecture-debt-remote-main-baseline.md"
)

REQUIRED_BASELINE_ARTIFACTS = (
    "reports/quality/architecture-quality-scorecard.json",
    "reports/quality/module-coverage-inventory.json",
    "reports/quality/compatibility-importer-census.json",
    "reports/quality/dead-code-inventory.json",
    "reports/quality/contract-registry-diagnostics.json",
)
OPTIONAL_BASELINE_ARTIFACTS = (
    "reports/observability/runtime_cardinality_inventory.json",
)
_BASELINE_ARTIFACTS = REQUIRED_BASELINE_ARTIFACTS + OPTIONAL_BASELINE_ARTIFACTS
_GENERATOR_COMMANDS = (
    "python -m scripts.engineering.qa report-dep-map --check",
    "python -m scripts.engineering.qa report-module-coverage --check",
    "python -m scripts.engineering.qa report-compatibility-importer-census --check",
    "python -m scripts.engineering.qa report-dead-code-inventory --check",
    "python -m scripts.engineering.qa report-observability-metric-inventory "
    "--check --write-evidence reports/observability/runtime_cardinality_inventory.json",
    "python -m scripts.engineering.qa report-adr-enforcement-matrix --check",
    "python -m scripts.engineering.qa report-debt-governance-gates --check",
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(PROJECT_ROOT))
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--update", action="store_true")
    return parser.parse_args(argv)


def _run_git(repo_root: Path, args: list[str], *, check: bool = True) -> str:
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    result = subprocess.run(
        ensure_safe_cli_argv(["git", *[str(a) for a in args]]),
        cwd=repo_root,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _remote_main_sha(repo_root: Path, *, remote: str, branch: str) -> str:
    output = _run_git(repo_root, ["ls-remote", remote, f"refs/heads/{branch}"])
    if not output:
        raise RuntimeError(f"Could not resolve {remote}/{branch}")
    return output.split()[0]


def _git_blob(repo_root: Path, revision: str, path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _json_blob_summary(blob: bytes | None) -> dict[str, object]:
    if blob is None:
        return {"available": False}
    try:
        payload = json.loads(blob.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {"available": True}
    if not isinstance(payload, dict):
        return {"available": True}

    summary: dict[str, object] = {"available": True}
    for key in (
        "schema_version",
        "integral_score",
        "weights_sum",
        "coverage_xml_sha256",
        "source_tree_sha256",
        "snapshot_date",
        "valid",
        "blocking_issue_count",
    ):
        if key in payload:
            summary[key] = payload[key]
    nested_summary = payload.get("summary")
    if isinstance(nested_summary, dict):
        for key in (
            "source_module_count",
            "unmeasured_module_count",
            "repo_wide_untriaged_zero_import_candidate_count",
            "retained_entrypoint_count",
        ):
            if key in nested_summary:
                summary[key] = nested_summary[key]
    return summary


def _baseline_semantic_signature(payload: dict[str, object]) -> dict[str, object]:
    """Return the stable evidence identity, excluding commit metadata churn."""
    artifacts = payload.get("artifacts")
    assert isinstance(artifacts, list)
    artifact_rows: list[dict[str, object]] = []
    for row in artifacts:
        assert isinstance(row, dict)
        artifact_rows.append(
            {
                "path": row.get("path"),
                "blob_sha256": row.get("blob_sha256"),
                "required": row.get("required"),
                "required_on_remote": row.get("required_on_remote"),
                "introduced_after_remote_main": row.get("introduced_after_remote_main"),
                "summary": row.get("summary"),
            }
        )

    return {
        "schema_version": payload.get("schema_version"),
        "generated_by": payload.get("generated_by"),
        "evidence_source": payload.get("evidence_source"),
        "remote": payload.get("remote"),
        "branch": payload.get("branch"),
        "remote_main_ref": payload.get("remote_main_ref"),
        "generator_commands": payload.get("generator_commands"),
        "artifacts": artifact_rows,
    }


def baseline_artifact_fingerprint(payload: dict[str, object]) -> str:
    """Fingerprint the tracked baseline evidence without volatile commit SHAs."""
    signature = _baseline_semantic_signature(payload)
    encoded = json.dumps(signature, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def payloads_semantically_equivalent(
    left: dict[str, object], right: dict[str, object]
) -> bool:
    """Return True when baseline evidence is unchanged apart from commit metadata."""
    return _baseline_semantic_signature(left) == _baseline_semantic_signature(right)


def build_payload(
    *,
    repo_root: Path = PROJECT_ROOT,
    remote: str = "origin",
    branch: str = "main",
) -> dict[str, object]:
    """Build clean remote-main debt baseline from Git tree blobs."""
    repo_root = repo_root.resolve()
    remote_sha = _remote_main_sha(repo_root, remote=remote, branch=branch)
    local_origin_sha = _run_git(
        repo_root,
        ["rev-parse", "--verify", f"{remote}/{branch}"],
        check=False,
    )
    artifact_rows: list[dict[str, object]] = []
    for path in _BASELINE_ARTIFACTS:
        blob = _git_blob(repo_root, remote_sha, path)
        local_head_blob = _git_blob(repo_root, "HEAD", path)
        required = path in REQUIRED_BASELINE_ARTIFACTS
        introduced_after_remote_main = blob is None and local_head_blob is not None
        artifact_rows.append(
            {
                "path": path,
                "source_revision": remote_sha,
                "blob_sha256": (
                    hashlib.sha256(blob).hexdigest() if blob is not None else None
                ),
                "required": required,
                "required_on_remote": required and not introduced_after_remote_main,
                "introduced_after_remote_main": introduced_after_remote_main,
                "summary": _json_blob_summary(blob),
            }
        )

    payload: dict[str, object] = {
        "schema_version": 1,
        "generated_by": "scripts.engineering.qa.report_architecture_debt_remote_main_baseline",
        "evidence_source": "remote_main_git_tree",
        "remote": remote,
        "branch": branch,
        "remote_main_ref": f"refs/heads/{branch}",
        "remote_main_sha": remote_sha,
        "local_tracking_ref": f"{remote}/{branch}",
        "local_tracking_ref_sha": local_origin_sha or None,
        "local_tracking_ref_matches_remote": local_origin_sha == remote_sha,
        "dirty_closeout_guard": {
            "policy": "closeout evidence must come from remote-main Git tree blobs, not unstaged local files",
            "command": "git status --porcelain --untracked-files=no",
            "expected_output": "",
        },
        "generator_commands": list(_GENERATOR_COMMANDS),
        "artifacts": artifact_rows,
    }
    payload["baseline_artifact_fingerprint"] = baseline_artifact_fingerprint(payload)
    return payload


def render_markdown(payload: dict[str, object]) -> str:
    artifacts = payload["artifacts"]
    assert isinstance(artifacts, list)
    lines = [
        "# Architecture Debt Remote-Main Baseline",
        "",
        "> Generated by `python -m scripts.engineering.qa report-architecture-debt-remote-main-baseline`.",
        "",
        f"- evidence_source: `{payload['evidence_source']}`",
        f"- remote_main_ref: `{payload['remote_main_ref']}`",
        "- baseline_artifact_fingerprint: "
        f"`{payload.get('baseline_artifact_fingerprint') or baseline_artifact_fingerprint(payload)}`",
        f"- local_tracking_ref_matches_remote: `{payload['local_tracking_ref_matches_remote']}`",
        "",
        "| artifact | blob_sha256 | available | required_on_remote | introduced_after_remote_main |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in artifacts:
        assert isinstance(row, dict)
        summary = row["summary"]
        assert isinstance(summary, dict)
        lines.append(
            "| `{path}` | `{blob}` | `{available}` | `{required_on_remote}` | `{introduced}` |".format(
                path=row["path"],
                blob=row["blob_sha256"] or "",
                available=summary.get("available"),
                required_on_remote=row.get("required_on_remote", row.get("required")),
                introduced=row.get("introduced_after_remote_main", False),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _write_artifacts(
    payload: dict[str, object],
    *,
    json_out: Path,
    md_out: Path,
    root: Path | None = None,
) -> None:
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        json_out = resolve_output_path(json_out, root=root)
        md_out = resolve_output_path(md_out, root=root)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(render_markdown(payload), encoding="utf-8")


def _check_artifacts(
    payload: dict[str, object],
    *,
    json_out: Path,
    md_out: Path,
    root: Path | None = None,
) -> list[str]:
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        json_out = resolve_output_path(json_out, root=root)
        md_out = resolve_output_path(md_out, root=root)
    errors: list[str] = []
    expected_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(payload)
    json_matches = False
    if json_out.exists():
        actual_json = json_out.read_text(encoding="utf-8")
        json_matches = actual_json == expected_json
        if not json_matches:
            try:
                committed_payload = json.loads(actual_json)
            except json.JSONDecodeError:
                committed_payload = None
            if isinstance(committed_payload, dict):
                json_matches = payloads_semantically_equivalent(
                    committed_payload, payload
                )
    if not json_matches:
        errors.append(f"Remote-main debt baseline JSON artifact is stale: {json_out}")
    if not md_out.exists() or md_out.read_text(encoding="utf-8") != expected_md:
        errors.append(f"Remote-main debt baseline Markdown artifact is stale: {md_out}")
    if payload["evidence_source"] != "remote_main_git_tree":
        errors.append("Remote-main debt baseline evidence_source is not clean")
    if not payload["local_tracking_ref_matches_remote"]:
        errors.append(
            "Local tracking ref does not match remote main; fetch before closeout"
        )
    for row in payload["artifacts"]:
        assert isinstance(row, dict)
        summary = row["summary"]
        assert isinstance(summary, dict)
        required_on_remote = row.get("required_on_remote", row.get("required"))
        if required_on_remote and not summary.get("available"):
            errors.append(f"Remote-main baseline artifact unavailable: {row['path']}")
    return errors


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    payload = build_payload(repo_root=repo_root, remote=args.remote, branch=args.branch)
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)

    if args.check:
        errors = _check_artifacts(
            payload, json_out=json_out, md_out=md_out, root=repo_root
        )
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        return 0

    if args.update:
        _write_artifacts(payload, json_out=json_out, md_out=md_out, root=repo_root)
        return 0

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

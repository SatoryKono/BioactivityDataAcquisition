#!/usr/bin/env python3
"""Generate accepted-ADR enforcement coverage matrix artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.generate_adr_registry import ADRMetadata, ADRRegistryGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "adr-enforcement-matrix.json"
)
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "adr-enforcement-matrix.md"

_TEXT_SUFFIXES = frozenset(
    {".cfg", ".ini", ".json", ".md", ".py", ".toml", ".yaml", ".yml"}
)
_SCAN_PREFIXES = (
    ".github/workflows/",
    "configs/",
    "docs/00-project/",
    "docs/01-requirements/",
    "docs/03-guides/",
    "docs/04-reference/",
    "docs/05-operations/",
    "grafana/",
    "scripts/",
    "src/bioetl/",
    "tests/",
)
_EXCLUDED_PREFIXES = (
    "docs/02-architecture/adr-registry/",
    "docs/02-architecture/decisions/",
    "reports/",
    "tests/fixtures/",
)
_ENFORCEMENT_PREFIXES = (
    ".github/workflows/",
    "configs/quality/",
    "scripts/",
    "tests/",
)
_IMPLEMENTATION_PREFIXES = (
    "configs/",
    "docs/00-project/",
    "docs/01-requirements/",
    "docs/03-guides/",
    "docs/04-reference/",
    "docs/05-operations/",
    "grafana/",
    "scripts/",
    "src/bioetl/",
    "tests/",
)
_MANUAL_EXCEPTION_PREFIX = "manual-exception:"
_ADR_REFERENCE_RE = re.compile(r"\bADR-\d{3}\b", flags=re.IGNORECASE)
_ADR_REFERENCE_BYTES_RE = re.compile(rb"\bADR-\d{3}\b", flags=re.IGNORECASE)
_GIT_ADR_REFERENCE_PATTERN = r"ADR-[0-9]{3}"


@dataclass(frozen=True)
class AdrCoverage:
    """Coverage row for one accepted ADR."""

    adr_id: str
    title: str
    decision_path: str
    category: str
    owner: str
    decision_date: str | None
    implementation_owner_paths: tuple[str, ...]
    enforcement_owner_paths: tuple[str, ...]
    manual_exception: dict[str, str] | None

    @property
    def has_implementation_owner(self) -> bool:
        return bool(self.implementation_owner_paths)

    @property
    def has_enforcement_owner(self) -> bool:
        return bool(self.enforcement_owner_paths)

    @property
    def has_manual_exception(self) -> bool:
        return self.manual_exception is not None

    @property
    def status(self) -> str:
        if self.has_enforcement_owner:
            return "enforced"
        if self.has_manual_exception:
            return "manual_exception"
        return "gap"

    @property
    def gap_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.has_implementation_owner:
            reasons.append("missing_implementation_owner")
        if not self.has_enforcement_owner and not self.has_manual_exception:
            reasons.append("missing_enforcement_owner")
        return tuple(reasons)

    def as_dict(self) -> dict[str, object]:
        return {
            "adr_id": self.adr_id,
            "title": self.title,
            "status": self.status,
            "decision_path": self.decision_path,
            "category": self.category,
            "owner": self.owner,
            "decision_date": self.decision_date,
            "implementation_owner_paths": list(self.implementation_owner_paths),
            "enforcement_owner_paths": list(self.enforcement_owner_paths),
            "manual_exception": self.manual_exception,
            "gap_reasons": list(self.gap_reasons),
        }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(PROJECT_ROOT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed ADR enforcement matrix artifacts differ or have blocking gaps.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write ADR enforcement matrix artifacts.",
    )
    return parser.parse_args(argv)


def _should_scan_path(rel_path: str) -> bool:
    """Return whether a repo-relative text path belongs to the ADR reference scan."""
    return (
        rel_path.startswith(_SCAN_PREFIXES)
        and not rel_path.startswith(_EXCLUDED_PREFIXES)
        and Path(rel_path).suffix in _TEXT_SUFFIXES
    )


def _git_grep_reference_lines(repo_root: Path) -> list[tuple[str, str]] | None:
    """Return ADR reference lines from git-grep, or None when git-grep is unavailable."""
    try:
        from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

        result = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
            ensure_safe_cli_argv(
                [
                    "git",
                    "grep",
                    "--untracked",
                    "-I",
                    "-E",
                    "-i",
                    "-n",
                    "-e",
                    _GIT_ADR_REFERENCE_PATTERN,
                    "--",
                    *_SCAN_PREFIXES,
                    ":(exclude)tests/fixtures/",
                ]
            ),
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None
    if result.returncode not in (0, 1):
        return None
    lines: list[tuple[str, str]] = []
    for raw_line in result.stdout.splitlines():
        try:
            path, _line_number, text = raw_line.split(":", 2)
        except ValueError:
            continue
        lines.append((path, text))
    return lines


def _ripgrep_reference_lines(repo_root: Path) -> list[tuple[str, str]] | None:
    """Return ADR reference lines from ripgrep, or None when it is unavailable."""
    try:
        from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

        result = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
            ensure_safe_cli_argv(
                [
                    "rg",
                    "--hidden",
                    "--line-number",
                    "--ignore-case",
                    "--with-filename",
                    "--no-heading",
                    "--color",
                    "never",
                    "--glob",
                    "!tests/fixtures/**",
                    "-e",
                    r"ADR-\d{3}",
                    "--",
                    *_SCAN_PREFIXES,
                ]
            ),
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None
    if result.returncode not in (0, 1):
        return None

    lines: list[tuple[str, str]] = []
    for raw_line in result.stdout.splitlines():
        try:
            path, _line_number, text = raw_line.split(":", 2)
        except ValueError:
            continue
        lines.append((path, text))
    return lines


def _python_reference_lines(repo_root: Path) -> list[tuple[str, str]]:
    """Fallback ADR reference scan for environments where Git commands fail."""
    scan_paths = _python_scan_paths(repo_root)
    max_workers = min(32, (os.cpu_count() or 1) + 4)
    lines: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for file_lines in executor.map(
            lambda rel_path: _read_python_reference_lines(
                repo_root=repo_root,
                rel_path=rel_path,
            ),
            scan_paths,
        ):
            lines.extend(file_lines)
    return lines


def _read_python_reference_lines(
    *, repo_root: Path, rel_path: str
) -> tuple[tuple[str, str], ...]:
    """Read only ADR-bearing lines from one text candidate."""
    reference_lines: list[tuple[str, str]] = []
    try:
        with (repo_root / rel_path).open("rb") as handle:
            for raw_line in handle:
                if not _ADR_REFERENCE_BYTES_RE.search(raw_line):
                    continue
                line = raw_line.decode("utf-8", errors="ignore").rstrip("\r\n")
                reference_lines.append((rel_path, line))
    except OSError:
        return ()
    return tuple(reference_lines)


def _python_scan_paths(repo_root: Path) -> tuple[str, ...]:
    """Return repo-relative scan paths without relying on Git discovery."""
    discovered: set[str] = set()
    for prefix in _SCAN_PREFIXES:
        prefix_path = repo_root / prefix
        if not prefix_path.exists():
            continue
        candidates = prefix_path.rglob("*") if prefix_path.is_dir() else (prefix_path,)
        for path in candidates:
            if not path.is_file():
                continue
            try:
                rel_path = path.relative_to(repo_root).as_posix()
            except ValueError:
                continue
            if _should_scan_path(rel_path):
                discovered.add(rel_path)
    return tuple(sorted(discovered))


def _reference_index(
    repo_root: Path,
) -> tuple[dict[str, set[str]], dict[str, dict[str, str]]]:
    reference_lines = _git_grep_reference_lines(repo_root)
    if reference_lines is None:
        reference_lines = _ripgrep_reference_lines(repo_root)
    if reference_lines is None:
        reference_lines = _python_reference_lines(repo_root)

    paths_by_adr: dict[str, set[str]] = {}
    manual_exceptions: dict[str, dict[str, str]] = {}
    for path, text in reference_lines:
        if not _should_scan_path(path):
            continue
        for raw_adr_id in _ADR_REFERENCE_RE.findall(text):
            adr_id = raw_adr_id.upper()
            paths_by_adr.setdefault(adr_id, set()).add(path)
            manual_exception = _manual_exception_from_text(
                adr_id=adr_id,
                rel_path=path,
                text=text,
            )
            if manual_exception is not None:
                manual_exceptions.setdefault(adr_id, manual_exception)
    return paths_by_adr, manual_exceptions


def _accepted_adrs(repo_root: Path) -> tuple[ADRMetadata, ...]:
    generator = ADRRegistryGenerator()
    generator.adr_dir = repo_root / "docs" / "02-architecture" / "decisions"
    generator.output_dir = repo_root / "docs" / "02-architecture" / "adr-registry"
    generator.navigator_registry_file = (
        repo_root / "docs" / "02-architecture" / "adr-registry.md"
    )
    generator.adr_index_file = generator.adr_dir / "README.md"
    generator.adr_index_metadata = generator._load_adr_index_metadata()

    adrs: list[ADRMetadata] = []
    for adr_path in generator.find_adr_files():
        metadata = generator.extract_adr_metadata(adr_path)
        if metadata is not None and metadata.status == "accepted":
            adrs.append(metadata)
    return tuple(sorted(adrs, key=lambda adr: int(adr.adr_number)))


def _manual_exception_from_text(
    *,
    adr_id: str,
    rel_path: str,
    text: str,
) -> dict[str, str] | None:
    marker = f"{_MANUAL_EXCEPTION_PREFIX}{adr_id}"
    for line in text.splitlines():
        if marker not in line:
            continue
        reason = line.split(marker, 1)[1].strip(" :-")
        return {
            "source": rel_path,
            "marker": marker,
            "reason": reason or "reviewed manual enforcement exception",
        }
    return None


def _collect_references(
    reference_paths: set[str],
    manual_exception: dict[str, str] | None,
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, str] | None]:
    implementation_paths: list[str] = []
    enforcement_paths: list[str] = []

    for rel_path in reference_paths:
        if rel_path.startswith(_IMPLEMENTATION_PREFIXES):
            implementation_paths.append(rel_path)
        if rel_path.startswith(_ENFORCEMENT_PREFIXES):
            enforcement_paths.append(rel_path)

    return (
        tuple(sorted(set(implementation_paths))),
        tuple(sorted(set(enforcement_paths))),
        manual_exception,
    )


def build_payload(*, repo_root: Path = PROJECT_ROOT) -> dict[str, object]:
    """Build the deterministic ADR enforcement matrix payload."""
    repo_root = repo_root.resolve()
    reference_paths_by_adr, manual_exceptions = _reference_index(repo_root)
    rows: list[AdrCoverage] = []

    for adr in _accepted_adrs(repo_root):
        adr_id = f"ADR-{adr.adr_number}"
        implementation_paths, enforcement_paths, manual_exception = _collect_references(
            reference_paths_by_adr.get(adr_id, set()),
            manual_exceptions.get(adr_id),
        )
        rows.append(
            AdrCoverage(
                adr_id=adr_id,
                title=adr.title,
                decision_path=("docs/02-architecture/decisions/" + adr.file_path),
                category=adr.category,
                owner=adr.owner,
                decision_date=adr.decision_date,
                implementation_owner_paths=implementation_paths,
                enforcement_owner_paths=enforcement_paths,
                manual_exception=manual_exception,
            )
        )

    gap_rows = [row for row in rows if row.status == "gap"]
    manual_exception_rows = [row for row in rows if row.status == "manual_exception"]
    enforced_rows = [row for row in rows if row.status == "enforced"]

    return {
        "schema_version": 1,
        "generated_by": "scripts.engineering.qa.report_adr_enforcement_matrix",
        "source": {
            "adr_decisions_dir": "docs/02-architecture/decisions",
            "tracked_file_discovery": "git grep --untracked with python fallback",
            "manual_exception_marker_prefix": _MANUAL_EXCEPTION_PREFIX,
        },
        "summary": {
            "accepted_adr_count": len(rows),
            "enforced_adr_count": len(enforced_rows),
            "manual_exception_count": len(manual_exception_rows),
            "blocking_gap_count": len(gap_rows),
            "missing_implementation_owner_count": sum(
                1 for row in rows if not row.has_implementation_owner
            ),
            "missing_enforcement_owner_count": sum(
                1 for row in rows if not row.has_enforcement_owner
            ),
        },
        "rows": [row.as_dict() for row in rows],
    }


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    assert isinstance(summary, dict)
    rows = payload["rows"]
    assert isinstance(rows, list)
    lines = [
        "# ADR Enforcement Matrix",
        "",
        "> Generated by `python -m scripts.engineering.qa report-adr-enforcement-matrix`.",
        "",
        f"- accepted_adr_count: {summary['accepted_adr_count']}",
        f"- enforced_adr_count: {summary['enforced_adr_count']}",
        f"- manual_exception_count: {summary['manual_exception_count']}",
        f"- blocking_gap_count: {summary['blocking_gap_count']}",
        f"- missing_implementation_owner_count: {summary['missing_implementation_owner_count']}",
        f"- missing_enforcement_owner_count: {summary['missing_enforcement_owner_count']}",
        "",
        "| ADR | status | implementation owners | enforcement owners | gaps |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        assert isinstance(row, dict)
        gaps = ", ".join(str(item) for item in row["gap_reasons"]) or "-"
        lines.append(
            "| `{adr_id}` | `{status}` | {impl_count} | {enf_count} | {gaps} |".format(
                adr_id=row["adr_id"],
                status=row["status"],
                impl_count=len(row["implementation_owner_paths"]),
                enf_count=len(row["enforcement_owner_paths"]),
                gaps=gaps,
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
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    base = root if root is not None else REPO_ROOT
    json_out = resolve_output_path(json_out, root=base)
    md_out = resolve_output_path(md_out, root=base)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(  # NOSONAR - path confined by resolve_output_path
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(
        render_markdown(payload), encoding="utf-8"
    )  # NOSONAR - path confined by resolve_output_path


def _check_artifacts(
    payload: dict[str, object],
    *,
    json_out: Path,
    md_out: Path,
    root: Path | None = None,
) -> list[str]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    base = root if root is not None else REPO_ROOT
    json_out = resolve_output_path(json_out, root=base)
    md_out = resolve_output_path(md_out, root=base)
    errors: list[str] = []
    expected_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(payload)
    if (
        not json_out.exists()
        or json_out.read_text(encoding="utf-8")  # NOSONAR - path confined
        != expected_json
    ):
        errors.append(f"ADR enforcement JSON artifact is stale: {json_out}")
    if (
        not md_out.exists()
        or md_out.read_text(encoding="utf-8")  # NOSONAR - path confined
        != expected_md
    ):
        errors.append(f"ADR enforcement Markdown artifact is stale: {md_out}")
    summary = payload["summary"]
    assert isinstance(summary, dict)
    if int(summary["blocking_gap_count"]) > 0:
        errors.append(
            "Accepted ADR enforcement gaps remain: "
            f"{summary['blocking_gap_count']} ADR(s) lack enforcement owner or manual exception"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    payload = build_payload(repo_root=repo_root)
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

#!/usr/bin/env python3
"""Generate accepted-ADR enforcement coverage matrix artifacts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.generate_adr_registry import ADRMetadata, ADRRegistryGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "adr-enforcement-matrix.json"
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "adr-enforcement-matrix.md"

_TEXT_SUFFIXES = frozenset({".cfg", ".ini", ".json", ".md", ".py", ".toml", ".yaml", ".yml"})
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


def _repo_relative(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _tracked_files(repo_root: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    files = []
    for raw_path in result.stdout.splitlines():
        path = raw_path.strip()
        if not path:
            continue
        if not path.startswith(_SCAN_PREFIXES):
            continue
        if path.startswith(_EXCLUDED_PREFIXES):
            continue
        if Path(path).suffix not in _TEXT_SUFFIXES:
            continue
        files.append(path)
    return tuple(sorted(files))


def _accepted_adrs(repo_root: Path) -> tuple[ADRMetadata, ...]:
    generator = ADRRegistryGenerator()
    generator.adr_dir = repo_root / "docs" / "02-architecture" / "decisions"
    generator.output_dir = repo_root / "docs" / "02-architecture" / "adr-registry"
    generator.navigator_registry_file = repo_root / "docs" / "02-architecture" / "adr-registry.md"
    generator.adr_index_file = generator.adr_dir / "README.md"
    generator.adr_index_metadata = generator._load_adr_index_metadata()

    adrs: list[ADRMetadata] = []
    for adr_path in generator.find_adr_files():
        metadata = generator.extract_adr_metadata(adr_path)
        if metadata is not None and metadata.status == "accepted":
            adrs.append(metadata)
    return tuple(sorted(adrs, key=lambda adr: int(adr.adr_number)))


def _read_text(repo_root: Path, rel_path: str) -> str:
    return (repo_root / rel_path).read_text(encoding="utf-8", errors="ignore")


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
    repo_root: Path,
    tracked_files: tuple[str, ...],
    adr_id: str,
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, str] | None]:
    pattern = re.compile(rf"\b{re.escape(adr_id)}\b", flags=re.IGNORECASE)
    implementation_paths: list[str] = []
    enforcement_paths: list[str] = []
    manual_exception: dict[str, str] | None = None

    for rel_path in tracked_files:
        text = _read_text(repo_root, rel_path)
        if not pattern.search(text):
            continue
        if manual_exception is None:
            manual_exception = _manual_exception_from_text(
                adr_id=adr_id,
                rel_path=rel_path,
                text=text,
            )
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
    tracked_files = _tracked_files(repo_root)
    rows: list[AdrCoverage] = []

    for adr in _accepted_adrs(repo_root):
        adr_id = f"ADR-{adr.adr_number}"
        implementation_paths, enforcement_paths, manual_exception = _collect_references(
            repo_root,
            tracked_files,
            adr_id,
        )
        rows.append(
            AdrCoverage(
                adr_id=adr_id,
                title=adr.title,
                decision_path=(
                    "docs/02-architecture/decisions/" + adr.file_path
                ),
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
            "tracked_file_discovery": "git ls-files",
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


def _write_artifacts(payload: dict[str, object], *, json_out: Path, md_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(render_markdown(payload), encoding="utf-8")


def _check_artifacts(payload: dict[str, object], *, json_out: Path, md_out: Path) -> list[str]:
    errors: list[str] = []
    expected_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(payload)
    if not json_out.exists() or json_out.read_text(encoding="utf-8") != expected_json:
        errors.append(f"ADR enforcement JSON artifact is stale: {json_out}")
    if not md_out.exists() or md_out.read_text(encoding="utf-8") != expected_md:
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
        errors = _check_artifacts(payload, json_out=json_out, md_out=md_out)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        return 0

    if args.update:
        _write_artifacts(payload, json_out=json_out, md_out=md_out)
        return 0

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

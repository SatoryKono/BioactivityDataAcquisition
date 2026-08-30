#!/usr/bin/env python3
"""Contract verify for P1 (#9808) — checks on generated/ catalog.

Checks:
  - generated_exists              — generated/ contains at least one domain/profile md
  - profile_precedence            — compiled params reflect profile precedence
  - deterministic_compile         — recompile produces same bytes + prompt_sha8
  - finding_fingerprint_stability — sha256(domain|requirement_id|root_cause|canonical_paths)

CLI:
  python -m scripts.ai.prompts.verify
  python -m scripts.ai.prompts.verify --golden  # also compare golden snapshots if present
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from scripts.ai.prompts.registry import PROMPTS_ROOT as _REG_PROMPTS_ROOT

    PROMPTS_ROOT: Path = _REG_PROMPTS_ROOT
except Exception:
    PROMPTS_ROOT = Path(__file__).resolve().parents[3] / "docs" / "00-project" / "ai" / "prompts"

GENERATED_ROOT = PROMPTS_ROOT / "generated"
OVERLAYS_DIR = PROMPTS_ROOT / "overlays"
PROFILES_DIR = PROMPTS_ROOT / "profiles"
GOLDEN_ROOT = PROMPTS_ROOT / "golden"  # optional

ALLOW_KEYS = {
    "ALLOW_ISSUE_WRITE",
    "ALLOW_PUSH",
    "ALLOW_MERGE",
    "ALLOW_CLOSE",
    "ALLOW_NETWORK",
    "ALLOW_FULL_SUITE",
}

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class VerifyIssue:
    level: str  # error | warning
    code: str
    message: str
    path: str = ""


@dataclass(slots=True)
class VerifyReport:
    errors: list[VerifyIssue] = field(default_factory=list)
    warnings: list[VerifyIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, code: str, message: str, path: str = "") -> None:
        self.errors.append(VerifyIssue("error", code, message, path))

    def add_warning(self, code: str, message: str, path: str = "") -> None:
        self.warnings.append(VerifyIssue("warning", code, message, path))


def _sha8(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:8]


# ---------------------------------------------------------------------------
# finding_fingerprint_stability  (matches evidence-contract-v3.md)
# ---------------------------------------------------------------------------


def finding_fingerprint(
    domain: str,
    requirement_id: str,
    root_cause: str,
    canonical_paths: list[str],
) -> str:
    """Stable sha256(domain|requirement_id|root_cause|canonical_paths).

    canonical_paths are sorted, de-duplicated, repo-relative; joined with ",".
    Returns 64-hex.
    """
    cleaned = sorted({p.strip() for p in canonical_paths if p.strip()})
    joined = ",".join(cleaned)
    payload = "|".join([domain, requirement_id, root_cause, joined])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def check_fingerprint_stability(report: VerifyReport) -> None:
    # Known vectors: claim paraphrasing must not change fingerprint when
    # domain, requirement_id, root_cause, and path set are identical.
    fp_a = finding_fingerprint(
        domain="docs",
        requirement_id="REQ-001",
        root_cause="broken SSOT link in README",
        canonical_paths=["README.md", "docs/guide.md"],
    )
    fp_b = finding_fingerprint(
        domain="docs",
        requirement_id="REQ-001",
        root_cause="broken SSOT link in README",
        canonical_paths=["docs/guide.md", "README.md"],  # reordered
    )
    if fp_a != fp_b:
        report.add_error(
            "finding_fingerprint_stability",
            f"fingerprint must be order-insensitive: {fp_a} != {fp_b}",
        )

    fp_c = finding_fingerprint(
        domain="docs",
        requirement_id="REQ-001",
        root_cause="broken SSOT link in README",
        canonical_paths=["README.md", "docs/guide.md", "README.md"],  # duplicate
    )
    if fp_a != fp_c:
        report.add_error(
            "finding_fingerprint_stability",
            "fingerprint must deduplicate canonical_paths",
        )

    # Different root cause must yield different fingerprint
    fp_diff = finding_fingerprint(
        domain="docs",
        requirement_id="REQ-001",
        root_cause="typo in guide",
        canonical_paths=["README.md", "docs/guide.md"],
    )
    if fp_a == fp_diff:
        report.add_error(
            "finding_fingerprint_stability",
            "different root_cause must yield different fingerprint",
        )

    # Schema: must be 64 hex
    if len(fp_a) != 64 or not all(c in "0123456789abcdef" for c in fp_a):
        report.add_error(
            "finding_fingerprint_stability",
            f"fingerprint must be 64 hex: got {fp_a!r}",
        )


# ---------------------------------------------------------------------------
# Generated / deterministic / precedence
# ---------------------------------------------------------------------------


def _parse_provenance_header(text: str) -> dict[str, str] | None:
    """Extract provenance fields from first 3 lines if present."""
    import re

    m = re.search(r"<!-- provenance:\s*(.*?)\s*-->", text, re.S)
    if m is None:
        return None
    raw = m.group(1)
    fields: dict[str, str] = {}
    for part in re.split(r"\s+", raw.strip()):
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k] = v
    return fields


def check_generated_catalog(report: VerifyReport) -> list[Path]:
    files = sorted(GENERATED_ROOT.rglob("*.md"))
    # Exclude CATALOG.md from domain/profile listing — but catalog must exist
    domain_files = [p for p in files if p.name != "CATALOG.md"]
    catalog = GENERATED_ROOT / "CATALOG.md"
    if not GENERATED_ROOT.is_dir():
        report.add_error("generated_exists", f"generated dir not found: {GENERATED_ROOT}")
        return domain_files
    if not domain_files:
        report.add_error("generated_exists", f"no generated domain/profile files under {GENERATED_ROOT}")
    if not catalog.is_file():
        report.add_warning("generated_catalog_missing", f"CATALOG.md not found: {catalog}")

    # Every generated file should have provenance header + prompt_sha8
    for p in domain_files:
        try:
            text = p.read_text(encoding="utf-8").replace("\r\n", "\n")
        except Exception as exc:
            report.add_error("generated_read", str(exc), p.as_posix())
            continue
        prov = _parse_provenance_header(text)
        if prov is None or "prompt_sha8" not in prov:
            report.add_error(
                "generated_provenance",
                "missing provenance header with prompt_sha8",
                p.as_posix(),
            )
            continue
        # Verify prompt_sha8 matches body hash (header excluded)
        lines = text.splitlines()
        body_start = 0
        for idx, line in enumerate(lines):
            if line.startswith("<!-- params:"):
                body_start = idx + 1
                break
        body = "\n".join(lines[body_start:]).lstrip("\n")
        if not body.endswith("\n"):
            body += "\n"
        expected_sha8 = _sha8(body.encode("utf-8"))
        if prov.get("prompt_sha8") != expected_sha8:
            report.add_error(
                "deterministic_compile",
                f"prompt_sha8 mismatch: header {prov.get('prompt_sha8')} != body {expected_sha8}",
                p.as_posix(),
            )
    return domain_files


def check_deterministic_recompile(report: VerifyReport) -> None:
    """Recompile overlays×profiles and compare to files on disk."""
    try:
        from scripts.ai.prompts.compile import compile_one, discover_overlays, discover_profiles
    except ImportError as exc:
        report.add_warning("compile_import", f"could not import compile: {exc}")
        return

    overlays = discover_overlays()
    profiles = discover_profiles()
    if not overlays or not profiles:
        report.add_warning("deterministic_compile", "no overlays or profiles to recompile")
        return

    for domain in sorted(overlays):
        for profile in sorted(profiles):
            expected_path = GENERATED_ROOT / domain / f"{profile}.md"
            if not expected_path.is_file():
                # generated_exists already reports this; skip double-report
                continue
            result = compile_one(domain, profile, check=False)
            if result.get("error"):
                report.add_error(
                    "deterministic_compile",
                    f"compile failed for {domain}/{profile}: {result['error']}",
                    expected_path.as_posix(),
                )
                continue
            rendered: str | None = result.get("rendered_text")
            if rendered is None:
                continue
            rendered_norm = rendered.replace("\r\n", "\n")
            on_disk = expected_path.read_text(encoding="utf-8").replace("\r\n", "\n")
            if rendered_norm != on_disk:
                exp_sha8 = result.get("prompt_sha8", "?")
                disk_sha8 = _sha8(
                    "\n".join(on_disk.splitlines()[3:]).lstrip("\n").encode("utf-8")
                    if "<!-- provenance:" in on_disk
                    else on_disk.encode("utf-8")
                )
                report.add_error(
                    "deterministic_compile",
                    f"recompile mismatch for {domain}/{profile}: "
                    f"expected prompt_sha8 {exp_sha8}, disk body sha8 {disk_sha8} — bytes differ",
                    expected_path.as_posix(),
                )


def check_profile_precedence(report: VerifyReport) -> None:
    """Ensure generated params respect profile precedence."""
    try:
        import yaml
    except ImportError:
        report.add_warning("profile_precedence", "yaml not available for precedence check")
        return

    files = [p for p in sorted(GENERATED_ROOT.rglob("*.md")) if p.name != "CATALOG.md"]
    if not files:
        return

    import re

    params_re = re.compile(r"<!-- params:\s*(.*?)\s*-->", re.S)
    for p in files:
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        m = params_re.search(text)
        if m is None:
            continue
        raw_params = m.group(1).strip()
        parsed: dict[str, str] = {}
        for part in raw_params.split():
            if "=" in part:
                k, v = part.split("=", 1)
                parsed[k] = v

        profile = p.stem
        domain = p.parent.name

        profile_path = PROFILES_DIR / f"{profile}.yaml"
        if profile_path.is_file():
            try:
                prof = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            for k in ("MODE", "LANGUAGE", "AUDIT_MODE", "N"):
                if k in prof and str(prof[k]).lower() != parsed.get(k, "").lower() and k in parsed:
                    report.add_error(
                        "profile_precedence",
                        f"{domain}/{profile}: param {k} header {parsed.get(k)!r} != profile {prof[k]!r}",
                        p.as_posix(),
                    )
            for k in ALLOW_KEYS:
                if k in prof:
                    expected = "true" if prof[k] else "false"
                    if k in parsed and parsed[k] != expected:
                        report.add_error(
                            "profile_precedence",
                            f"{domain}/{profile}: {k} header {parsed[k]!r} != profile {expected!r}",
                            p.as_posix(),
                        )
        else:
            report.add_warning(
                "profile_precedence",
                f"profile yaml not found for generated {domain}/{profile}",
                p.as_posix(),
            )


def check_golden(report: VerifyReport) -> None:
    if not GOLDEN_ROOT.is_dir():
        report.add_warning("golden_missing", f"golden dir not found: {GOLDEN_ROOT} (skip)")
        return

    goldens = sorted(GOLDEN_ROOT.rglob("*.md"))
    if not goldens:
        report.add_warning("golden_empty", f"no golden files under {GOLDEN_ROOT}")
        return
    for gold in goldens:
        rel = gold.relative_to(GOLDEN_ROOT)
        candidate = GENERATED_ROOT / rel
        if not candidate.is_file():
            report.add_error("golden_missing_generated", f"golden {rel} has no generated counterpart", gold.as_posix())
            continue
        g_text = gold.read_text(encoding="utf-8").replace("\r\n", "\n")
        c_text = candidate.read_text(encoding="utf-8").replace("\r\n", "\n")
        if g_text != c_text:
            report.add_error(
                "golden_mismatch",
                f"golden {rel} differs from generated/{rel}",
                gold.as_posix(),
            )


def verify_all(*, golden: bool = False) -> VerifyReport:
    report = VerifyReport()
    check_generated_catalog(report)
    check_deterministic_recompile(report)
    check_profile_precedence(report)
    check_fingerprint_stability(report)
    if golden:
        check_golden(report)

    report.stats = {
        "errors": len(report.errors),
        "warnings": len(report.warnings),
        "generated_files": len([p for p in GENERATED_ROOT.rglob("*.md") if p.name != "CATALOG.md"])
        if GENERATED_ROOT.is_dir()
        else 0,
    }
    return report


def format_report(report: VerifyReport, *, title: str = "Prompt verify") -> str:
    lines = [title, ""]
    if report.stats:
        lines.append(f"stats: {report.stats}")
        lines.append("")
    if not report.errors and not report.warnings:
        lines.append("OK — no issues")
        return "\n".join(lines) + "\n"
    for issue in report.errors:
        loc = f" [{issue.path}]" if issue.path else ""
        lines.append(f"ERROR {issue.code}{loc}: {issue.message}")
    for issue in report.warnings:
        loc = f" [{issue.path}]" if issue.path else ""
        lines.append(f"WARN  {issue.code}{loc}: {issue.message}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.ai.prompts.verify",
        description="Contract verify for generated prompt catalog (P1 #9808)",
    )
    parser.add_argument(
        "--golden",
        action="store_true",
        help="Also compare generated/ against golden/ snapshots",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = verify_all(golden=args.golden)
    text = format_report(report)
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        assert sys.stdout.buffer is not None
        sys.stdout.buffer.write(text.encode("utf-8"))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

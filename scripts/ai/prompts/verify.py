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
import importlib.util
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from scripts.ai.prompts.registry import PROMPTS_ROOT as _REG_PROMPTS_ROOT

    PROMPTS_ROOT: Path = _REG_PROMPTS_ROOT
except ImportError:
    PROMPTS_ROOT = (
        Path(__file__).resolve().parents[3] / "docs" / "00-project" / "ai" / "prompts"
    )

GENERATED_ROOT = PROMPTS_ROOT / "generated"
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

_CATALOG_FILENAME = "CATALOG.md"
_HTML_COMMENT_END = "-->"
_PARAMS_PREFIX = "<!-- params:"
_PROVENANCE_PREFIX = "<!-- provenance:"
_PROFILE_SCALAR_KEYS = ("MODE", "LANGUAGE", "AUDIT_MODE", "N")
_CODE_DETERMINISTIC = "deterministic_compile"
_CODE_FINGERPRINT = "finding_fingerprint_stability"
_CODE_PRECEDENCE = "profile_precedence"
_PROMPT_SHA8 = "prompt_sha8"

_FP_DOMAIN = "docs"
_FP_REQUIREMENT_ID = "REQ-001"
_FP_ROOT_CAUSE = "broken SSOT link in README"
_FP_ROOT_CAUSE_OTHER = "typo in guide"
_FP_README = "README.md"
_FP_GUIDE = "docs/guide.md"
_FP_HEX = "0123456789abcdef"

CompileOne = Callable[..., dict[str, Any]]


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


def _parse_kv_pairs(raw: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in raw.split():
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key] = value
    return fields


def _html_comment_payload(text: str, prefix: str) -> str | None:
    """Return the inner payload of the first single-line HTML comment with prefix.

    Line-scan is linear (no regex backtracking, S8786) and allows values
    such as ``<shortsha>`` that contain ``>``.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix) and stripped.endswith(_HTML_COMMENT_END):
            return stripped[len(prefix) : -len(_HTML_COMMENT_END)].strip()
    return None


def _parse_html_kv_comment(text: str, prefix: str) -> dict[str, str] | None:
    raw = _html_comment_payload(text, prefix)
    if raw is None:
        return None
    return _parse_kv_pairs(raw)


def _iter_generated_domain_files() -> list[Path]:
    if not GENERATED_ROOT.is_dir():
        return []
    return sorted(
        path for path in GENERATED_ROOT.rglob("*.md") if path.name != _CATALOG_FILENAME
    )


def _body_after_params_header(text: str) -> str:
    lines = text.splitlines()
    body_start = 0
    for idx, line in enumerate(lines):
        if line.startswith(_PARAMS_PREFIX):
            body_start = idx + 1
            break
    body = "\n".join(lines[body_start:]).lstrip("\n")
    if not body.endswith("\n"):
        body += "\n"
    return body


def _disk_body_sha8(on_disk: str) -> str:
    if _PROVENANCE_PREFIX not in on_disk:
        return _sha8(on_disk.encode("utf-8"))
    body = "\n".join(on_disk.splitlines()[3:]).lstrip("\n")
    return _sha8(body.encode("utf-8"))


def _read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _try_read_utf8(report: VerifyReport, path: Path, *, code: str) -> str | None:
    try:
        return _read_utf8(path)
    except (OSError, UnicodeError) as exc:
        report.add_error(code, str(exc), path.as_posix())
        return None


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


def _fixture_fingerprint(
    root_cause: str,
    canonical_paths: list[str],
) -> str:
    return finding_fingerprint(
        _FP_DOMAIN, _FP_REQUIREMENT_ID, root_cause, canonical_paths
    )


def check_fingerprint_stability(report: VerifyReport) -> None:
    # Known vectors: claim paraphrasing must not change fingerprint when
    # domain, requirement_id, root_cause, and path set are identical.
    paths = [_FP_README, _FP_GUIDE]
    fp_a = _fixture_fingerprint(_FP_ROOT_CAUSE, paths)
    fp_b = _fixture_fingerprint(_FP_ROOT_CAUSE, [_FP_GUIDE, _FP_README])
    if fp_a != fp_b:
        report.add_error(
            _CODE_FINGERPRINT,
            f"fingerprint must be order-insensitive: {fp_a} != {fp_b}",
        )

    fp_c = _fixture_fingerprint(_FP_ROOT_CAUSE, [_FP_README, _FP_GUIDE, _FP_README])
    if fp_a != fp_c:
        report.add_error(
            _CODE_FINGERPRINT,
            "fingerprint must deduplicate canonical_paths",
        )

    fp_diff = _fixture_fingerprint(_FP_ROOT_CAUSE_OTHER, paths)
    if fp_a == fp_diff:
        report.add_error(
            _CODE_FINGERPRINT,
            "different root_cause must yield different fingerprint",
        )

    if len(fp_a) != 64 or any(char not in _FP_HEX for char in fp_a):
        report.add_error(
            _CODE_FINGERPRINT,
            f"fingerprint must be 64 hex: got {fp_a!r}",
        )


# ---------------------------------------------------------------------------
# Generated / deterministic / precedence
# ---------------------------------------------------------------------------


def _parse_provenance_header(text: str) -> dict[str, str] | None:
    """Extract provenance fields from the provenance HTML comment if present."""
    return _parse_html_kv_comment(text, _PROVENANCE_PREFIX)


def _parse_params_header(text: str) -> dict[str, str] | None:
    return _parse_html_kv_comment(text, _PARAMS_PREFIX)


def _check_one_generated_file(report: VerifyReport, path: Path) -> None:
    text = _try_read_utf8(report, path, code="generated_read")
    if text is None:
        return
    provenance = _parse_provenance_header(text)
    if provenance is None or _PROMPT_SHA8 not in provenance:
        report.add_error(
            "generated_provenance",
            "missing provenance header with prompt_sha8",
            path.as_posix(),
        )
        return
    expected_sha8 = _sha8(_body_after_params_header(text).encode("utf-8"))
    if provenance.get(_PROMPT_SHA8) == expected_sha8:
        return
    report.add_error(
        _CODE_DETERMINISTIC,
        f"prompt_sha8 mismatch: header {provenance.get(_PROMPT_SHA8)} != body {expected_sha8}",
        path.as_posix(),
    )


def check_generated_catalog(report: VerifyReport) -> int:
    """Compile every domain×profile in memory and check provenance headers."""
    try:
        from scripts.ai.prompts.compile import (
            compile_one,
            discover_overlays,
            discover_profiles,
        )
    except ImportError as exc:
        report.add_error("compile_import", f"could not import compile: {exc}")
        return 0

    overlays = discover_overlays()
    profiles = discover_profiles()
    if not overlays:
        report.add_error("generated_exists", f"no domains in {PROMPTS_ROOT / 'domains.yaml'}")
        return 0
    compiled = 0
    for domain in overlays:
        for profile in profiles:
            result = compile_one(domain, profile)
            label = f"{domain}/{profile}"
            if result.get("error"):
                report.add_error("compile", str(result["error"]), label)
                continue
            text = result.get("rendered_text")
            if not isinstance(text, str):
                report.add_error("compile", "no rendered_text", label)
                continue
            provenance = _parse_provenance_header(text)
            if provenance is None or _PROMPT_SHA8 not in provenance:
                report.add_error(
                    "generated_provenance",
                    "missing provenance header with prompt_sha8",
                    label,
                )
                continue
            expected_sha8 = _sha8(_body_after_params_header(text).encode("utf-8"))
            if provenance.get(_PROMPT_SHA8) != expected_sha8:
                report.add_error(
                    _CODE_DETERMINISTIC,
                    (
                        f"prompt_sha8 mismatch: header {provenance.get(_PROMPT_SHA8)} "
                        f"!= body {expected_sha8}"
                    ),
                    label,
                )
            compiled += 1
    return compiled


def _check_recompile_pair(
    report: VerifyReport,
    domain: str,
    profile: str,
    compile_one: CompileOne,
) -> None:
    expected_path = GENERATED_ROOT / domain / f"{profile}.md"
    if not expected_path.is_file():
        return
    result = compile_one(domain, profile, check=False)
    if result.get("error"):
        report.add_error(
            _CODE_DETERMINISTIC,
            f"compile failed for {domain}/{profile}: {result['error']}",
            expected_path.as_posix(),
        )
        return
    rendered = result.get("rendered_text")
    if not isinstance(rendered, str):
        report.add_error(
            _CODE_DETERMINISTIC,
            f"compile produced no rendered_text for {domain}/{profile}",
            expected_path.as_posix(),
        )
        return
    on_disk = _try_read_utf8(report, expected_path, code=_CODE_DETERMINISTIC)
    if on_disk is None:
        return
    if rendered.replace("\r\n", "\n") == on_disk:
        return
    exp_sha8 = result.get(_PROMPT_SHA8, "?")
    disk_sha8 = _disk_body_sha8(on_disk)
    report.add_error(
        _CODE_DETERMINISTIC,
        f"recompile mismatch for {domain}/{profile}: "
        f"expected prompt_sha8 {exp_sha8}, disk body sha8 {disk_sha8} — bytes differ",
        expected_path.as_posix(),
    )


def check_deterministic_recompile(report: VerifyReport) -> None:
    """Recompile overlays×profiles twice and require byte-identical output."""
    try:
        from scripts.ai.prompts.compile import (
            compile_one,
            discover_overlays,
            discover_profiles,
        )
    except ImportError as exc:
        report.add_warning("compile_import", f"could not import compile: {exc}")
        return

    overlays = discover_overlays()
    profiles = discover_profiles()
    if not overlays or not profiles:
        report.add_warning(_CODE_DETERMINISTIC, "no overlays or profiles to recompile")
        return

    for domain in sorted(overlays):
        for profile in sorted(profiles):
            first = compile_one(domain, profile)
            second = compile_one(domain, profile)
            label = f"{domain}/{profile}"
            if first.get("error") or second.get("error"):
                report.add_error(
                    _CODE_DETERMINISTIC,
                    f"compile failed: {first.get('error') or second.get('error')}",
                    label,
                )
                continue
            if first.get("rendered_text") != second.get("rendered_text"):
                report.add_error(
                    _CODE_DETERMINISTIC,
                    "recompile mismatch: two in-memory compiles differ",
                    label,
                )


def _load_profile_mapping(profile_path: Path) -> dict[str, Any] | None:
    import yaml

    try:
        loaded = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    if isinstance(loaded, dict):
        return loaded
    return None


def _check_scalar_profile_params(
    report: VerifyReport,
    domain: str,
    profile: str,
    parsed: Mapping[str, str],
    prof: Mapping[str, Any],
    path: Path,
) -> None:
    for key in _PROFILE_SCALAR_KEYS:
        if key not in prof or key not in parsed:
            continue
        if str(prof[key]).lower() == parsed.get(key, "").lower():
            continue
        report.add_error(
            _CODE_PRECEDENCE,
            f"{domain}/{profile}: param {key} header {parsed.get(key)!r} != profile {prof[key]!r}",
            path.as_posix(),
        )


def _check_allow_profile_params(
    report: VerifyReport,
    domain: str,
    profile: str,
    parsed: Mapping[str, str],
    prof: Mapping[str, Any],
    path: Path,
) -> None:
    for key in ALLOW_KEYS:
        if key not in prof:
            continue
        expected = "true" if prof[key] else "false"
        if key not in parsed or parsed[key] == expected:
            continue
        report.add_error(
            _CODE_PRECEDENCE,
            f"{domain}/{profile}: {key} header {parsed[key]!r} != profile {expected!r}",
            path.as_posix(),
        )


def _check_one_generated_profile(report: VerifyReport, path: Path) -> None:
    text = _try_read_utf8(report, path, code="generated_read")
    if text is None:
        return
    parsed = _parse_params_header(text)
    if parsed is None:
        return
    profile = path.stem
    domain = path.parent.name
    profile_path = PROFILES_DIR / f"{profile}.yaml"
    if not profile_path.is_file():
        report.add_warning(
            _CODE_PRECEDENCE,
            f"profile yaml not found for generated {domain}/{profile}",
            path.as_posix(),
        )
        return
    prof = _load_profile_mapping(profile_path)
    if prof is None:
        report.add_error(
            _CODE_PRECEDENCE,
            f"unreadable or invalid profile yaml: {profile_path}",
            path.as_posix(),
        )
        return
    _check_scalar_profile_params(report, domain, profile, parsed, prof, path)
    _check_allow_profile_params(report, domain, profile, parsed, prof, path)


def check_profile_precedence(report: VerifyReport) -> None:
    """Ensure compiled params respect profile precedence."""
    if importlib.util.find_spec("yaml") is None:
        report.add_warning(_CODE_PRECEDENCE, "yaml not available for precedence check")
        return
    try:
        from scripts.ai.prompts.compile import (
            compile_one,
            discover_overlays,
            discover_profiles,
        )
    except ImportError as exc:
        report.add_warning("compile_import", f"could not import compile: {exc}")
        return

    overlays = discover_overlays()
    profiles = discover_profiles()
    for domain in overlays:
        for profile in profiles:
            result = compile_one(domain, profile)
            text = result.get("rendered_text")
            if result.get("error") or not isinstance(text, str):
                continue
            parsed = _parse_params_header(text)
            if parsed is None:
                continue
            profile_path = PROFILES_DIR / f"{profile}.yaml"
            prof = _load_profile_mapping(profile_path)
            if prof is None:
                report.add_error(
                    _CODE_PRECEDENCE,
                    f"unreadable or invalid profile yaml: {profile_path}",
                    f"{domain}/{profile}",
                )
                continue
            _check_scalar_profile_params(
                report, domain, profile, parsed, prof, profile_path
            )
            _check_allow_profile_params(
                report, domain, profile, parsed, prof, profile_path
            )


def check_golden(report: VerifyReport) -> None:
    if not GOLDEN_ROOT.is_dir():
        report.add_warning(
            "golden_missing", f"golden dir not found: {GOLDEN_ROOT} (skip)"
        )
        return

    goldens = sorted(GOLDEN_ROOT.rglob("*.md"))
    if not goldens:
        report.add_warning("golden_empty", f"no golden files under {GOLDEN_ROOT}")
        return
    for gold in goldens:
        rel = gold.relative_to(GOLDEN_ROOT)
        candidate = GENERATED_ROOT / rel
        if not candidate.is_file():
            report.add_error(
                "golden_missing_generated",
                f"golden {rel} has no generated counterpart",
                gold.as_posix(),
            )
            continue
        gold_text = _try_read_utf8(report, gold, code="golden_mismatch")
        candidate_text = _try_read_utf8(report, candidate, code="golden_mismatch")
        if gold_text is None or candidate_text is None:
            continue
        if gold_text != candidate_text:
            report.add_error(
                "golden_mismatch",
                f"golden {rel} differs from generated/{rel}",
                gold.as_posix(),
            )


def verify_all(*, golden: bool = False) -> VerifyReport:
    report = VerifyReport()
    compiled = check_generated_catalog(report)
    check_deterministic_recompile(report)
    check_profile_precedence(report)
    check_fingerprint_stability(report)
    if golden:
        check_golden(report)

    report.stats = {
        "errors": len(report.errors),
        "warnings": len(report.warnings),
        "generated_files": compiled,
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
        buffer = sys.stdout.buffer
        if buffer is None:
            raise
        buffer.write(text.encode("utf-8"))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

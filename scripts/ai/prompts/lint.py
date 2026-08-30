#!/usr/bin/env python3
"""Lint checks for P1 (#9808) prompt kernel/overlay/profile compiler.

Checks:
  - kernel_schema_valid
  - overlay_schema_valid  (jsonschema if available, else minimal fallback)
  - guard_non_weakening   (overlay must not contain ALLOW_*=true / controller weakening)
  - no_controller_duplication (regex scan for controller phrases like
      "Scope freeze|Iteration i|Issue-sync|Validate|Post-audit" in overlay)
  - full_profile_explicit  (ALLOW_*=true only in full-write profile)

CLI:
  python -m scripts.ai.prompts.lint           # all overlays + profiles
  python -m scripts.ai.prompts.lint --strict  # fail on warnings too
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.ai.prompts.registry import PROMPTS_ROOT as _REG_PROMPTS_ROOT

    PROMPTS_ROOT: Path = _REG_PROMPTS_ROOT
except Exception:
    PROMPTS_ROOT = Path(__file__).resolve().parents[3] / "docs" / "00-project" / "ai" / "prompts"

OVERLAYS_DIR = PROMPTS_ROOT / "overlays"
PROFILES_DIR = PROMPTS_ROOT / "profiles"
SCHEMA_DIR = PROMPTS_ROOT / "_schema"

LOGGER = logging.getLogger(__name__)

# Controller phrase regex — case-insensitive scan on overlay *values*
# Covers stages / controller keywords that must live only in the kernel.
# NOTE: we scan joined overlay values, not raw YAML keys, to avoid
# false-positives on allowed field name ``VALIDATION:`` or OBJECT text
# like ``generate->validate->artifact``.
CONTROLLER_RE = re.compile(
    r"(Scope freeze|Iteration\s+i|Issue-sync|Post-audit|\bNormalize\b.*\bplan\b|\bPlan\s*[\|:])",
    re.I,
)

# Validate as controller stage (stage G) — only flag when it looks like
# an orchestration heading (e.g. "Validate:" or "Validate | foo"),
# not a bare verb in domain prose like "validate->artifact" or "validation".
CONTROLLER_VALIDATE_RE = re.compile(r"\bValidate\s*[\|:]\s*", re.I)

CONTROLLER_EXTRA_RE = re.compile(
    r"\b(Audit\s*[\|:]|Implement\s*[\|:]|Close\s*[\|:])",
    re.I,
)

ALLOWED_ALLOW_PROFILE = "full-write"

ALLOW_KEYS = {
    "ALLOW_ISSUE_WRITE",
    "ALLOW_PUSH",
    "ALLOW_MERGE",
    "ALLOW_CLOSE",
    "ALLOW_NETWORK",
    "ALLOW_FULL_SUITE",
}


@dataclass(slots=True)
class LintIssue:
    level: str  # "error" | "warning"
    code: str
    message: str
    path: str = ""


@dataclass(slots=True)
class LintReport:
    errors: list[LintIssue] = field(default_factory=list)
    warnings: list[LintIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, code: str, message: str, path: str = "") -> None:
        self.errors.append(LintIssue("error", code, message, path))

    def add_warning(self, code: str, message: str, path: str = "") -> None:
        self.warnings.append(LintIssue("warning", code, message, path))


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any] | None:
    import json

    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_with_jsonschema(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Validate via jsonschema if available; return error messages."""
    try:
        import jsonschema  # type: ignore[import-untyped]
    except ImportError:
        return []  # fallback handled by caller

    validator_cls = None
    # Prefer 2020-12 validator if schema declares it
    try:
        from jsonschema import Draft202012Validator  # type: ignore[attr-defined]

        validator_cls = Draft202012Validator
    except ImportError:
        try:
            from jsonschema import Draft7Validator  # type: ignore[attr-defined]

            validator_cls = Draft7Validator
        except ImportError:
            import jsonschema as _js  # type: ignore[import-not-found]

            _js.validate(data, schema)  # type: ignore[call-arg]
            return []

    assert validator_cls is not None
    validator = validator_cls(schema)
    msgs: list[str] = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) if err.path else "(root)"
        msgs.append(f"{loc}: {err.message}")
    return msgs


def _minimal_overlay_checks(data: dict[str, Any]) -> list[str]:
    """Fallback when jsonschema unavailable — checks required fields + ALLOW_* ban."""
    errors: list[str] = []
    for req in ("domain", "id", "OBJECT", "SCOPE"):
        if req not in data:
            errors.append(f"missing required field: {req}")
    if "id" in data and not str(data["id"]).startswith("prompt.audit."):
        errors.append("id must start with prompt.audit.")
    scope = data.get("SCOPE")
    if scope is not None and not isinstance(scope, list):
        errors.append("SCOPE must be an array")
    elif isinstance(scope, list) and len(scope) == 0:
        errors.append("SCOPE must have at least one entry")
    for k in data:
        if k.startswith("ALLOW_"):
            errors.append(f"overlay must not declare {k} (fail-closed)")
    return errors


def _minimal_kernel_checks(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "SCOPE" not in data:
        errors.append("kernel params missing SCOPE")
    if "MODE" not in data:
        errors.append("kernel params missing MODE")
    mode = data.get("MODE")
    if mode is not None and mode not in {"audit", "audit+issues", "full"}:
        errors.append(f"invalid MODE: {mode!r}")
    return errors


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------


def check_kernel_schema(report: LintReport) -> None:
    schema = _load_json(SCHEMA_DIR / "kernel.schema.json")
    if schema is None:
        report.add_warning("kernel_schema_missing", f"schema not found: {SCHEMA_DIR / 'kernel.schema.json'}")
        return
    # Kernel schema describes params object; we validate a sample defaults payload.
    sample: dict[str, Any] = {"SCOPE": "src/bioetl/domain", "MODE": "audit"}
    if _has_jsonschema():
        errs = _validate_with_jsonschema(sample, schema)
        for msg in errs:
            report.add_error("kernel_schema_valid", msg, str(SCHEMA_DIR / "kernel.schema.json"))
    else:
        errs = _minimal_kernel_checks(sample)
        for msg in errs:
            report.add_error("kernel_schema_valid", msg)


def _has_jsonschema() -> bool:
    try:
        import jsonschema  # type: ignore[import-untyped]

        return True
    except ImportError:
        return False


def check_overlay(report: LintReport, path: Path, data: dict[str, Any], raw_text: str) -> None:
    # -- overlay_schema_valid
    schema = _load_json(SCHEMA_DIR / "domain-overlay.schema.json")
    if schema is None:
        report.add_warning(
            "overlay_schema_missing",
            f"schema not found: {SCHEMA_DIR / 'domain-overlay.schema.json'}",
            path.as_posix(),
        )
    else:
        if _has_jsonschema():
            errs = _validate_with_jsonschema(data, schema)
            for msg in errs:
                report.add_error("overlay_schema_valid", msg, path.as_posix())
        else:
            for msg in _minimal_overlay_checks(data):
                report.add_error("overlay_schema_valid", msg, path.as_posix())

    # -- guard_non_weakening: overlay must not contain ALLOW_*=true or weakening keys
    # Schema already bans ALLOW_*; this guard gives a clearer fail-closed message
    # and the raw-text scan below covers nested ALLOW_*: true literals.
    for key, _val in data.items():
        if key.startswith("ALLOW_"):
            report.add_error(
                "guard_non_weakening",
                f"overlay must not declare {key} (fail-closed); move ALLOW_* to profile",
                path.as_posix(),
            )
    # Scan raw text for ALLOW_*=true literal — covers nested cases
    for m in re.finditer(r"ALLOW_[A-Z_]+\s*:\s*true", raw_text):
        snippet = m.group(0).strip()
        already = any(snippet.split(":")[0].strip() in e.message for e in report.errors if e.path == path.as_posix())
        if not already:
            report.add_error(
                "guard_non_weakening",
                f"overlay contains weakening declaration: {snippet}",
                path.as_posix(),
            )

    # Check for controller-weakening keywords in free-form values
    guard_keywords_re = re.compile(r"\b(Iteration|Issue-sync|ALLOW_NETWORK|ALLOW_FULL_SUITE)\b", re.I)
    for key, val in data.items():
        if isinstance(val, list):
            joined = " ".join(str(x) for x in val)
        elif isinstance(val, str):
            joined = val
        else:
            continue
        if guard_keywords_re.search(joined) and key not in {"domain", "id", "successor"}:
            if re.search(r"\bIteration\b", joined, re.I) or re.search(r"Issue-sync", joined, re.I):
                report.add_error(
                    "guard_non_weakening",
                    f"overlay field {key!r} contains controller keyword '{guard_keywords_re.search(joined).group(0)}'",
                    path.as_posix(),
                )

    # -- no_controller_duplication: regex scan for controller orchestration phrases
    # Build values-only text to avoid matching YAML keys like ``VALIDATION:``.
    values_parts: list[str] = []
    for v in data.values():
        if isinstance(v, list):
            values_parts.extend(str(x) for x in v)
        elif isinstance(v, str):
            values_parts.append(v)
    values_text = "\n".join(values_parts)
    for pat, label in (
        (CONTROLLER_RE, "controller phrase"),
        (CONTROLLER_VALIDATE_RE, "controller phrase"),
        (CONTROLLER_EXTRA_RE, "controller phrase"),
    ):
        m = pat.search(values_text)
        if m:
            snippet = m.group(0).strip()
            report.add_error(
                "no_controller_duplication",
                f"overlay contains {label} '{snippet}' — controller belongs in kernel fragment",
                path.as_posix(),
            )
            break  # one error per overlay for this check is enough


def check_profiles(report: LintReport) -> None:
    if not PROFILES_DIR.is_dir():
        report.add_warning("profiles_missing", f"profiles dir not found: {PROFILES_DIR}")
        return
    schema = _load_json(SCHEMA_DIR / "execution-profile.schema.json")
    has_js = _has_jsonschema()
    for path in sorted(PROFILES_DIR.glob("*.yaml")):
        try:
            raw = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw) or {}
        except Exception as exc:
            report.add_error("profile_parse", str(exc), path.as_posix())
            continue

        if not isinstance(data, dict):
            report.add_error("profile_parse", "profile must be a mapping", path.as_posix())
            continue

        if schema is not None and has_js:
            errs = _validate_with_jsonschema(data, schema)
            for msg in errs:
                report.add_error("profile_schema_valid", msg, path.as_posix())

        # -- full_profile_explicit: ALLOW_*=true only in full-write profile
        is_full_write = path.stem == ALLOWED_ALLOW_PROFILE
        for key in ALLOW_KEYS:
            if data.get(key) is True and not is_full_write:
                report.add_error(
                    "full_profile_explicit",
                    f"{key}=true only allowed in {ALLOWED_ALLOW_PROFILE}.yaml (found in {path.stem}.yaml)",
                    path.as_posix(),
                )


def lint_all(*, strict: bool = False) -> LintReport:  # noqa: ARG001 — strict handled by caller
    report = LintReport()
    check_kernel_schema(report)

    if not OVERLAYS_DIR.is_dir():
        report.add_warning("overlays_missing", f"overlays dir not found: {OVERLAYS_DIR}")
    else:
        for path in sorted(OVERLAYS_DIR.glob("*.yaml")):
            try:
                raw = path.read_text(encoding="utf-8")
                data = yaml.safe_load(raw) or {}
            except Exception as exc:
                report.add_error("overlay_parse", str(exc), path.as_posix())
                continue
            if not isinstance(data, dict):
                report.add_error("overlay_parse", "overlay must be a mapping", path.as_posix())
                continue
            check_overlay(report, path, data, raw)

    check_profiles(report)

    report.stats = {
        "errors": len(report.errors),
        "warnings": len(report.warnings),
        "overlays": len(list(OVERLAYS_DIR.glob("*.yaml"))) if OVERLAYS_DIR.is_dir() else 0,
        "profiles": len(list(PROFILES_DIR.glob("*.yaml"))) if PROFILES_DIR.is_dir() else 0,
    }
    return report


def format_report(report: LintReport, *, title: str = "Prompt lint") -> str:
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
        prog="python -m scripts.ai.prompts.lint",
        description="Lint kernel/overlay/profile checks (P1 #9808)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings as well as errors",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = lint_all(strict=args.strict)
    # Write to stdout using utf-8 aware path (avoid print for logging parity)
    text = format_report(report)
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        assert sys.stdout.buffer is not None
        sys.stdout.buffer.write(text.encode("utf-8"))

    if not report.ok:
        return 1
    if args.strict and report.warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

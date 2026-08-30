#!/usr/bin/env python3
"""Deterministic compiler for P1 (#9808) — kernel + overlay + profile → generated.

Reads:
  - fragments/cyclic-kernel-v3.md
  - overlays/<domain>.yaml
  - profiles/<profile>.yaml

Resolves {{PARAM}} tokens (N, SCOPE, MODE, AUDIT_MODE, LANGUAGE, BASE_BRANCH,
WORK_BRANCH, ALLOW_*) and emits deterministic byte-identical
docs/00-project/ai/prompts/generated/<domain>/<profile>.md with provenance
header (kernel_sha8 / overlay_sha8 / profile + prompt_sha8 + params).

prompt_sha8 = first 8 hex of sha256(rendered_body.encode("utf-8"))
where rendered_body is the kernel + overlay markdown after param substitution
(excluding the provenance header itself).

CLI:
  python -m scripts.ai.prompts.compile --domain docs --profile audit-readonly
  python -m scripts.ai.prompts.compile --all
  python -m scripts.ai.prompts.compile --all --check
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Paths — mirrors registry.py
# ---------------------------------------------------------------------------
try:
    from scripts.ai.prompts.registry import PROMPTS_ROOT as _RP
    from scripts.ai.prompts.registry import REPO_ROOT as _RR

    _PROMPTS_ROOT: Path = _RP
    _REPO_ROOT: Path = _RR
except ImportError:  # graceful fallback for importable tests without repo layout
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _PROMPTS_ROOT = _REPO_ROOT / "docs" / "00-project" / "ai" / "prompts"

PROMPTS_ROOT: Path = _PROMPTS_ROOT
REPO_ROOT: Path = _REPO_ROOT

KERNEL_PATH: Path = PROMPTS_ROOT / "fragments" / "cyclic-kernel-v3.md"
OVERLAYS_DIR: Path = PROMPTS_ROOT / "overlays"
PROFILES_DIR: Path = PROMPTS_ROOT / "profiles"
GENERATED_ROOT: Path = PROMPTS_ROOT / "generated"

PARAM_TOKEN_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")

# Default kernel params — mirrors docs/00-project/ai/prompts/_schema/kernel.schema.json
KERNEL_DEFAULTS: dict[str, Any] = {
    "N": 10,
    "MODE": "audit",
    "AUDIT_MODE": "full",
    "SCOPE": "",  # required — filled from overlay or profile; validated
    "BASE_BRANCH": "main",
    "WORK_BRANCH": "fix/audit-cycle",
    "ALLOW_ISSUE_WRITE": False,
    "ALLOW_PUSH": False,
    "ALLOW_MERGE": False,
    "ALLOW_CLOSE": False,
    "ALLOW_NETWORK": False,
    "ALLOW_FULL_SUITE": False,
    "MONITORING": False,
    "MAX_FILES_PER_SCOPE": 300,
    "MAX_ISSUES_PER_ITERATION": 5,
    "MAX_WAVES_PER_ITERATION": 3,
    "MAX_COMMAND_SECONDS": 900,
    "LANGUAGE": "ru",
}

ALLOW_KEYS = {k for k in KERNEL_DEFAULTS if k.startswith("ALLOW_")}

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------


def sha8(data: bytes) -> str:
    """First 8 hex of sha256."""
    return hashlib.sha256(data).hexdigest()[:8]


def file_sha8(path: Path) -> str:
    return sha8(path.read_bytes())


# ---------------------------------------------------------------------------
# Frontmatter / body helpers (mirrors registry.fragment_body)
# ---------------------------------------------------------------------------

_FRONTMATTER_DELIM = "---"


def strip_frontmatter(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        return text
    # find closing ---
    offset = len(lines[0])
    for line in lines[1:]:
        if line.strip() == _FRONTMATTER_DELIM:
            return text[offset + len(line) :].lstrip("\n")
        offset += len(line)
    return text


def kernel_body() -> str:
    raw = KERNEL_PATH.read_text(encoding="utf-8")
    return strip_frontmatter(raw).strip() + "\n"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_overlay(domain: str) -> tuple[dict[str, Any], bytes]:
    path = OVERLAYS_DIR / f"{domain}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"overlay not found: {path}")
    raw = path.read_bytes()
    data = yaml.safe_load(raw.decode("utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"overlay {domain} must be a mapping")
    return data, raw


def load_profile(profile: str) -> tuple[dict[str, Any], bytes]:
    path = PROFILES_DIR / f"{profile}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"profile not found: {path}")
    raw = path.read_bytes()
    data = yaml.safe_load(raw.decode("utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"profile {profile} must be a mapping")
    return data, raw


def discover_overlays() -> list[str]:
    if not OVERLAYS_DIR.is_dir():
        return []
    return sorted(p.stem for p in OVERLAYS_DIR.glob("*.yaml"))


def discover_profiles() -> list[str]:
    if not PROFILES_DIR.is_dir():
        return []
    return sorted(p.stem for p in PROFILES_DIR.glob("*.yaml"))


# ---------------------------------------------------------------------------
# Param resolution
# ---------------------------------------------------------------------------


def _format_param(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def resolve_params(
    overlay_data: dict[str, Any],
    profile_data: dict[str, Any],
    domain: str,
) -> dict[str, Any]:
    """Merge defaults + profile + overlay-derived SCOPE."""
    params: dict[str, Any] = dict(KERNEL_DEFAULTS)

    # Profile overrides (MODE, AUDIT_MODE, ALLOW_*, LANGUAGE, N ... )
    for key, val in profile_data.items():
        if key in {"name", "description"}:
            continue
        if key in params:
            params[key] = val
        elif key.startswith("ALLOW_") or key in {"MODE", "AUDIT_MODE", "N", "LANGUAGE", "SCOPE", "BASE_BRANCH", "WORK_BRANCH"}:
            params[key] = val

    # Overlay-derived SCOPE: SCOPE is array in overlay, string in kernel
    overlay_scope = overlay_data.get("SCOPE")
    if isinstance(overlay_scope, list) and overlay_scope:
        # Join with single space — deterministic
        params["SCOPE"] = " ".join(str(s) for s in overlay_scope)
    elif isinstance(overlay_scope, str) and overlay_scope:
        params["SCOPE"] = overlay_scope

    # WORK_BRANCH default templating: fix/<domain>-cycle-<shortsha> placeholder
    wb = str(params.get("WORK_BRANCH", ""))
    if "<domain>" in wb or "<shortsha>" in wb:
        wb = wb.replace("<domain>", domain)
        # <shortsha> stays as placeholder unless profile provides concrete value
        params["WORK_BRANCH"] = wb
    # If default still generic (fix/audit-cycle), specialize per domain
    if params.get("WORK_BRANCH") == "fix/audit-cycle":
        params["WORK_BRANCH"] = f"fix/{domain}-cycle-<shortsha>"

    # Ensure SCOPE present — compile fails fast if empty
    if not str(params.get("SCOPE", "")).strip():
        raise ValueError(f"resolved SCOPE is empty for domain {domain!r}")

    return params


def substitute_params(text: str, params: dict[str, Any]) -> str:
    """Replace {{PARAM}} tokens. Tokens not in params raise ValueError."""

    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in params:
            raise ValueError(f"missing required param: {key}")
        val = params[key]
        if isinstance(val, bool):
            return "true" if val else "false"
        return str(val)

    return PARAM_TOKEN_RE.sub(repl, text)


# ---------------------------------------------------------------------------
# Overlay markdown rendering
# ---------------------------------------------------------------------------


def render_overlay_sections(overlay: dict[str, Any]) -> str:
    lines: list[str] = []
    domain = overlay.get("domain", "")
    lines.append(f"## Domain overlay: `{domain}`")
    lines.append("")

    field_order = [
        ("OBJECT", "Object"),
        ("SCOPE", "Scope"),
        ("SSOT", "SSOT"),
        ("AUDIT_CONTOURS", "Audit contours"),
        ("MANDATORY_EVIDENCE", "Mandatory evidence"),
        ("VALIDATION", "Validation"),
        ("DOMAIN_STOP", "Domain stop"),
        ("OUTPUT_EXTRAS", "Output extras"),
    ]
    for key, title in field_order:
        val = overlay.get(key)
        if val is None:
            continue
        lines.append(f"### {title} (`{key}`)")
        lines.append("")
        if isinstance(val, list):
            for item in val:
                lines.append(f"- {item}")
        else:
            lines.append(str(val))
        lines.append("")

    # Include any additional scalar fields for determinism (sorted)
    known = {k for k, _ in field_order} | {"domain", "id", "successor"}
    extras = sorted(k for k in overlay if k not in known)
    if extras:
        lines.append("### Additional overlay fields")
        lines.append("")
        for k in extras:
            lines.append(f"- `{k}`: {overlay[k]}")
        lines.append("")

    if overlay.get("id"):
        lines.append(f"Overlay id: `{overlay['id']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Full render
# ---------------------------------------------------------------------------


def render_compiled(
    _domain: str,
    profile: str,
    kernel_sha8: str,
    overlay_sha8: str,
    params: dict[str, Any],
    body: str,
) -> tuple[str, str]:
    """Return (prompt_sha8, final_text).

    prompt_sha8 is hash of body (kernel+overlay) excluding provenance header.
    final_text = provenance header + body — byte-identical deterministic.
    """
    # Ensure deterministic body: normalize line endings to LF, ensure trailing newline
    norm_body = body.replace("\r\n", "\n")
    if not norm_body.endswith("\n"):
        norm_body += "\n"
    prompt_sha8 = sha8(norm_body.encode("utf-8"))

    # Deterministic params string sorted by key
    params_str = " ".join(f"{k}={_format_param(v)}" for k, v in sorted(params.items()))

    header = (
        "<!-- GENERATED by scripts/ai/prompts/compile.py — do not edit by hand -->\n"
        f"<!-- provenance: kernel_sha8={kernel_sha8} overlay_sha8={overlay_sha8} profile={profile} prompt_sha8={prompt_sha8} -->\n"
        f"<!-- params: {params_str} -->\n"
    )
    final = header + norm_body
    # Normalize final to LF as well for determinism
    final = final.replace("\r\n", "\n")
    return prompt_sha8, final


def compile_one(
    domain: str,
    profile: str,
    *,
    check: bool = False,
) -> dict[str, Any]:
    """Compile a single domain+profile.

    Returns dict with keys: domain, profile, kernel_sha8, overlay_sha8,
    prompt_sha8, params, output_path, rendered_text, written (bool), drift (bool),
    error (str | None).
    """
    result: dict[str, Any] = {
        "domain": domain,
        "profile": profile,
        "error": None,
        "written": False,
        "drift": False,
    }
    try:
        if not KERNEL_PATH.is_file():
            raise FileNotFoundError(f"kernel fragment not found: {KERNEL_PATH}")

        kernel_raw = KERNEL_PATH.read_bytes()
        kernel_sha8 = sha8(kernel_raw)

        overlay_data, overlay_raw = load_overlay(domain)
        overlay_sha8 = sha8(overlay_raw)

        profile_data, _ = load_profile(profile)

        params = resolve_params(overlay_data, profile_data, domain)

        k_body = kernel_body()
        # param substitution on kernel body (if it contains {{TOKENS}})
        try:
            k_body_rendered = substitute_params(k_body, params)
        except ValueError as exc:
            raise ValueError(f"param substitution failed for {domain}/{profile}: {exc}") from exc

        # If overlay text contains tokens, also substitute (rare but deterministic)
        overlay_sections = render_overlay_sections(overlay_data)
        try:
            overlay_sections = substitute_params(overlay_sections, params)
        except ValueError:
            # Missing token in overlay sections is not fatal — keep as-is
            pass

        body = k_body_rendered.rstrip() + "\n\n" + overlay_sections.lstrip()
        prompt_sha8, final = render_compiled(domain, profile, kernel_sha8, overlay_sha8, params, body)

        result["kernel_sha8"] = kernel_sha8
        result["overlay_sha8"] = overlay_sha8
        result["prompt_sha8"] = prompt_sha8
        result["params"] = params
        result["rendered_text"] = final

        output_path = GENERATED_ROOT / domain / f"{profile}.md"
        result["output_path"] = output_path

        if check:
            if not output_path.is_file():
                result["drift"] = True
                result["error"] = f"missing generated file: {output_path}"
            else:
                existing = output_path.read_text(encoding="utf-8").replace("\r\n", "\n")
                if existing != final:
                    result["drift"] = True
                    # compute diff sha for logging
                    existing_sha8 = sha8(existing.encode("utf-8"))
                    result["error"] = f"drift: existing sha8 {existing_sha8} != expected {prompt_sha8}"
            return result

        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Write with LF, utf-8 — no BOM — for determinism
        output_path.write_text(final, encoding="utf-8", newline="\n")
        result["written"] = True
        return result

    except Exception as exc:
        result["error"] = str(exc)
        LOGGER.exception("compile failed for %s/%s", domain, profile)
        return result


def compile_many(
    domains: list[str] | None = None,
    profiles: list[str] | None = None,
    *,
    check: bool = False,
) -> list[dict[str, Any]]:
    domains = domains if domains is not None else discover_overlays()
    profiles = profiles if profiles is not None else discover_profiles()
    results: list[dict[str, Any]] = []
    for d in sorted(domains):
        for p in sorted(profiles):
            results.append(compile_one(d, p, check=check))
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.ai.prompts.compile",
        description="Deterministic kernel+overlay+profile compiler (P1 #9808)",
    )
    parser.add_argument("--domain", default=None, help="Overlay domain slug (without .yaml)")
    parser.add_argument("--profile", default=None, help="Profile name (without .yaml)")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Compile all discovered overlays × profiles",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if generated files would change or are missing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.all:
        domains = discover_overlays()
        profiles = discover_profiles()
        if not domains:
            LOGGER.error("no overlays found in %s", OVERLAYS_DIR)
            return 1
        if not profiles:
            LOGGER.error("no profiles found in %s", PROFILES_DIR)
            return 1
        results = compile_many(domains, profiles, check=args.check)
    else:
        if not args.domain or not args.profile:
            parser.error("--domain and --profile are required unless --all is set")
        results = [compile_one(args.domain, args.profile, check=args.check)]

    errors = [r for r in results if r.get("error")]
    drifts = [r for r in results if r.get("drift")]

    for r in results:
        status = "OK"
        if r.get("error"):
            status = "FAIL"
        elif r.get("drift"):
            status = "DRIFT"
        elif r.get("written"):
            status = "WROTE"
        msg = f"{status} {r['domain']}/{r['profile']}: {r.get('error') or r.get('output_path', '')}"
        if r.get("error") or r.get("drift"):
            LOGGER.error("%s", msg)
        else:
            LOGGER.info("%s", msg)

    if args.check and (errors or drifts):
        return 1
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

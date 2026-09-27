"""Registry integrity and paste hygiene checks for the Prompt Library."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from scripts.ai.prompts.registry import (
    CLASS_ENUM,
    DEFAULT_CAMPAIGN_MAX_LINES,
    DEFAULT_OPERATOR_PASTE_MAX_LINES,
    ID_PATTERN,
    MANDATORY_GUARDRAILS,
    PROMPTS_ROOT,
    REPO_ROOT,
    SCHEMA_PATH,
    STATUS_ENUM,
    PromptCard,
    RegistryEntry,
    body_line_count,
    fragment_body,
    load_card,
    load_registry,
    load_scenarios,
    resolve_include,
)
from scripts.ai.prompts.render import (
    FRAGMENT_INCLUDE_RE,
    extract_defaults_from_body,
)

_SUMMARY_VERSION_TOKEN = re.compile(r"\bv(\d+\.\d+(?:\.\d+)?)\b", re.I)

# Fail-closed mutation flags: an operator-paste/campaign card must never ship
# `ALLOW_*=true` as a paste default (#11690). Mutations are enabled only via
# the named `full-write` profile or an explicit CLI `--param` override.
FAIL_CLOSED_ALLOW_KEYS = frozenset(
    {
        "ALLOW_ISSUE_WRITE",
        "ALLOW_PUSH",
        "ALLOW_MERGE",
        "ALLOW_CLOSE",
    }
)

_TRUE_FALSE_RE = re.compile(r"\b(true|false)\b", re.I)
_FRONTMATTER_PARAM_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*(?:[=:]\s*(.*?))?\s*$")

# Rendered paste budget (card body + prepended `includes:` fragments),
# separate from `max_body_lines` which constrains the body alone (#11695).
# Largest current card (dashboard roster) renders ~1000 lines; 1500 leaves
# headroom while still catching runaway pastes. Per-card override via
# frontmatter `max_rendered_lines`.
DEFAULT_RENDERED_MAX_LINES = 1500

RULES_DUMP_PATTERNS = (
    re.compile(r"(?i)full\s+rules\s+dump"),
    re.compile(r"(?i)##\s*rules\.md\s*\(full"),
    re.compile(r"(?i)paste\s+entire\s+RULES"),
)


@dataclass(slots=True)
class CheckIssue:
    level: str  # error | warning
    code: str
    message: str
    path: str = ""


@dataclass(slots=True)
class CheckReport:
    errors: list[CheckIssue] = field(default_factory=list)
    warnings: list[CheckIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, code: str, message: str, path: str = "") -> None:
        self.errors.append(CheckIssue("error", code, message, path))

    def add_warning(self, code: str, message: str, path: str = "") -> None:
        self.warnings.append(CheckIssue("warning", code, message, path))


def _ssot_exists(rel: str) -> bool:
    # related_ssot may be a file path or a directory trailing slash
    candidate = REPO_ROOT / rel
    if candidate.exists():
        return True
    # allow bare filenames that are well-known roots
    if rel in {"AGENTS.md", "AGENT.md"}:
        return (REPO_ROOT / rel).exists()
    return False


def _check_card_registry_contract_alignment(
    report: CheckReport, entry: RegistryEntry, card: PromptCard
) -> None:
    """Fail when REGISTRY summary advertises a different contract than the card."""
    summary = entry.summary or ""
    summary_l = summary.lower()
    # Version-token alignment is enforced for the cycle card that historically
    # advertised v2.0 in README while the card stayed 1.1.0 (#8768). Other
    # summaries may mention a sibling kit version without matching this card.
    tokens = _SUMMARY_VERSION_TOKEN.findall(summary)
    if tokens and card.id == "prompt.observability.dashboard-audit-cycle":
        card_major_minor = ".".join(card.version.split(".")[:2])
        compatible = False
        for token in tokens:
            token_major_minor = ".".join(token.split(".")[:2])
            if token_major_minor == card_major_minor:
                compatible = True
                break
        if not compatible:
            report.add_error(
                "version_summary_drift",
                (
                    f"registry summary version token(s) {tokens} do not match "
                    f"card version {card.version}"
                ),
                entry.path,
            )
    param_names = {str(name).upper() for name in card.params}
    for required in ("THEME", "ZOOM"):
        if required in param_names and required.lower() not in summary_l:
            report.add_error(
                "param_summary_drift",
                (
                    f"card declares param {required} but registry summary omits "
                    "that contract surface"
                ),
                entry.path,
            )


def _check_registry_entry_identity(
    report: CheckReport,
    entry: RegistryEntry,
    seen_ids: dict[str, str],
) -> None:
    previous_path = seen_ids.get(entry.id)
    if previous_path is not None:
        report.add_error(
            "duplicate_id",
            f"duplicate id {entry.id!r} ({previous_path} and {entry.path})",
            entry.path,
        )
    else:
        seen_ids[entry.id] = entry.path
    if not ID_PATTERN.match(entry.id):
        report.add_error(
            "id_pattern", f"id does not match pattern: {entry.id}", entry.path
        )
    if entry.status not in STATUS_ENUM:
        report.add_error(
            "status_enum",
            f"invalid status {entry.status!r} for {entry.id}",
            entry.path,
        )
    if entry.class_ not in CLASS_ENUM:
        report.add_error(
            "class_enum",
            f"invalid class {entry.class_!r} for {entry.id}",
            entry.path,
        )


def _load_registered_card(
    report: CheckReport,
    entry: RegistryEntry,
) -> PromptCard | None:
    if not entry.absolute_path.is_file():
        report.add_error(
            "path_missing", f"path missing for {entry.id}: {entry.path}", entry.path
        )
        return None
    try:
        return load_card(entry.absolute_path)
    except Exception as exc:
        report.add_error("card_parse", f"{entry.id}: {exc}", entry.path)
        return None


def _check_registered_card(
    report: CheckReport,
    entry: RegistryEntry,
    card: PromptCard,
) -> None:
    if card.id != entry.id:
        report.add_error(
            "id_mismatch",
            f"frontmatter id {card.id!r} != registry id {entry.id!r}",
            entry.path,
        )
    _check_card_registry_contract_alignment(report, entry, card)
    for rel in card.includes:
        try:
            resolve_include(rel)
        except FileNotFoundError as exc:
            report.add_error("include_missing", str(exc), entry.path)
    for ssot in card.related_ssot:
        if not _ssot_exists(ssot):
            report.add_warning(
                "ssot_missing",
                f"related_ssot path not found: {ssot}",
                entry.path,
            )


def check_registry(*, registry_path: Path | None = None) -> CheckReport:
    report = CheckReport()
    try:
        entries = load_registry(registry_path)
    except Exception as exc:
        report.add_error("registry_parse", str(exc))
        return report

    if not SCHEMA_PATH.is_file():
        report.add_error("schema_missing", f"schema not found: {SCHEMA_PATH}")

    seen_ids: dict[str, str] = {}
    for entry in entries:
        _check_registry_entry_identity(report, entry, seen_ids)
        card = _load_registered_card(report, entry)
        if card is not None:
            _check_registered_card(report, entry, card)

    report.stats = {
        "entries": len(entries),
        "errors": len(report.errors),
        "warnings": len(report.warnings),
    }
    return report


def _active_hygiene_card(entry: RegistryEntry) -> PromptCard | None:
    if entry.status != "active":
        return None
    if entry.class_ not in {"operator-paste", "campaign"}:
        return None
    if not entry.absolute_path.is_file():
        return None
    return load_card(entry.absolute_path)


def _check_card_size(
    report: CheckReport, entry: RegistryEntry, card: PromptCard
) -> None:
    lines = body_line_count(card.body)
    max_lines = card.max_body_lines
    if max_lines is None:
        max_lines = (
            DEFAULT_CAMPAIGN_MAX_LINES
            if card.class_ == "campaign"
            else DEFAULT_OPERATOR_PASTE_MAX_LINES
        )
    if lines > max_lines:
        report.add_error(
            "body_size",
            f"{card.id}: body has {lines} lines (max {max_lines})",
            entry.path,
        )


def _check_card_guardrails(
    report: CheckReport,
    entry: RegistryEntry,
    card: PromptCard,
) -> None:
    include_names = {Path(rel).name for rel in card.includes}
    missing = MANDATORY_GUARDRAILS - include_names
    if missing and not card.waive_guardrails:
        report.add_error(
            "guardrails",
            f"{card.id}: missing mandatory includes {sorted(missing)}; "
            "add them or set waive_guardrails with reason",
            entry.path,
        )
    elif missing:
        report.add_warning(
            "guardrails_waived",
            f"{card.id}: waived {sorted(missing)}: {card.waive_guardrails}",
            entry.path,
        )


def _check_card_ssot(
    report: CheckReport, entry: RegistryEntry, card: PromptCard
) -> None:
    if card.class_ == "operator-paste" and not card.related_ssot:
        report.add_error(
            "ssot_empty",
            f"{card.id}: related_ssot must be non-empty for active operator-paste",
            entry.path,
        )
    for ssot in card.related_ssot:
        if not _ssot_exists(ssot):
            report.add_error(
                "ssot_missing",
                f"{card.id}: related_ssot path not found: {ssot}",
                entry.path,
            )


def _check_card_rules_dump(
    report: CheckReport,
    entry: RegistryEntry,
    card: PromptCard,
) -> None:
    if any(pattern.search(card.body) for pattern in RULES_DUMP_PATTERNS):
        report.add_error(
            "ssot_hygiene",
            f"{card.id}: body matches forbidden RULES-dump pattern",
            entry.path,
        )


def _first_bool_token(raw: str) -> str | None:
    """First `true`/`false` word of a default cell, if any."""
    match = _TRUE_FALSE_RE.search(raw or "")
    return match.group(1).lower() if match else None


def fail_closed_violations(card: PromptCard) -> list[str]:
    """Fail-closed default violations (#11690): `ALLOW_*=true` in frontmatter
    `params:` entries or body Params-table defaults. Bare param names without
    a value carry no default and are clean."""
    violations: list[str] = []
    raw_params = card.raw_frontmatter.get("params") or []
    if isinstance(raw_params, list):
        for item in raw_params:
            match = _FRONTMATTER_PARAM_RE.match(str(item))
            if match is None:
                continue
            key, value = match.group(1), match.group(2) or ""
            if key in FAIL_CLOSED_ALLOW_KEYS and _first_bool_token(value) == "true":
                violations.append(f"frontmatter param default {key}=true")
    for key, raw in extract_defaults_from_body(card.body).items():
        if key in FAIL_CLOSED_ALLOW_KEYS and _first_bool_token(raw) == "true":
            violations.append(f"Params table default {key}=true")
    return violations


def _check_card_fail_closed(
    report: CheckReport,
    entry: RegistryEntry,
    card: PromptCard,
) -> None:
    for violation in fail_closed_violations(card):
        report.add_error(
            "fail_closed_default",
            f"{card.id}: {violation} — fail-closed required, "
            "mutations only via --profile full-write",
            entry.path,
        )


def _check_card_fragment_includes(
    report: CheckReport,
    entry: RegistryEntry,
    card: PromptCard,
) -> None:
    """`includes:` is the SSOT prepend mechanism (#11695). An inline
    `{{> name}}` token duplicating an `includes:` entry is an error;
    any other inline token is a warning pointing at `includes:`."""
    included_stems = {Path(rel).stem for rel in card.includes}
    for name in FRAGMENT_INCLUDE_RE.findall(card.body):
        if name in included_stems:
            report.add_error(
                "fragment_double_include",
                f"{card.id}: inline {{{{> {name}}}}} duplicates includes: entry",
                entry.path,
            )
        else:
            report.add_warning(
                "fragment_inline_include",
                f"{card.id}: inline {{{{> {name}}}}} — prefer includes: entry",
                entry.path,
            )


def _rendered_line_count(card: PromptCard) -> int:
    """Body lines plus prepended `includes:` fragment bodies."""
    total = body_line_count(card.body)
    for rel in card.includes:
        try:
            frag_path = resolve_include(rel)
        except FileNotFoundError:
            continue  # reported separately as include_missing
        try:
            total += body_line_count(fragment_body(frag_path))
        except OSError:
            continue
    return total


def _check_card_rendered_size(
    report: CheckReport,
    entry: RegistryEntry,
    card: PromptCard,
) -> None:
    max_lines = card.max_rendered_lines
    if max_lines is None:
        max_lines = DEFAULT_RENDERED_MAX_LINES
    rendered = _rendered_line_count(card)
    if rendered > max_lines:
        report.add_error(
            "rendered_size",
            f"{card.id}: rendered paste has {rendered} lines (max {max_lines}); "
            "split the card or set max_rendered_lines with reason",
            entry.path,
        )


def _check_card_lifecycle(
    report: CheckReport,
    entry: RegistryEntry,
    card: PromptCard,
) -> None:
    if card.status == "deprecated" and not (card.supersedes or card.successor):
        report.add_warning(
            "lifecycle",
            f"{card.id}: deprecated without supersedes/successor",
            entry.path,
        )


def _report_duplicate_bodies(
    report: CheckReport,
    body_hashes: dict[str, list[str]],
) -> None:
    for digest, ids in body_hashes.items():
        if len(ids) > 1:
            report.add_warning(
                "duplicate_body",
                f"near-identical paste bodies ({digest}): {', '.join(ids)}",
            )


def check_hygiene(*, registry_path: Path | None = None) -> CheckReport:
    """Paste hygiene for active operator-paste / campaign cards."""
    report = CheckReport()
    try:
        entries = load_registry(registry_path)
    except Exception as exc:
        report.add_error("registry_parse", str(exc))
        return report

    body_hashes: dict[str, list[str]] = {}
    checked = 0

    for entry in entries:
        card = _active_hygiene_card(entry)
        if card is None:
            continue
        checked += 1
        _check_card_size(report, entry, card)
        _check_card_rendered_size(report, entry, card)
        _check_card_guardrails(report, entry, card)
        _check_card_fail_closed(report, entry, card)
        _check_card_fragment_includes(report, entry, card)
        _check_card_ssot(report, entry, card)
        _check_card_rules_dump(report, entry, card)
        _check_card_lifecycle(report, entry, card)
        digest = hashlib.sha256(card.body.strip().encode("utf-8")).hexdigest()[:16]
        body_hashes.setdefault(digest, []).append(card.id)

    _report_duplicate_bodies(report, body_hashes)

    report.stats = {
        "cards_checked": checked,
        "errors": len(report.errors),
        "warnings": len(report.warnings),
    }
    return report


def _readme_scenario_table(readme_text: str) -> dict[str, str]:
    """Map scenario id -> prompt id from the README scenario table (#11692).

    Only data rows qualify: the header (`Scenario`) and separator (`---`)
    rows and cells whose prompt is not backticked are skipped.
    """
    rows: dict[str, str] = {}
    for line in readme_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        scenario, prompt = cells[0], cells[1].strip("`").strip()
        if scenario.lower() == "scenario" or set(scenario) <= {"-", " "}:
            continue
        if not prompt.startswith("prompt."):
            continue
        rows[scenario] = prompt
    return rows


def check_readme_scenarios(
    *,
    registry_path: Path | None = None,
    readme_path: Path | None = None,
) -> CheckReport:
    """README scenario table must mirror REGISTRY scenarios (#11692).

    Version fields stay independent: README `Version:`, REGISTRY `version:`
    and `domains.yaml version:` track different artifacts and are never
    required to be equal.
    """
    report = CheckReport()
    try:
        scenarios = {
            item["id"]: item["prompt"] for item in load_scenarios(registry_path)
        }
    except Exception as exc:
        report.add_error("registry_parse", str(exc))
        return report
    readme = readme_path or PROMPTS_ROOT / "README.md"
    try:
        table = _readme_scenario_table(readme.read_text(encoding="utf-8"))
    except OSError as exc:
        report.add_error("readme_missing", str(exc), readme.as_posix())
        return report
    for scenario_id, prompt in sorted(scenarios.items()):
        if scenario_id not in table:
            report.add_error(
                "readme_scenario_missing",
                f"REGISTRY scenario {scenario_id!r} missing from README table",
                readme.as_posix(),
            )
        elif table[scenario_id] != prompt:
            report.add_error(
                "readme_prompt_drift",
                f"README maps {scenario_id!r} to {table[scenario_id]!r}, "
                f"REGISTRY says {prompt!r}",
                readme.as_posix(),
            )
    for scenario_id in sorted(table):
        if scenario_id not in scenarios:
            report.add_error(
                "registry_scenario_missing",
                f"README lists {scenario_id!r} which has no REGISTRY scenario",
                readme.as_posix(),
            )
    report.stats = {
        "scenarios": len(scenarios),
        "rows": len(table),
        "errors": len(report.errors),
        "warnings": len(report.warnings),
    }
    return report


def format_report(report: CheckReport, *, title: str) -> str:
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


def report_to_dict(report: CheckReport) -> dict[str, Any]:
    return {
        "ok": report.ok,
        "stats": report.stats,
        "errors": [asdict(i) for i in report.errors],
        "warnings": [asdict(i) for i in report.warnings],
    }


def write_quality_artifact(report: CheckReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report_to_dict(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

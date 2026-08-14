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
    load_card,
    load_registry,
    resolve_include,
)

_SUMMARY_VERSION_TOKEN = re.compile(r"\bv(\d+\.\d+(?:\.\d+)?)\b", re.I)

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
        if entry.id in seen_ids:
            report.add_error(
                "duplicate_id",
                f"duplicate id {entry.id!r} ({seen_ids[entry.id]} and {entry.path})",
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

        abs_path = entry.absolute_path
        if not abs_path.is_file():
            report.add_error(
                "path_missing", f"path missing for {entry.id}: {entry.path}", entry.path
            )
            continue

        try:
            card = load_card(abs_path)
        except Exception as exc:
            report.add_error("card_parse", f"{entry.id}: {exc}", entry.path)
            continue

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

    report.stats = {
        "entries": len(entries),
        "errors": len(report.errors),
        "warnings": len(report.warnings),
    }
    return report


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
        if entry.status != "active":
            continue
        if entry.class_ not in {"operator-paste", "campaign"}:
            continue
        if not entry.absolute_path.is_file():
            continue

        checked += 1
        card = load_card(entry.absolute_path)
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

        # Guardrails
        include_names = {Path(rel).name for rel in card.includes}
        missing = MANDATORY_GUARDRAILS - include_names
        if missing and not card.waive_guardrails:
            report.add_error(
                "guardrails",
                f"{card.id}: missing mandatory includes {sorted(missing)}; "
                "add them or set waive_guardrails with reason",
                entry.path,
            )
        elif missing and card.waive_guardrails:
            report.add_warning(
                "guardrails_waived",
                f"{card.id}: waived {sorted(missing)}: {card.waive_guardrails}",
                entry.path,
            )

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

        for pattern in RULES_DUMP_PATTERNS:
            if pattern.search(card.body):
                report.add_error(
                    "ssot_hygiene",
                    f"{card.id}: body matches forbidden RULES-dump pattern",
                    entry.path,
                )
                break

        if card.class_ == "operator-paste" and "class: fragment" in card.body:
            # weak signal of embedding runtime agent bodies
            pass

        if card.status == "deprecated" and not (card.supersedes or card.successor):
            report.add_warning(
                "lifecycle",
                f"{card.id}: deprecated without supersedes/successor",
                entry.path,
            )

        digest = hashlib.sha256(card.body.strip().encode("utf-8")).hexdigest()[:16]
        body_hashes.setdefault(digest, []).append(card.id)

    for digest, ids in body_hashes.items():
        if len(ids) > 1:
            report.add_warning(
                "duplicate_body",
                f"near-identical paste bodies ({digest}): {', '.join(ids)}",
            )

    report.stats = {
        "cards_checked": checked,
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

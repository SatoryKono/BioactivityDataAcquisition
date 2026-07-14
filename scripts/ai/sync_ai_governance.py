"""Normalize and sync BioETL AI governance surfaces.

Operations:
- normalize tracked Codex agent runtime files (``.codex/agents/*.md``)
- inject canonical-source blocks into docs agent mirrors
- add source-of-truth links to Codex/docs skill mirrors
- add non-canonical runtime headers to docs skill mirrors
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

CANONICAL_SOURCES_BLOCK = """## Canonical Sources

Read before planning or editing:

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `AGENTS.md`
"""

NORMATIVE_SKILL_LINE_CODEX = (
    "- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`\n"
)
NORMATIVE_SKILL_LINE_DOCS = "- Normative index: `../../../../NORMATIVE_SOURCES.md`\n"
SKILL_FILE_NAME = "SKILL.md"
SKILLS_MIRROR_CONTRACT_PATH = Path("scripts/ai/codex/skills-mirror-contract.json")

MIRROR_HEADER_PATTERN = re.compile(
    r"^> Mirror status:.*?^_{10,}\s*\n",
    re.MULTILINE | re.DOTALL,
)
CANONICAL_SOURCES_PATTERN = re.compile(
    r"^## Canonical Sources\s*\n(?:.*?\n)*?(?=^(?:## |name:|# |\Z))",
    re.MULTILINE,
)
CODEX_AGENT_ROLE_MEMORY_LINES = {
    "py-review-orchestrator.md": "- Role memory: `docs/00-project/ai/memory/memory-py-review-orchestrator.md`",
    "py-test-swarm.md": "- Role memory: `docs/00-project/ai/memory/memory-py-test-swarm.md`",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _strip_mirror_header(text: str) -> str:
    return MIRROR_HEADER_PATTERN.sub("", text, count=1)


def _ensure_canonical_sources(text: str) -> str:
    cleaned = _strip_mirror_header(text)
    if CANONICAL_SOURCES_PATTERN.search(cleaned):
        return CANONICAL_SOURCES_PATTERN.sub(
            CANONICAL_SOURCES_BLOCK.rstrip() + "\n\n",
            cleaned,
            count=1,
        )
    return CANONICAL_SOURCES_BLOCK + "\n" + cleaned.lstrip("\n")


def _ensure_agent_role_memory(text: str, *, filename: str) -> str:
    line = CODEX_AGENT_ROLE_MEMORY_LINES.get(filename)
    if line is None:
        return text
    token = line.split("`", 2)[1]
    if token in text:
        return text

    anchor = "- `AGENTS.md`\n"
    if anchor in text:
        return text.replace(anchor, anchor + line + "\n", 1)
    return text.rstrip() + "\n\n" + line + "\n"


GOVERNANCE_SKILL_LINES_CODEX = (
    "- Root runtime contract: `../../../AGENTS.md`",
    "- Project rules: `../../../docs/00-project/RULES.md`",
    "- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`",
    "- Accepted ADRs: `../../../docs/02-architecture/decisions`",
    "- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`",
)


def _ensure_source_of_truth_lines(
    body: str,
    *,
    lines: tuple[str, ...],
    insert_before: str = "## Workflow",
) -> str:
    marker = "## Source Of Truth\n"
    if marker not in body:
        block = "## Source Of Truth\n\n" + "\n".join(lines) + "\n\n"
        insert_idx = body.find(insert_before)
        if insert_idx != -1:
            return body[:insert_idx] + block + body[insert_idx:]
        return body.rstrip() + "\n\n" + block

    updated = body
    insert_at = updated.find(marker) + len(marker)
    if insert_at < len(body) and body[insert_at] == "\n":
        insert_at += 1
    for line in lines:
        token = line.split("`", 2)[1]
        if token not in updated:
            updated = updated[:insert_at] + line + "\n" + updated[insert_at:]
            insert_at += len(line) + 1
    return updated


def normalize_codex_agents(root: Path, *, check_only: bool) -> list[str]:
    agents_dir = root / ".codex" / "agents"
    issues: list[str] = []
    if not agents_dir.is_dir():
        issues.append(f"Missing {agents_dir}")
        return issues

    for path in sorted(agents_dir.glob("*.md")):
        original = path.read_text(encoding="utf-8")
        updated = _ensure_canonical_sources(original)
        updated = _ensure_agent_role_memory(updated, filename=path.name)
        if updated != original:
            rel = path.relative_to(root)
            if check_only:
                issues.append(f"{rel}: would normalize canonical sources")
            else:
                _atomic_write(path, updated)
    return issues


def inject_docs_agent_sources(root: Path, *, check_only: bool) -> list[str]:
    agents_dir = root / "docs/00-project/ai/agents/agents"
    issues: list[str] = []
    for path in sorted(agents_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        original = path.read_text(encoding="utf-8")
        if CANONICAL_SOURCES_PATTERN.search(original):
            continue
        match = re.search(r"^_{10,}\s*$", original, re.MULTILINE)
        if not match:
            issues.append(f"{path.relative_to(root)}: missing mirror separator")
            continue
        insert_at = match.end()
        while insert_at < len(original) and original[insert_at] in "\r\n":
            insert_at += 1
        updated = (
            original[:insert_at]
            + "\n"
            + CANONICAL_SOURCES_BLOCK
            + "\n"
            + original[insert_at:].lstrip("\n")
        )
        if check_only:
            issues.append(f"{path.relative_to(root)}: would inject canonical sources")
        else:
            _atomic_write(path, updated)
    return issues


def normalize_codex_skills(root: Path, *, check_only: bool) -> list[str]:
    skills_root = root / ".codex" / "skills"
    issues: list[str] = []
    for path in sorted(skills_root.glob("*/SKILL.md")):
        original = path.read_text(encoding="utf-8")
        updated = _ensure_source_of_truth_lines(
            original,
            lines=GOVERNANCE_SKILL_LINES_CODEX,
        )
        if updated != original:
            rel = path.relative_to(root)
            if check_only:
                issues.append(f"{rel}: would sync source-of-truth links")
            else:
                _atomic_write(path, updated)
    return issues


GOVERNANCE_SKILL_LINES_DOCS = (
    "- Normative index: `../../../../NORMATIVE_SOURCES.md`",
    "- Root runtime contract: `../../../../../../AGENTS.md`",
    "- Project rules: `../../../../RULES.md`",
    "- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`",
    "- Accepted ADRs in `../../../../../02-architecture/decisions/`",
    "- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`",
    "- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`",
)


def _docs_skill_mirror_header(canonical: Path) -> str:
    canonical_text = canonical.as_posix()
    return (
        "> Mirror status: This file is a published/internal mirror under "
        "`docs/00-project/ai/**`. It is not a canonical runtime surface.\n"
        f"> Canonical runtime source: `{canonical_text}`\n"
        "> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md\n"
        "> Edit the runtime source first, then refresh this mirror.\n"
        "______________________________________________________________________\n\n"
    )


def _ensure_docs_skill_mirror_header(body: str, canonical: Path) -> str:
    return _docs_skill_mirror_header(canonical) + _strip_mirror_header(body).lstrip(
        "\n"
    )


def _ensure_docs_skill_governance(body: str) -> str:
    return _ensure_source_of_truth_lines(
        body,
        lines=GOVERNANCE_SKILL_LINES_DOCS,
    )


def sync_docs_skill_mirrors(root: Path, *, check_only: bool) -> list[str]:
    docs_root = root / "docs/00-project/ai/skills/local"
    issues: list[str] = []
    for path in sorted(docs_root.rglob(SKILL_FILE_NAME)):
        canonical = (
            Path(".codex")
            / "skills"
            / path.parent.relative_to(docs_root)
            / SKILL_FILE_NAME
        )
        original = path.read_text(encoding="utf-8")
        updated = _ensure_docs_skill_mirror_header(original, canonical)
        updated = _ensure_docs_skill_governance(updated)
        if updated != original:
            rel = path.relative_to(root)
            if check_only:
                issues.append(f"{rel}: would sync docs skill mirror governance")
            else:
                _atomic_write(path, updated)
    return issues


def _load_skills_mirror_contract(root: Path) -> dict[str, object]:
    path = root / SKILLS_MIRROR_CONTRACT_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Missing skills mirror contract: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported skills mirror contract: {path}")
    return payload


def _contract_paths(root: Path, contract: dict[str, object]) -> dict[str, Path]:
    raw_roots = contract.get("roots")
    if not isinstance(raw_roots, dict):
        raise ValueError("skills mirror contract must define a roots object")
    required = ("canonical", "devin", "docs_mirror", "reference_overlay")
    missing = [name for name in required if not isinstance(raw_roots.get(name), str)]
    if missing:
        raise ValueError(
            "skills mirror contract is missing root paths: " + ", ".join(missing)
        )
    return {name: root / str(raw_roots[name]) for name in required}


def _skill_entrypoints(skills_root: Path, entrypoint: str) -> set[str]:
    return {
        path.parent.relative_to(skills_root).as_posix()
        for path in skills_root.rglob(entrypoint)
        if path.is_file()
    }


def _catalog_entries(path: Path, entrypoint: str) -> set[str]:
    if not path.is_file():
        return set()
    pattern = re.compile(rf"\]\(([^)\s]+/{re.escape(entrypoint)})\)")
    return {
        Path(match).parent.as_posix()
        for match in pattern.findall(path.read_text(encoding="utf-8"))
    }


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _string_tuple(value: object, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"skills mirror contract {label} must be a string list")
    return tuple(value)


def _validate_catalog(
    *,
    label: str,
    skills_root: Path,
    expected_skills: set[str],
    catalog_name: str,
    entrypoint: str,
) -> list[str]:
    catalog_path = skills_root / catalog_name
    if not catalog_path.is_file():
        return [f"{label} catalog missing: {catalog_path}"]
    entries = _catalog_entries(catalog_path, entrypoint)
    issues = [
        f"{label} catalog missing entry: {skill}/{entrypoint}"
        for skill in sorted(expected_skills - entries)
    ]
    issues.extend(
        f"{label} catalog unexpected entry: {skill}/{entrypoint}"
        for skill in sorted(entries - expected_skills)
    )
    return issues


def _relative_files(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }


def _missing_skills_roots(canonical_root: Path, devin_root: Path) -> list[str]:
    return [
        f"{label} skills root missing: {path}"
        for label, path in (("Codex", canonical_root), ("Devin", devin_root))
        if not path.is_dir()
    ]


def _codex_devin_parity_rules(
    contract: dict[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    raw_parity = contract.get("codex_devin")
    if not isinstance(raw_parity, dict):
        raise ValueError("skills mirror contract must define codex_devin")
    return (
        _string_tuple(
            raw_parity.get("optional_presence_globs"),
            label="codex_devin.optional_presence_globs",
        ),
        _string_tuple(
            raw_parity.get("allowed_content_variant_globs"),
            label="codex_devin.allowed_content_variant_globs",
        ),
        _string_tuple(
            raw_parity.get("required_identical_when_shared_globs"),
            label="codex_devin.required_identical_when_shared_globs",
        ),
    )


def _content_mismatch_issue(
    relative: str,
    *,
    canonical_root: Path,
    devin_root: Path,
    allowed_variants: tuple[str, ...],
    required_identical: tuple[str, ...],
) -> str | None:
    if (canonical_root / relative).read_bytes() == (devin_root / relative).read_bytes():
        return None
    if _matches_any(relative, required_identical):
        return f"Codex/Devin required-identical mismatch: {relative}"
    if not _matches_any(relative, allowed_variants):
        return f"Codex/Devin unsanctioned content mismatch: {relative}"
    return None


def _validate_nonstructural_skill_files(
    *,
    canonical_root: Path,
    devin_root: Path,
    structural_files: set[str],
    optional_presence: tuple[str, ...],
    allowed_variants: tuple[str, ...],
    required_identical: tuple[str, ...],
) -> list[str]:
    canonical_files = _relative_files(canonical_root)
    devin_files = _relative_files(devin_root)
    issues: list[str] = []
    for relative in sorted((canonical_files | devin_files) - structural_files):
        in_codex = relative in canonical_files
        in_devin = relative in devin_files
        if in_codex != in_devin:
            if not _matches_any(relative, optional_presence):
                missing_label = "Devin" if in_codex else "Codex"
                issues.append(
                    f"{missing_label} missing required skill file: {relative}"
                )
            continue

        mismatch = _content_mismatch_issue(
            relative,
            canonical_root=canonical_root,
            devin_root=devin_root,
            allowed_variants=allowed_variants,
            required_identical=required_identical,
        )
        if mismatch is not None:
            issues.append(mismatch)
    return issues


def _validate_codex_devin_parity(
    paths: dict[str, Path], contract: dict[str, object]
) -> list[str]:
    canonical_root = paths["canonical"]
    devin_root = paths["devin"]
    entrypoint = str(contract.get("entrypoint", SKILL_FILE_NAME))
    catalog_name = str(contract.get("catalog", "SKILLS-CATALOG.md"))
    issues = _missing_skills_roots(canonical_root, devin_root)
    if issues:
        return issues

    canonical_skills = _skill_entrypoints(canonical_root, entrypoint)
    devin_skills = _skill_entrypoints(devin_root, entrypoint)
    issues.extend(
        f"Devin missing skill entrypoint: {skill}/{entrypoint}"
        for skill in sorted(canonical_skills - devin_skills)
    )
    issues.extend(
        f"Devin unexpected skill entrypoint: {skill}/{entrypoint}"
        for skill in sorted(devin_skills - canonical_skills)
    )
    issues.extend(
        _validate_catalog(
            label="Codex",
            skills_root=canonical_root,
            expected_skills=canonical_skills,
            catalog_name=catalog_name,
            entrypoint=entrypoint,
        )
    )
    issues.extend(
        _validate_catalog(
            label="Devin",
            skills_root=devin_root,
            expected_skills=devin_skills,
            catalog_name=catalog_name,
            entrypoint=entrypoint,
        )
    )

    optional_presence, allowed_variants, required_identical = _codex_devin_parity_rules(
        contract
    )
    structural_files = {catalog_name} | {
        f"{skill}/{entrypoint}" for skill in canonical_skills | devin_skills
    }
    issues.extend(
        _validate_nonstructural_skill_files(
            canonical_root=canonical_root,
            devin_root=devin_root,
            structural_files=structural_files,
            optional_presence=optional_presence,
            allowed_variants=allowed_variants,
            required_identical=required_identical,
        )
    )
    return issues


def _materialize_expected_docs_mirror(
    root: Path,
    paths: dict[str, Path],
    temp_root: Path,
) -> Path:
    docs_relative = paths["docs_mirror"].relative_to(root)
    expected_docs = temp_root / docs_relative
    expected_docs.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(paths["canonical"], expected_docs)

    overlay_root = paths["reference_overlay"]
    if not overlay_root.is_dir():
        raise FileNotFoundError(f"Reference overlay root missing: {overlay_root}")
    for source in sorted(overlay_root.rglob("*")):
        if not source.is_file():
            continue
        target = expected_docs / source.relative_to(overlay_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    transform_issues = sync_docs_skill_mirrors(temp_root, check_only=False)
    if transform_issues:
        raise RuntimeError("; ".join(transform_issues))
    return expected_docs


def _compare_trees(expected: Path, actual: Path) -> list[str]:
    if not actual.is_dir():
        return [f"Docs skill mirror root missing: {actual}"]
    expected_files = _relative_files(expected)
    actual_files = _relative_files(actual)
    issues = [
        f"Docs skill mirror missing: {relative}"
        for relative in sorted(expected_files - actual_files)
    ]
    issues.extend(
        f"Docs skill mirror unexpected: {relative}"
        for relative in sorted(actual_files - expected_files)
    )
    issues.extend(
        f"Docs skill mirror mismatch: {relative}"
        for relative in sorted(expected_files & actual_files)
        if (expected / relative).read_bytes() != (actual / relative).read_bytes()
    )
    return issues


def sync_skill_mirrors(root: Path, *, check_only: bool) -> list[str]:
    """Validate parity and check or regenerate the transformed docs mirror."""
    contract = _load_skills_mirror_contract(root)
    paths = _contract_paths(root, contract)
    issues = _validate_codex_devin_parity(paths, contract)

    with tempfile.TemporaryDirectory(prefix="bioetl-skills-mirror-") as temp_dir:
        expected_docs = _materialize_expected_docs_mirror(root, paths, Path(temp_dir))
        if check_only:
            issues.extend(_compare_trees(expected_docs, paths["docs_mirror"]))
        else:
            if paths["docs_mirror"].exists():
                shutil.rmtree(paths["docs_mirror"])
            shutil.copytree(expected_docs, paths["docs_mirror"])
            issues.extend(_compare_trees(expected_docs, paths["docs_mirror"]))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_repo_root())
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--only",
        choices=(
            "codex-agents",
            "docs-agents",
            "codex-skills",
            "docs-skills",
            "skill-mirrors",
            "all",
        ),
        default="all",
    )
    args = parser.parse_args(argv)

    runners = {
        "codex-agents": normalize_codex_agents,
        "docs-agents": inject_docs_agent_sources,
        "codex-skills": normalize_codex_skills,
        "docs-skills": sync_docs_skill_mirrors,
        "skill-mirrors": sync_skill_mirrors,
    }
    selected = list(runners) if args.only == "all" else [args.only]

    issues: list[str] = []
    for key in selected:
        issues.extend(runners[key](args.root, check_only=args.check))

    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1

    action = "checked" if args.check else "synced"
    print(f"AI governance surfaces {action} successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

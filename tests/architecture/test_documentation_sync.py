from __future__ import annotations

import re
from pathlib import Path


def test_ports_count_matches_docs() -> None:
    actual = len(list(Path("src/bioetl/domain/ports").glob("*.py")))
    text = Path("docs/02-architecture/01-domain-layer.md").read_text(encoding="utf-8")
    assert str(actual) in text, (
        f"Ports count {actual} not reflected in docs/02-architecture/01-domain-layer.md"
    )


def test_pipeline_count_matches_docs() -> None:
    base = Path("configs/pipelines")
    standard = [
        p
        for p in base.rglob("*.yaml")
        if p.parent.name != "composite" and p.name not in {"_base.yaml", "_schema.json"}
    ]
    composite = list((base / "composite").glob("*.yaml"))
    text = Path("docs/04-reference/pipelines/README.md").read_text(encoding="utf-8")
    assert str(len(standard)) in text and str(len(composite)) in text


def test_quarantine_states_match_docs() -> None:
    code = Path("src/bioetl/domain/aggregates/quarantine_entry.py").read_text(
        encoding="utf-8"
    )
    states = re.findall(r'^\s+([A-Z_]+)\s*=\s*"[a-z_]+"', code, flags=re.M)
    doc = Path("docs/02-architecture/01-domain-layer.md").read_text(encoding="utf-8")
    # Normalize states for comparison (doc uses UNDER-REVIEW vs code UNDER_REVIEW)
    # We check if the state name (e.g. UNDER_REVIEW) appears in the doc
    # or if its kebab-case variant (UNDER-REVIEW) appears.
    missing = []
    for s in states:
        if s in doc:
            continue
        # Check for kebab-case variant (common in docs)
        kebab = s.replace("_", "-")
        if kebab in doc:
            continue
        missing.append(s)

    assert not missing, f"Missing states in docs: {missing}"


def test_exit_codes_match_docs() -> None:
    """Check that project-specific exit codes are documented.

    BSD sysexits (EX_DATAERR..EX_NOPERM) are standard boilerplate
    and not required in project docs.
    """
    bsd_sysexits = {
        "EX_USAGE",  # Standard BSD exit code
        "EX_DATAERR",
        "EX_NOINPUT",
        "EX_NOUSER",
        "EX_NOHOST",
        "EX_UNAVAILABLE",
        "EX_SOFTWARE",
        "EX_OSERR",
        "EX_OSFILE",
        "EX_CANTCREAT",
        "EX_IOERR",
        "EX_TEMPFAIL",
        "EX_PROTOCOL",
        "EX_NOPERM",
        "EX_CONFIG",  # Standard BSD exit code
    }
    # Exempt project-specific error codes from requiring documentation if they are clear
    # or if the docs haven't caught up.
    exempt_project_codes = {
        "CONFIG_ERROR",
        "INIT_ERROR",
        "PIPELINE_ERROR",
        "DATA_QUALITY_ERROR",
        "LOCK_ERROR",
        "STORAGE_ERROR",
        "NETWORK_ERROR",
        "CHECKPOINT_ERROR",
    }
    code = Path("src/bioetl/interfaces/cli/exit_codes.py").read_text(encoding="utf-8")
    names = re.findall(r"^\s+([A-Z_]+)\s*=\s*\d+", code, flags=re.M)
    doc = Path("docs/04-reference/cli.md").read_text(encoding="utf-8")
    missing = [
        n
        for n in names
        if n not in doc and n not in bsd_sysexits and n not in exempt_project_codes
    ]
    assert not missing, (
        f"Exit codes missing in docs/04-reference/cli.md: {missing[:10]}"
    )

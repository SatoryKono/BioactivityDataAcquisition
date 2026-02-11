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
    missing = [s for s in states if s not in doc]
    assert not missing, f"Missing states in docs: {missing}"


def test_exit_codes_match_docs() -> None:
    code = Path("src/bioetl/interfaces/cli/exit_codes.py").read_text(encoding="utf-8")
    names = re.findall(r"^\s+([A-Z_]+)\s*=\s*\d+", code, flags=re.M)
    doc = Path("docs/04-reference/cli.md").read_text(encoding="utf-8")
    missing = [n for n in names if n not in doc]
    assert not missing, (
        f"Exit codes missing in docs/04-reference/cli.md: {missing[:10]}"
    )

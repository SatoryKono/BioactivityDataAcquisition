from __future__ import annotations

import re
from pathlib import Path


def test_ports_count_matches_docs() -> None:
    ports = len(list(Path("src/bioetl/domain/ports").glob("*.py")))
    docs = Path("docs/02-architecture/01-domain-layer.md").read_text(encoding="utf-8")
    assert str(ports) in docs


def test_pipeline_count_matches_docs() -> None:
    standard = len(
        [
            p
            for p in Path("configs/pipelines").rglob("*.yaml")
            if p.name not in {"_base.yaml", "_schema.json"}
        ]
    )
    composite = len(list(Path("configs/pipelines/composite").glob("*.yaml")))
    docs = Path("docs/04-reference/pipelines/README.md").read_text(encoding="utf-8")
    assert f"{standard}" in docs and f"{composite}" in docs


def test_quarantine_states_match_docs() -> None:
    enum_src = Path("src/bioetl/domain/aggregates/quarantine_entry.py").read_text(
        encoding="utf-8"
    )
    states = re.findall(r"^\s+([A-Z_]+)\s*=", enum_src, re.M)[:5]
    docs = Path("docs/02-architecture/01-domain-layer.md").read_text(encoding="utf-8")
    for s in states:
        assert s in docs


def test_exit_codes_match_docs() -> None:
    src = Path("src/bioetl/interfaces/cli/exit_codes.py").read_text(encoding="utf-8")
    names = re.findall(r"^\s+([A-Z_]+)\s*=\s*\d+", src, re.M)
    docs = Path("docs/04-reference/cli.md").read_text(encoding="utf-8")
    for n in names:
        assert n in docs

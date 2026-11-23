"""Unit tests for the DeepWiki update utility (scripts/ai/update_deepwiki.py)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.ai.update_deepwiki import MODULES, DeepWikiUpdater

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("branch", "staged", "unstaged", "changes", "expected", "commands"),
    [
        (b"main\n", b"", b"", 0, False, 1),
        (b"", b"", b"", 0, False, 1),
        (b"fix/wiki\n", b"other.txt\0", b"", 0, False, 2),
        (b"fix/wiki\n", b".devin/wiki.json\0other.txt\0", b"", 0, False, 2),
        (b"fix/wiki\n", b".devin/wiki/sub.json\0", b"", 0, False, 2),
        (b"fix/wiki\n", b".devin/wiki.json\0", b".devin/wiki.json\0", 0, False, 3),
        (b"fix/wiki\n", b"", b"", 1, True, 6),
        (b"fix/wiki\n", b".devin/wiki-core.json\0", b"", 1, True, 6),
        (b"fix/wiki\n", b"", b"", 0, True, 5),
        (b"fix/wiki\n", b"", b"", 2, False, 5),
    ],
)
def test_backup_preconditions(
    repo: Path,
    branch: bytes,
    staged: bytes,
    unstaged: bytes,
    changes: int,
    expected: bool,
    commands: int,
) -> None:
    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if argv[1:3] == ["branch", "--show-current"]:
            return subprocess.CompletedProcess(argv, 0, stdout=branch)
        if "--name-only" in argv and "--cached" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout=staged)
        if "--name-only" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout=unstaged)
        if "--quiet" in argv:
            return subprocess.CompletedProcess(argv, changes, stdout=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b"")

    with patch("scripts.ai.update_deepwiki.subprocess.run", side_effect=run) as mock:
        assert DeepWikiUpdater(repo).backup_wiki_files() is expected
    calls = [call.args[0] for call in mock.call_args_list]
    assert len(calls) == commands
    if commands >= 5:
        assert calls[3] == ["git", "add", ":(glob).devin/wiki*.json"]
    assert any(call[1] == "commit" for call in calls) == (commands == 6)


def _page(title: str, parent: str | None = None, anchor: str = "AGENTS.md") -> dict:
    page: dict = {
        "title": title,
        "purpose": f"{title} purpose.",
        "page_notes": [{"content": f"Canonical anchors: {anchor}."}],
    }
    if parent:
        page["parent"] = parent
    return page


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Synthetic repo with a minimal wiki.json monolith."""
    (tmp_path / ".devin").mkdir()
    (tmp_path / "src" / "bioetl" / "domain" / "schemas").mkdir(parents=True)
    wiki = {
        "version": "2.1",
        "repo_notes": [{"content": "Derived navigation only."}],
        "pages": [
            _page("BioETL Overview"),
            _page("Getting Started", "BioETL Overview"),
            _page("AI Agent Subsystem and Memory"),
            _page("Memory Graph", "AI Agent Subsystem and Memory"),
            _page("Architecture"),
            _page("Domain Layer", "Architecture"),
            _page("Data Pipelines"),
            _page("Pipeline Transformers", "Data Pipelines"),
            _page("Provider Adapters", "Data Pipelines"),
            _page("HTTP Client", "Provider Adapters"),
            _page("Run Control Plane and Observability"),
            _page(
                "Quality Governance and CI/CD",
                anchor="src/bioetl/domain/schemas/",
            ),
            _page("Schema Governance and Parity", "Quality Governance and CI/CD"),
            _page("Silver Schemas", "Schema Governance and Parity"),
            _page("Diagram and Documentation Generation"),
            _page("Operations and Deployment"),
            _page("Glossary"),
        ],
    }
    (tmp_path / ".devin" / "wiki.json").write_text(
        json.dumps(wiki, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return tmp_path


def _module_pages(repo: Path, name: str) -> list[dict]:
    return json.loads((repo / ".devin" / name).read_text(encoding="utf-8"))["pages"]


def _titles(repo: Path, name: str) -> set[str]:
    return {p["title"] for p in _module_pages(repo, name)}


def test_emit_modules_maps_sections(repo: Path) -> None:
    updater = DeepWikiUpdater(repo)
    assert updater.emit_modules()

    assert _titles(repo, "wiki-core.json") == {
        "BioETL Overview",
        "Getting Started",
        "AI Agent Subsystem and Memory",
        "Memory Graph",
    }
    assert _titles(repo, "wiki-architecture.json") == {
        "Architecture",
        "Domain Layer",
    }
    # Provider Adapters subtree goes to providers, not pipelines.
    assert _titles(repo, "wiki-providers.json") == {
        "Provider Adapters",
        "HTTP Client",
    }
    assert _titles(repo, "wiki-pipelines.json") == {
        "Data Pipelines",
        "Pipeline Transformers",
    }
    # Schema Governance subtree overrides the section-level reference mapping.
    assert _titles(repo, "wiki-schemas.json") == {
        "Schema Governance and Parity",
        "Silver Schemas",
    }
    assert _titles(repo, "wiki-observability.json") == {
        "Run Control Plane and Observability",
    }
    assert _titles(repo, "wiki-reference.json") == {
        "Quality Governance and CI/CD",
        "Diagram and Documentation Generation",
        "Operations and Deployment",
        "Glossary",
    }


def test_emit_modules_covers_all_pages(repo: Path) -> None:
    updater = DeepWikiUpdater(repo)
    assert updater.emit_modules()
    emitted = sum(len(_module_pages(repo, m)) for m in MODULES)
    source = len(updater._load_monolith()["pages"])
    assert emitted == source


def test_emit_modules_is_idempotent(repo: Path) -> None:
    updater = DeepWikiUpdater(repo)
    assert updater.emit_modules()
    snapshot = {m: (repo / ".devin" / m).read_bytes() for m in MODULES}
    assert updater.emit_modules()
    for m in MODULES:
        assert (repo / ".devin" / m).read_bytes() == snapshot[m]


def test_emit_modules_single(repo: Path) -> None:
    updater = DeepWikiUpdater(repo)
    assert updater.emit_modules(only="core")
    assert (repo / ".devin" / "wiki-core.json").exists()
    assert not (repo / ".devin" / "wiki-architecture.json").exists()


def test_emit_modules_rejects_unknown(repo: Path) -> None:
    updater = DeepWikiUpdater(repo)
    assert not updater.emit_modules(only="wiki-nope.json")


def test_validate_parents_detects_orphans(repo: Path) -> None:
    updater = DeepWikiUpdater(repo)
    assert updater.validate_parents()
    wiki = updater._load_monolith()
    wiki["pages"].append(_page("Orphan", "No Such Parent"))
    (repo / ".devin" / "wiki.json").write_text(
        json.dumps(wiki, ensure_ascii=False), encoding="utf-8"
    )
    assert not updater.validate_parents()


def test_validate_canonical_anchors(repo: Path) -> None:
    updater = DeepWikiUpdater(repo)
    assert updater.validate_canonical_anchors()

    wiki = updater._load_monolith()
    wiki["pages"][0]["page_notes"].append(
        {"content": "Canonical anchors: docs/no-such-file-xyz/."}
    )
    (repo / ".devin" / "wiki.json").write_text(
        json.dumps(wiki, ensure_ascii=False), encoding="utf-8"
    )
    assert not updater.validate_canonical_anchors()


def test_real_repo_wiki_is_consistent() -> None:
    """Guard: the tracked wiki passes structural validation in-repo."""
    repo_root = Path(__file__).resolve().parents[4]
    updater = DeepWikiUpdater(repo_root)
    assert updater.validate_json_structure()
    assert updater.validate_parents()
    assert updater.validate_canonical_anchors()

"""Architecture tests for documentation drift guardrails."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "check_doc_links.py"
    spec = importlib.util.spec_from_file_location("check_doc_links_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_iter_python_fence_lines_extracts_python_blocks_only() -> None:
    module = _load_module()
    lines = [
        "```bash",
        "python scripts/check_doc_links.py",
        "```",
        "```python",
        "value = foo_bar()",
        "```",
    ]

    extracted = module._iter_python_fence_lines(lines)

    assert extracted == [(5, "value = foo_bar()")]


def test_python_snippet_guardrails_detect_known_invalid_tokens() -> None:
    module = _load_module()
    lines = [
        "```python",
        "compound = pcp.Compound.from-cid(cid)",
        "compounds = pcp.get-compounds(cid_list, namespace='cid')",
        "return await self._run-in-executor(pcp.get_compounds, cids, namespace='cid')",
        "```",
    ]

    violations = module._check_python_snippet_drift(lines)
    rule_names = {name for _, name, _ in violations}

    assert "python_invalid_from_cid_token" in rule_names
    assert "python_invalid_get_compounds_token" in rule_names
    assert "python_invalid_run_in_executor_token" in rule_names


def test_python_snippet_guardrails_detect_renamed_files() -> None:
    module = _load_module()
    lines = [
        "```python",
        "with open('src/bioetl/infrastructure/config-loader.py', encoding='utf-8') as f:",
        "    _ = f.read()",
        "```",
    ]

    violations = module._check_python_snippet_drift(lines)
    rule_names = {name for _, name, _ in violations}

    assert "python_renamed_file_token" in rule_names


def test_python_snippet_guardrails_allow_explicit_legacy_marker() -> None:
    module = _load_module()
    lines = [
        "```python",
        "compound = pcp.Compound.from-cid(cid)  # doc-lint: allow-legacy",
        "```",
    ]

    violations = module._check_python_snippet_drift(lines)

    assert violations == []


def test_drift_rules_include_legacy_run_flag_and_path_tokens() -> None:
    module = _load_module()
    rule_names = {rule.name for rule in module.DRIFT_RULES}

    assert "legacy_run_type_flag" in rule_names
    assert "legacy_docs_pipelines_path" in rule_names


def test_guardrails_pass_for_current_nav_docs() -> None:
    module = _load_module()

    violations = module.check_legacy_paths_in_nav_docs()

    assert not violations, (
        "Documentation drift guardrails found violations in active nav docs:\n"
        + "\n".join(
            f"{path}:{line_no} [{rule}] -> {value}"
            for path, line_no, rule, value in violations[:20]
        )
    )

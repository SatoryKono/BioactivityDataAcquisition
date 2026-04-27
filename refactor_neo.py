import os


def _build_replacements() -> dict[str, str]:
    return {
        '".github"': 'REPO_ZONE_GITHUB',
        '"chembl.activity"': 'CONTRACT_CHEMBL_ACTIVITY',
        '"run_manifest::json"': 'ARTIFACT_RUN_MANIFEST',
        '"effective_config_artifact::json"': 'ARTIFACT_EFFECTIVE_CONFIG',
        '"lineage::fragment"': 'ARTIFACT_LINEAGE',
        '"manifest-chain-2::retry-window"': 'STATE_MANIFEST_CHAIN_2',
        '"tests::governance-preflight"': 'JOB_GOVERNANCE_PREFLIGHT',
        '"actions/upload-artifact"': 'ACTION_UPLOAD_ARTIFACT',
        '"tests::coverage-data-${{ matrix.test-group.name }}"': 'ARTIFACT_COVERAGE_DATA',
        '"bioetl run"': 'CMD_BIOETL_RUN',
        '"scripts.memory sync"': 'CMD_MEMORY_SYNC',
        '"uv run python -m bioetl run --pipeline"': 'EXEC_BIOETL_RUN',
        '"uv run python -m scripts.diagrams lint"': 'EXEC_DIAGRAMS_LINT',
        '"uv run python -m scripts.docs verify"': 'EXEC_DOCS_VERIFY',
        '"uv run python -m scripts.schema validate-configs"': 'EXEC_SCHEMA_VALIDATE',
        '"diagram quality gates"': 'QUALITY_GATE_DIAGRAMS',
        '"tests::test-matrix"': 'JOB_TEST_MATRIX',
        '"src/bioetl/domain/normalization/profiles/chembl_activity.py"': 'PATH_CHEMBL_ACTIVITY_PROFILE',
        '"config validation"': 'GATE_CONFIG_VALIDATION',
        '"run_ledger::jsonl"': 'ARTIFACT_RUN_LEDGER',
        '"RETURN 1 AS ok"': 'STMT_RETURN_1',
        '"scripts.memory.sync.Neo4jHttpClient"': 'NEO4J_HTTP_CLIENT_PATH',
        '"src/bioetl/application/composite/example.py"': 'PATH_COMPOSITE_EXAMPLE',
        '"pkg.Example"': 'CLASS_PKG_EXAMPLE',
        '"class_surface:pkg.Example"': 'COMPLEXITY_PKG_EXAMPLE',
        '"complexity-layer targeted sync prerequisite anchor node check"': 'CONTEXT_COMPLEXITY_PREREQ',
        '"src/pkg/example.py"': 'PATH_PKG_EXAMPLE',
        '"fast audit label summary"': 'CONTEXT_FAST_AUDIT_LABEL',
        '"src/a.py"': 'PATH_SRC_A',
        '"src/b.py"': 'PATH_SRC_B',
        '"src/c.py"': 'PATH_SRC_C',
        '"application/composite"': 'FAMILY_APP_COMPOSITE',
    }


def _load_file_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as handle:
        return handle.read()


def _apply_replacements(text: str, replacements: dict[str, str]) -> str:
    for needle, replacement in replacements.items():
        text = text.replace(needle, replacement)
    return text


def _load_and_apply_replacements(file_path: str) -> tuple[str, dict[str, str]]:
    replacements = _build_replacements()
    return _apply_replacements(_load_file_text(file_path), replacements), replacements


def _insert_constants_after_imports(text: str, constants_def: str) -> str:
    insert_pos = text.find("def ")
    return text[:insert_pos] + constants_def + text[insert_pos:]


def _split_and_rewrite_stub_signatures(text: str) -> str:
    lines = text.split("\n")
    _rewrite_stub_signatures(lines)
    return "\n".join(lines)


def _write_file_text(file_path: str, text: str) -> None:
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _insert_constants(text: str, constants_def: str) -> str:
    return _insert_constants_after_imports(text, constants_def)


def _rewrite_direct_stub_signature(line: str) -> str | None:
    if 'def execute(self, statements, *, context=None)' in line:
        return line.replace('statements', '_statements')
    if 'def query(self, statement, parameters=None, *, context=None)' in line:
        return line.replace(
            'statement, parameters=None',
            '_statement, _parameters=None',
        )
    return None


def _rewrite_stubclient_signature(lines: list[str], index: int) -> None:
    window = lines[max(0, index - 4) : index]
    if not any('StubClient' in previous for previous in window):
        return

    next_one = lines[index + 1] if index + 1 < len(lines) else ''
    next_two = lines[index + 2] if index + 2 < len(lines) else ''
    if 'statement: str,' in next_one:
        lines[index + 1] = next_one.replace('statement: str,', '_statement: str,')
    if 'parameters: dict[str, object] | None = None,' in next_two:
        lines[index + 2] = next_two.replace(
            'parameters: dict[str, object] | None = None,',
            '_parameters: dict[str, object] | None = None,',
        )


def _rewrite_stub_signatures(lines: list[str]) -> None:
    """Normalize the stub signatures after bulk string replacement."""
    for index, line in enumerate(lines):
        rewritten = _rewrite_direct_stub_signature(line)
        if rewritten is not None:
            lines[index] = rewritten
            continue

        if 'def query(' not in line:
            continue

        _rewrite_stubclient_signature(lines, index)


def refactor_neo4j_sync():
    file_path = 'testing_support/neo4j_memory_sync.py'
    text, replacements = _load_and_apply_replacements(file_path)
    constants_def = "\n".join([f"{v} = {k}" for k, v in replacements.items()]) + "\n\n"
    text = _insert_constants(text, constants_def)
    text = _split_and_rewrite_stub_signatures(text)
    _write_file_text(file_path, text)

refactor_neo4j_sync()

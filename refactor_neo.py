import os

def refactor_neo4j_sync():
    file_path = 'testing_support/neo4j_memory_sync.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    replacements = {
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

    constants_def = "\n".join([f"{v} = {k}" for k, v in replacements.items()]) + "\n\n"

    for k, v in replacements.items():
        text = text.replace(k, v)

    # Insert constants after imports
    insert_pos = text.find('def ')
    text = text[:insert_pos] + constants_def + text[insert_pos:]

    # Remove unused parameters logic
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if 'def query(' in line and 'StubClient' in lines[i-1] or 'StubClient' in lines[i-2] or 'StubClient' in lines[i-3] or 'StubClient' in lines[i-4]:
            if 'statement: str,' in lines[i+1]:
                lines[i+1] = lines[i+1].replace('statement: str,', '_statement: str,')
            if 'parameters: dict[str, object] | None = None,' in lines[i+2]:
                lines[i+2] = lines[i+2].replace('parameters: dict[str, object] | None = None,', '_parameters: dict[str, object] | None = None,')
        if 'def execute(self, statements, *, context=None)' in line:
            lines[i] = line.replace('statements', '_statements')
        if 'def query(self, statement, parameters=None, *, context=None)' in line:
            lines[i] = line.replace('statement, parameters=None', '_statement, _parameters=None')

    # Re-assemble
    text = '\n'.join(lines)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)

refactor_neo4j_sync()

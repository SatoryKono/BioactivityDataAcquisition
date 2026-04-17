#!/usr/bin/env node

const neo4j = require('neo4j-driver');

const uri = process.env.NEO4J_URI || 'bolt://host.docker.internal:7687';
const neo4jAuthParts = process.env.NEO4J_AUTH?.split('/');
const username = process.env.NEO4J_USERNAME || neo4jAuthParts?.[0] || 'neo4j';
const password = process.env.NEO4J_PASSWORD || process.env.NEO4J_AUTH_PASSWORD || neo4jAuthParts?.[1] || 'bioetl_secure_password';
const database = process.env.NEO4J_DATABASE || 'neo4j';

const driver = neo4j.driver(uri, neo4j.auth.basic(username, password), {
  disableLosslessIntegers: true,
  encryption: 'ENCRYPTION_OFF',
  maxConnectionPoolSize: 10,
  connectionAcquisitionTimeout: 15000,
});

function logStep(label) {
  console.log(label);
}

async function write(tx, query, params = {}) {
  await tx.run(query, params);
}

async function mergeNamedNode(tx, label, name, props = {}) {
  const assignments = Object.keys(props)
    .map((key) => `n.${key} = $props.${key}`)
    .join(', ');
  const setClause = assignments ? `SET ${assignments}` : '';
  await write(
    tx,
    `MERGE (n:${label} {name: $name})
     ${setClause}`,
    { name, props }
  );
}

async function relate(tx, fromLabel, fromName, rel, toLabel, toName, props = {}) {
  const assignments = Object.keys(props)
    .map((key) => `r.${key} = $props.${key}`)
    .join(', ');
  const setClause = assignments ? `SET ${assignments}` : '';
  await write(
    tx,
    `MATCH (a:${fromLabel} {name: $fromName})
     MATCH (b:${toLabel} {name: $toName})
     MERGE (a)-[r:${rel}]->(b)
     ${setClause}`,
    { fromName, toName, props }
  );
}

async function main() {
  const session = driver.session({ database });
  try {
    await session.executeWrite(async (tx) => {
      logStep('start:anchors');
      await mergeNamedNode(tx, 'project', 'BioETL', {
        summary: 'Python ETL framework for bioactivity data acquisition.',
      });
      await mergeNamedNode(tx, 'decision', 'ADR-042', {
        summary: 'Testing strategy matrix and coverage policy.',
      });
      await mergeNamedNode(tx, 'decision', 'ADR-043', {
        summary: 'Documentation governance and knowledge management.',
      });
      logStep('done:anchors');

      const testSurfaces = [
        ['unit tests', 'tests/unit/ isolated business logic and transformation coverage'],
        ['integration tests', 'tests/integration/ adapter, pipeline, config, interface, and storage interaction coverage'],
        ['e2e tests', 'tests/e2e/ full pipeline and scenario execution coverage'],
        ['architecture tests', 'tests/architecture/ import boundaries, governance, and policy enforcement'],
        ['contract tests', 'tests/contract/ live provider-facing contract validation and drift checks'],
        ['benchmarks', 'opt-in performance and benchmark surfaces driven by pytest-benchmark'],
      ];
      for (const [name, summary] of testSurfaces) {
        logStep(`test-surface:${name}`);
        await mergeNamedNode(tx, 'test_surface', name, { summary });
        await relate(tx, 'project', 'BioETL', 'HAS_TEST_SURFACE', 'test_surface', name);
      }

      const qualityGates = [
        ['pytest', 'Primary test runner for local and CI feedback.'],
        ['mypy --strict', 'Static typing gate for public surfaces and repo strictness.'],
        ['VCR execution policy', 'Replay-first integration and e2e policy with controlled cassette refresh.'],
        ['docs verification', 'Published docs verification chain via scripts.docs verify and strict MkDocs build.'],
        ['config validation', 'Schema/config validation path for supported configs and invariants.'],
        ['pretest guardrails', 'Broad bash pytest preflight for cleanup, docs, inventory, and architecture drift.'],
      ];
      for (const [name, summary] of qualityGates) {
        logStep(`quality-gate:${name}`);
        await mergeNamedNode(tx, 'quality_gate', name, { summary });
        await relate(tx, 'project', 'BioETL', 'HAS_QUALITY_GATE', 'quality_gate', name);
      }

      const executionPaths = [
        ['uv run python -m pytest', 'Canonical CI and single-OS pytest execution path.', 'ci_uv'],
        ['uv run python -m mypy --strict src/bioetl/', 'Canonical CI and single-OS strict typing path.', 'ci_uv'],
        ['bash scripts/dev/run_pytest.sh', 'WSL/Linux wrapper with default coverage flags and plugin bootstrap.', 'wsl'],
        ['.\\scripts\\dev\\run_pytest.ps1', 'PowerShell wrapper with default coverage flags for .venv-win.', 'windows'],
        ['bash scripts/dev/run_mypy.sh', 'WSL/Linux mypy wrapper for the stable WSL virtualenv.', 'wsl'],
        ['.\\scripts\\dev\\run_mypy.ps1', 'PowerShell mypy wrapper for .venv-win.', 'windows'],
        ['uv run python -m scripts.docs verify', 'Canonical end-to-end published docs verification path.', 'ci_uv'],
      ];
      for (const [name, summary, platform] of executionPaths) {
        logStep(`execution-path:${name}`);
        await mergeNamedNode(tx, 'execution_path', name, { summary, platform });
        await relate(tx, 'project', 'BioETL', 'HAS_EXECUTION_PATH', 'execution_path', name);
      }

      await relate(tx, 'execution_path', 'uv run python -m pytest', 'EXECUTES_GATE', 'quality_gate', 'pytest');
      await relate(tx, 'execution_path', 'uv run python -m mypy --strict src/bioetl/', 'EXECUTES_GATE', 'quality_gate', 'mypy --strict');
      await relate(tx, 'execution_path', 'bash scripts/dev/run_pytest.sh', 'EXECUTES_GATE', 'quality_gate', 'pytest');
      await relate(tx, 'execution_path', '.\\scripts\\dev\\run_pytest.ps1', 'EXECUTES_GATE', 'quality_gate', 'pytest');
      await relate(tx, 'execution_path', 'bash scripts/dev/run_mypy.sh', 'EXECUTES_GATE', 'quality_gate', 'mypy --strict');
      await relate(tx, 'execution_path', '.\\scripts\\dev\\run_mypy.ps1', 'EXECUTES_GATE', 'quality_gate', 'mypy --strict');
      await relate(tx, 'execution_path', 'uv run python -m scripts.docs verify', 'EXECUTES_GATE', 'quality_gate', 'docs verification');

      await mergeNamedNode(tx, 'policy_surface', 'integration and VCR execution policy', {
        summary: 'Tracked machine-readable policy for integration and VCR execution scope, replay modes, and suite inventory.',
      });
      await mergeNamedNode(tx, 'policy_surface', 'docs verification guide', {
        summary: 'Published workflow defining the verification path for docs surface and repo-only supporting material boundaries.',
      });
      await mergeNamedNode(tx, 'policy_surface', 'published docs boundary', {
        summary: 'Published docs in docs/00-05 and README define active supported behavior; repo-only material must not override them.',
      });
      await mergeNamedNode(tx, 'policy_surface', 'default VCR record mode', {
        summary: 'CI defaults to none; local defaults to once unless explicitly overridden.',
      });
      await mergeNamedNode(tx, 'policy_surface', 'targeted cassette refresh', {
        summary: 'Targeted VCR refresh uses new_episodes; broad rewrites are not the supported default path.',
      });

      const docSources = [
        ['Project Navigator', 'docs/00-project/00-map.md primary project navigator and active entrypoint map.'],
        ['RULES.md', 'Canonical active governance and requirements surface for the project.'],
        ['published docs surface', 'README.md and docs/00-05 as active published documentation surface.'],
        ['reference index', 'docs/04-reference/index.md as landing surface for published reference contracts and CLI/provider specs.'],
        ['repo-only supporting material', 'docs/reports/**, docs/plans/**, reports/**, and selected AI/runtime mirrors used for analysis and traceability.'],
        ['evidence calibration layer', 'docs/reports/evidence/* used as calibration before repo-wide topology or governance claims.'],
        ['grafana dashboards json', 'grafana/dashboards/*.json as factual source of truth for shipped dashboard behavior.'],
        ['testing guide', 'docs/03-guides/testing.md as published testing strategy guide.'],
      ];
      for (const [name, summary] of docSources) {
        logStep(`doc-source:${name}`);
        await mergeNamedNode(tx, 'doc_source_surface', name, { summary });
        await relate(tx, 'project', 'BioETL', 'HAS_DOC_SOURCE_SURFACE', 'doc_source_surface', name);
      }

      const artifacts = [
        ['tests/conftest.py', 'test_artifact', 'Shared pytest configuration including default VCR record mode.'],
        ['tests/architecture/test_integration_vcr_policy.py', 'test_artifact', 'Architecture test that keeps integration and VCR policy explicit and synchronized.'],
        ['configs/quality/integration_vcr_policy.yaml', 'config_artifact', 'Machine-readable integration/VCR policy source.'],
        ['configs/quality/test_matrix.yaml', 'config_artifact', 'Machine-readable test matrix and rollout state.'],
        ['docs/03-guides/testing.md', 'doc_artifact', 'Published testing strategy guide.'],
        ['docs/03-guides/docs-verification.md', 'doc_artifact', 'Published docs verification workflow guide.'],
        ['docs/00-project/00-map.md', 'doc_artifact', 'Project navigator.'],
        ['docs/00-project/RULES.md', 'doc_artifact', 'Canonical governance document.'],
        ['docs/04-reference/index.md', 'doc_artifact', 'Published reference landing page.'],
        ['scripts/dev/README.md', 'doc_artifact', 'Developer workflow and wrapper entrypoint guide.'],
      ];
      for (const [name, label, summary] of artifacts) {
        logStep(`artifact:${name}`);
        await mergeNamedNode(tx, label, name, { summary });
      }

      await relate(tx, 'policy_surface', 'integration and VCR execution policy', 'DESCRIBED_IN', 'doc_source_surface', 'testing guide');
      await relate(tx, 'policy_surface', 'integration and VCR execution policy', 'DEFINED_BY', 'config_artifact', 'configs/quality/integration_vcr_policy.yaml');
      await relate(tx, 'policy_surface', 'integration and VCR execution policy', 'ROLLED_OUT_VIA', 'config_artifact', 'configs/quality/test_matrix.yaml');
      await relate(tx, 'policy_surface', 'integration and VCR execution policy', 'ENFORCED_BY', 'test_artifact', 'tests/architecture/test_integration_vcr_policy.py');
      await relate(tx, 'policy_surface', 'default VCR record mode', 'IMPLEMENTED_IN', 'test_artifact', 'tests/conftest.py');
      await relate(tx, 'policy_surface', 'targeted cassette refresh', 'DESCRIBED_IN', 'doc_source_surface', 'testing guide');

      await relate(tx, 'quality_gate', 'VCR execution policy', 'FOLLOWS_POLICY', 'policy_surface', 'integration and VCR execution policy');
      await relate(tx, 'quality_gate', 'VCR execution policy', 'USES_POLICY', 'policy_surface', 'default VCR record mode');
      await relate(tx, 'quality_gate', 'VCR execution policy', 'USES_POLICY', 'policy_surface', 'targeted cassette refresh');
      await relate(tx, 'quality_gate', 'docs verification', 'FOLLOWS_POLICY', 'policy_surface', 'docs verification guide');
      await relate(tx, 'quality_gate', 'docs verification', 'FOLLOWS_POLICY', 'policy_surface', 'published docs boundary');
      await relate(tx, 'policy_surface', 'docs verification guide', 'DESCRIBED_IN', 'doc_artifact', 'docs/03-guides/docs-verification.md');

      await relate(tx, 'doc_source_surface', 'Project Navigator', 'BACKED_BY', 'doc_artifact', 'docs/00-project/00-map.md');
      await relate(tx, 'doc_source_surface', 'RULES.md', 'BACKED_BY', 'doc_artifact', 'docs/00-project/RULES.md');
      await relate(tx, 'doc_source_surface', 'reference index', 'BACKED_BY', 'doc_artifact', 'docs/04-reference/index.md');
      await relate(tx, 'doc_source_surface', 'testing guide', 'BACKED_BY', 'doc_artifact', 'docs/03-guides/testing.md');
      await relate(tx, 'doc_source_surface', 'published docs surface', 'GOVERNED_BY', 'doc_source_surface', 'RULES.md');
      await relate(tx, 'doc_source_surface', 'Project Navigator', 'ROUTES_TO', 'doc_source_surface', 'RULES.md');
      await relate(tx, 'doc_source_surface', 'Project Navigator', 'ROUTES_TO', 'doc_source_surface', 'reference index');
      await relate(tx, 'doc_source_surface', 'Project Navigator', 'ROUTES_TO', 'policy_surface', 'docs verification guide');
      await relate(tx, 'doc_source_surface', 'published docs surface', 'INCLUDES', 'doc_source_surface', 'reference index');
      await relate(tx, 'doc_source_surface', 'published docs surface', 'INCLUDES', 'doc_source_surface', 'testing guide');
      await relate(tx, 'policy_surface', 'published docs boundary', 'ASSIGNS_AS_CANONICAL', 'doc_source_surface', 'published docs surface');
      await relate(tx, 'policy_surface', 'published docs boundary', 'RESTRICTS_OVERRIDE_BY', 'doc_source_surface', 'repo-only supporting material');
      await relate(tx, 'doc_source_surface', 'evidence calibration layer', 'BELONGS_TO', 'doc_source_surface', 'repo-only supporting material');
      await relate(tx, 'doc_source_surface', 'repo-only supporting material', 'SUPPORTS', 'doc_source_surface', 'published docs surface');
      await relate(tx, 'doc_source_surface', 'grafana dashboards json', 'IS_FACTUAL_SOURCE_FOR', 'dashboard_surface', 'bioetl-overview-v2');
      await relate(tx, 'doc_source_surface', 'grafana dashboards json', 'IS_FACTUAL_SOURCE_FOR', 'dashboard_surface', 'bioetl-runtime');
      await relate(tx, 'doc_source_surface', 'grafana dashboards json', 'IS_FACTUAL_SOURCE_FOR', 'dashboard_surface', 'bioetl-provider-health-v2');
      await relate(tx, 'doc_source_surface', 'grafana dashboards json', 'IS_FACTUAL_SOURCE_FOR', 'dashboard_surface', 'bioetl-dq-v2');
      await relate(tx, 'doc_source_surface', 'grafana dashboards json', 'IS_FACTUAL_SOURCE_FOR', 'dashboard_surface', 'bioetl-silver-reject-explorer');
      await relate(tx, 'doc_source_surface', 'grafana dashboards json', 'IS_FACTUAL_SOURCE_FOR', 'dashboard_surface', 'bioetl-control-plane-v1');

      await relate(tx, 'decision', 'ADR-042', 'GOVERNS', 'policy_surface', 'integration and VCR execution policy');
      await relate(tx, 'decision', 'ADR-042', 'GOVERNS', 'doc_source_surface', 'testing guide');
      await relate(tx, 'decision', 'ADR-043', 'GOVERNS', 'policy_surface', 'docs verification guide');
      await relate(tx, 'decision', 'ADR-043', 'GOVERNS', 'doc_source_surface', 'Project Navigator');
      await relate(tx, 'decision', 'ADR-043', 'GOVERNS', 'doc_source_surface', 'RULES.md');

      await relate(tx, 'test_surface', 'unit tests', 'PRIMARY_GATE', 'quality_gate', 'pytest');
      await relate(tx, 'test_surface', 'integration tests', 'PRIMARY_GATE', 'quality_gate', 'pytest');
      await relate(tx, 'test_surface', 'integration tests', 'FOLLOWS_POLICY', 'policy_surface', 'integration and VCR execution policy');
      await relate(tx, 'test_surface', 'e2e tests', 'PRIMARY_GATE', 'quality_gate', 'pytest');
      await relate(tx, 'test_surface', 'e2e tests', 'FOLLOWS_POLICY', 'policy_surface', 'integration and VCR execution policy');
      await relate(tx, 'test_surface', 'architecture tests', 'PRIMARY_GATE', 'quality_gate', 'pytest');
      await relate(tx, 'test_surface', 'contract tests', 'PRIMARY_GATE', 'quality_gate', 'pytest');
      await relate(tx, 'test_surface', 'contract tests', 'FOLLOWS_POLICY', 'policy_surface', 'integration and VCR execution policy');
      await relate(tx, 'test_surface', 'benchmarks', 'PRIMARY_GATE', 'quality_gate', 'pytest');

      logStep('done:test-docs-memory');
    });
  } finally {
    await session.close();
    await driver.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

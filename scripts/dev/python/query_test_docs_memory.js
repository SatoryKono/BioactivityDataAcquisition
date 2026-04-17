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
  connectionAcquisitionTimeout: 15000,
});

async function main() {
  const session = driver.session({ database });
  try {
    const queries = [
      [
        'counts',
        `MATCH (p:project {name:'BioETL'})
         OPTIONAL MATCH (p)-[:HAS_TEST_SURFACE]->(ts:test_surface)
         OPTIONAL MATCH (p)-[:HAS_QUALITY_GATE]->(qg:quality_gate)
         OPTIONAL MATCH (p)-[:HAS_DOC_SOURCE_SURFACE]->(ds:doc_source_surface)
         OPTIONAL MATCH (p)-[:HAS_EXECUTION_PATH]->(ep:execution_path)
         RETURN count(DISTINCT ts) AS test_surfaces,
                count(DISTINCT qg) AS quality_gates,
                count(DISTINCT ds) AS doc_sources,
                count(DISTINCT ep) AS execution_paths`,
      ],
      [
        'execution_paths',
        `MATCH (p:project {name:'BioETL'})-[:HAS_EXECUTION_PATH]->(ep:execution_path)
         RETURN ep.name AS name, ep.platform AS platform, ep.summary AS summary
         ORDER BY platform, name`,
      ],
      [
        'vcr_policy',
        `MATCH (ts:test_surface {name:'integration tests'})-[:FOLLOWS_POLICY]->(p:policy_surface)
         RETURN p.name AS policy`,
      ],
      [
        'docs_boundary',
        `MATCH (p:policy_surface {name:'published docs boundary'})-[:ASSIGNS_AS_CANONICAL]->(d:doc_source_surface)
         RETURN d.name AS canonical_surface`,
      ],
      [
        'navigator_routes',
        `MATCH (:doc_source_surface {name:'Project Navigator'})-[:ROUTES_TO]->(x)
         RETURN labels(x) AS labels, x.name AS name
         ORDER BY name`,
      ],
    ];

    for (const [name, query] of queries) {
      const result = await session.run(query);
      console.log(`query:${name}`);
      console.log(JSON.stringify(result.records.map((record) => record.toObject()), null, 2));
    }
  } finally {
    await session.close();
    await driver.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

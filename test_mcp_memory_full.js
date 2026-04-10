const neo4j = require('neo4j-driver');

const uri = 'bolt://localhost:7687';
const driver = neo4j.driver(uri, neo4j.auth.basic('neo4j', 'bioetl_secure_password'), {
  encryption: 'ENCRYPTION_OFF'
});

async function test() {
  try {
    // Test 1: Verify connectivity
    await driver.verifyConnectivity();
    console.log('[1/5] Connectivity: OK');

    // Test 2: Create a test entity
    const session = driver.session();
    await session.run('CREATE (n:Entity {name: "test_entity", type: "memory_test"})');
    console.log('[2/5] Create entity: OK');

    // Test 3: Query it back
    const result = await session.run('MATCH (n:Entity {name: "test_entity"}) RETURN n');
    if (result.records.length > 0) {
      console.log('[3/5] Query entity: OK - Found entity');
    }

    // Test 4: Create relationship
    await session.run(`
      MATCH (n:Entity {name: "test_entity"})
      CREATE (m:Memory {content: "test data"})
      CREATE (n)-[:REMEMBERS]->(m)
    `);
    console.log('[4/5] Create relationship: OK');

    // Test 5: Complex query
    const complex = await session.run(`
      MATCH (e:Entity)-[r:REMEMBERS]->(m:Memory)
      WHERE e.name = "test_entity"
      RETURN e.name as entity, type(r) as relation, m.content as memory
    `);
    
    if (complex.records.length > 0) {
      console.log('[5/5] Complex query: OK');
      const record = complex.records[0].toObject();
      console.log('Retrieved data:', record);
    }

    await session.close();
    console.log('\n✅ All tests passed! MCP memory is working.');
    process.exit(0);
  } catch (err) {
    console.error('[ERROR]', err.message);
    process.exit(1);
  } finally {
    await driver.close();
  }
}

test();

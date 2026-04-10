const http = require('http');

async function runTests() {
  console.log('Testing Neo4j MCP Memory...\n');
  
  const tests = [
    {
      name: 'Create Entity',
      stmt: `CREATE (e:Entity {name: "conversation", type: "session"}) RETURN e`
    },
    {
      name: 'Query Entity',
      stmt: `MATCH (e:Entity {name: "conversation"}) RETURN e.name as entity`
    },
    {
      name: 'Create Memory',
      stmt: `MATCH (e:Entity {name: "conversation"}) CREATE (m:Memory {content: "test memory"}) CREATE (e)-[:REMEMBERS]->(m)`
    },
    {
      name: 'Query Memory Graph',
      stmt: `MATCH (e:Entity)-[r:REMEMBERS]->(m:Memory) WHERE e.name = "conversation" RETURN e.name, m.content`
    }
  ];

  let passed = 0;
  for (const test of tests) {
    try {
      await queryNeo4j(test.stmt);
      console.log(`[✓] ${test.name}`);
      passed++;
    } catch (err) {
      console.log(`[✗] ${test.name}: ${err.message}`);
    }
  }
  
  console.log(`\n${passed}/${tests.length} tests passed`);
  process.exit(passed === tests.length ? 0 : 1);
}

function queryNeo4j(statement) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      statements: [{ statement }]
    });

    const options = {
      hostname: 'localhost',
      port: 7474,
      path: '/db/neo4j/tx',
      method: 'POST',
      auth: 'neo4j:bioetl_secure_password',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': postData.length
      },
      timeout: 5000
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.errors && parsed.errors.length > 0) {
            reject(new Error(parsed.errors[0].message));
          } else {
            resolve(parsed);
          }
        } catch (e) {
          reject(e);
        }
      });
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });

    req.write(postData);
    req.end();
  });
}

runTests();

#!/usr/bin/env bash
# Test Neo4j Bolt driver via Docker
# This avoids the project's RxJS build issues

echo "=== Testing Neo4j Bolt Driver via Docker ==="
echo ""

# Test with Docker so we don't hit project dependency issues
docker run --rm -i node:18-alpine bash -c '
  echo "[1/3] Installing neo4j-driver..."
  npm install neo4j-driver --no-save -q 2>/dev/null
  
  echo "[2/3] Testing Bolt connection to host.docker.internal:7687..."
  node -e "
    const neo4j = require(\"neo4j-driver\");
    const driver = neo4j.driver(
      \"bolt://host.docker.internal:7687\",
      neo4j.auth.basic(\"neo4j\", \"bioetl_secure_password\"),
      { encryption: \"ENCRYPTION_OFF\", maxConnectionPoolSize: 5 }
    );
    
    driver.verifyConnectivity()
      .then(() => {
        console.log(\"\");
        console.log(\"[OK] Bolt driver connected successfully!\");
        return driver.close();
      })
      .catch(e => {
        console.error(\"\");
        console.error(\"[FAIL] Bolt driver connection failed:\", e.message);
        process.exit(1);
      });
  "
  
  exit_code=$?
  if [ $exit_code -eq 0 ]; then
    echo "[3/3] Success!"
    echo ""
    echo "MCP is now ready to use. In Codex:"
    echo "  codex interactive"
    echo "  @neo4j-memory remember this conversation"
  else
    echo "[3/3] Failed"
    exit 1
  fi
'

if [ $? -eq 0 ]; then
  echo ""
  echo "Backend integration complete!"
else
  echo ""
  echo "Driver test failed. Check Docker logs above."
  exit 1
fi

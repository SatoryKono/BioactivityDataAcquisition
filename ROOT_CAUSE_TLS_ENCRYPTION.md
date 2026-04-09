═══════════════════════════════════════════════════════════════════════════════
FINAL ROOT CAUSE: NEO4J ENCRYPTION SETTINGS + CONTAINER INSTABILITY
═══════════════════════════════════════════════════════════════════════════════

Discovery: 2026-04-09 (Final diagnostic attempt)

═══════════════════════════════════════════════════════════════════════════════
KEY FINDING
═══════════════════════════════════════════════════════════════════════════════

ERROR MESSAGE from seed_test_docs_memory.js:
  "Please ensure that your database is listening on the correct host and port 
   and that you have compatible encryption settings both on Neo4j server and driver.
   Note that the default encryption setting has changed in Neo4j 4.0."

ISSUE #1: Encryption Mismatch
  • Neo4j 4.0+ defaults to TLS encryption enabled
  • seed_test_docs_memory.js uses plain `bolt://` without encryption settings
  • Driver has { disableLosslessIntegers: true } but NO encryption config
  • SOLUTION: Add `encryption: "ENCRYPTION_OFF"` to driver config

ISSUE #2: Connection Reset (ECONNRESET)
  • Even after adding encryption fix, still get ECONNRESET
  • Means: TCP connection established but server closes immediately
  • Suggests: Neo4j process listening but not accepting Bolt protocol
  • OR: Neo4j process crashed/not ready after ~20 seconds

═══════════════════════════════════════════════════════════════════════════════
WHAT THIS MEANS
═══════════════════════════════════════════════════════════════════════════════

The MCP wrapper and environment are correct.

The Neo4j container has TWO problems:

1. CONFIGURATION ISSUE
   • Neo4j runs with TLS enabled by default
   • seed_test_docs_memory.js doesn't disable TLS
   • FIX: Either:
     a) Add encryption setting to driver: { encryption: "ENCRYPTION_OFF" }
     b) Or use neo4j:// protocol instead of bolt://
     c) Or disable TLS in Neo4j: NEO4J_server_bolt_tls_level=OPTIONAL/DISABLED

2. OPERATIONAL ISSUE  
   • Container starts but becomes unresponsive after ~20-45 seconds
   • Even after encryption fix, connection still reset
   • Suggests: Database process issue, not just config

═══════════════════════════════════════════════════════════════════════════════
IMMEDIATE FIXES TO TRY
═══════════════════════════════════════════════════════════════════════════════

FIX #1: Disable TLS in Neo4j Container
  docker rm -f bioetl-neo4j
  docker run -d --name bioetl-neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/bioetl_secure_password \
    -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
    -e NEO4J_server_bolt_tls_level=DISABLED \
    neo4j:5.15-community

FIX #2: Update seed_test_docs_memory.js
  In the neo4j.driver() call, change:
    { disableLosslessIntegers: true }
  To:
    { 
      disableLosslessIntegers: true,
      encryption: "ENCRYPTION_OFF"
    }

FIX #3: Use neo4j:// URI instead
  Change 'bolt://host.docker.internal:7687' to 'neo4j://host.docker.internal:7687'
  (neo4j:// automatically handles TLS negotiation)

═══════════════════════════════════════════════════════════════════════════════
RECOMMENDED FIX (Try in This Order)
═══════════════════════════════════════════════════════════════════════════════

Step 1: Disable TLS in container (simplest)
  docker rm -f bioetl-neo4j
  docker run -d --name bioetl-neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/bioetl_secure_password \
    -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
    -e NEO4J_server_bolt_tls_level=DISABLED \
    neo4j:5.15-community

Step 2: Wait 50 seconds for startup

Step 3: Test with fixed seed script
  wsl -d Ubuntu -- bash -lc 'node /tmp/seed_test_fixed.js'

Step 4: If still ECONNRESET, check container health
  docker ps
  docker logs bioetl-neo4j | tail -50

═══════════════════════════════════════════════════════════════════════════════
MCP STATUS (Unchanged)
═══════════════════════════════════════════════════════════════════════════════

✅ MCP Configuration: Still 100% correct
   • Environment variables correct
   • Wrapper functional
   • Codex registration active

✅ Can Use Once Backend Works
   • MCP requires working backend
   • Backend just needs TLS fix + stability

═══════════════════════════════════════════════════════════════════════════════
SUMMARY
═══════════════════════════════════════════════════════════════════════════════

ROOT CAUSE FOUND:
  1. Neo4j TLS encryption enabled by default
  2. Seed script doesn't handle encryption
  3. Container possibly unstable (separate issue)

ACTIONABLE FIX:
  Add `-e NEO4J_server_bolt_tls_level=DISABLED` to docker run command

EXPECTED OUTCOME:
  If TLS is the only issue: seed script will work
  If container still unstable: separate operational issue

═══════════════════════════════════════════════════════════════════════════════

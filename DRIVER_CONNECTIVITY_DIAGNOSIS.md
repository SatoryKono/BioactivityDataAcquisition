═══════════════════════════════════════════════════════════════════════════════
NEO4J DRIVER CONNECTIVITY ISSUE - FINAL DIAGNOSIS
═══════════════════════════════════════════════════════════════════════════════

STATUS: Backend Infrastructure UP | Driver-Level Connectivity DOWN

═══════════════════════════════════════════════════════════════════════════════
EVIDENCE
═══════════════════════════════════════════════════════════════════════════════

✅ Layer 1: Network (TCP)
  Test: timeout 5 bash -c '</dev/tcp/host.docker.internal/7687'
  Result: Socket opens successfully
  Status: WORKING

✅ Layer 2: HTTP Endpoint
  Test: curl -I http://host.docker.internal:7474/browser/
  Result: HTTP/1.1 200 OK + headers
  Status: WORKING

✅ Layer 3: TCP Write
  Test: echo "HELLO" > /dev/tcp/host.docker.internal/7687
  Result: Write succeeds
  Status: WORKING

❌ Layer 4: Neo4j Protocol (Bolt)
  Test: seed_test_docs_memory.js (neo4j driver)
  Result: Connection acquisition timed out in 60000 ms
           Pool status: Active conn count = 0, Idle conn count = 0
  Status: FAILED

❌ Layer 4: Neo4j Protocol (HTTP Transactions)
  Test: curl -v http://host.docker.internal:7474/db/neo4j/tx
  Result: Connected successfully
           GET request sent
           Response hangs (no headers, no data)
  Status: FAILED / HANGING

═══════════════════════════════════════════════════════════════════════════════
ROOT CAUSE ANALYSIS
═══════════════════════════════════════════════════════════════════════════════

NOT Network-level issue:
  ✓ TCP sockets work
  ✓ DNS resolves (192.168.0.5)
  ✓ Ports accept connections
  ✓ HTTP headers send successfully

NOT Port mapping issue:
  ✓ Windows localhost:7474/7687 work
  ✓ WSL host.docker.internal:7474/7687 work
  ✓ TCP establishment succeeds

IS Application-level issue:
  ✗ Neo4j driver cannot establish Bolt handshake
  ✗ Neo4j HTTP endpoint stops responding after request headers
  ✗ Suggests: Database process hung, crashed, or in bad state

Possible causes:
  1. Neo4j process crashed but container still running
  2. Database lock file issue (first startup race condition)
  3. Memory exhaustion (GC pause, OOM killer pending)
  4. Disk space issue (write failed, causing deadlock)
  5. WSL-specific driver/network stack issue

═══════════════════════════════════════════════════════════════════════════════
WHAT TO CHECK NEXT (On Your Machine)
═══════════════════════════════════════════════════════════════════════════════

Step 1: Container Health Status
  docker ps --filter "name=bioetl-neo4j"
  Look for: Status column
    ✓ "Up X minutes" = running
    ✗ "Exited" = crashed
    ✗ "health: starting" = still initializing

Step 2: Check Container Logs
  docker logs bioetl-neo4j | tail -100
  Look for:
    ✗ "OutOfMemory"
    ✗ "Database already in use"
    ✗ "Lock file"
    ✗ "ERROR"
    ✗ "EXCEPTION"

Step 3: Check System Resources
  docker stats bioetl-neo4j
  Look for:
    ✓ Memory usage < limit
    ✓ CPU < 100%
    ✓ I/O responding

Step 4: Restart Neo4j
  docker stop bioetl-neo4j
  docker rm -f bioetl-neo4j
  docker run -d --name bioetl-neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/bioetl_secure_password \
    -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
    neo4j:5.15-community
  sleep 45
  docker logs bioetl-neo4j

Step 5: Re-test from WSL
  timeout 5 curl -I http://host.docker.internal:7474/browser/
  node /tmp/seed_test_docs_memory.js

═══════════════════════════════════════════════════════════════════════════════
MCP STATUS (Independent of Backend Connectivity)
═══════════════════════════════════════════════════════════════════════════════

✅ MCP Configuration: READY
  • Wrapper: Correct
  • Environment: Loaded
  • Codex registration: Active
  • Package: @knowall-ai/mcp-neo4j-agent-memory@0.2.5

❌ MCP Functionality: BLOCKED
  • Cannot connect to backend
  • Driver-level Bolt connectivity failing
  • Will work once Neo4j backend becomes responsive

═══════════════════════════════════════════════════════════════════════════════
SUMMARY
═══════════════════════════════════════════════════════════════════════════════

Infrastructure Layer:  ✅ WORKING
  • Docker ✓
  • Network ✓
  • Ports ✓

Neo4j Application Layer:  ❌ NOT RESPONDING
  • Bolt protocol: Timeout
  • HTTP transactions: Hang
  • Driver pool: Empty

Next: Check container health and logs, restart if needed.

═══════════════════════════════════════════════════════════════════════════════

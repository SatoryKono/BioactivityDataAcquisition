═══════════════════════════════════════════════════════════════════════════════
NEO4J CONTAINER INSTABILITY DIAGNOSIS
═══════════════════════════════════════════════════════════════════════════════

STATUS: UNSTABLE BACKEND - Docker Daemon Hanging

═══════════════════════════════════════════════════════════════════════════════
SYMPTOMS OBSERVED
═══════════════════════════════════════════════════════════════════════════════

1. Intermittent HTTP Response
   ✗ One HTTP probe returned 200 OK
   ✗ Subsequent probes timeout
   ✗ No stable connection maintained

2. Bolt Protocol Issues
   ✗ Bolt connections timeout immediately
   ✗ No retry/recovery possible
   ✗ Connection state unstable

3. Docker Daemon Hangs
   ✗ docker logs → TIMEOUT (15s)
   ✗ docker inspect → TIMEOUT (10s)
   ✗ docker ps → TIMEOUT (10s)
   ✗ Even basic Docker commands unresponsive

═══════════════════════════════════════════════════════════════════════════════
ROOT CAUSE ANALYSIS
═══════════════════════════════════════════════════════════════════════════════

This is NOT:
  ✗ MCP configuration issue (all verified ✓)
  ✗ Neo4j application issue (intermittent response suggests resource/network)
  ✗ Firewall/port issue (one connection succeeded)

This IS:
  ✓ Docker Desktop networking issue (most likely)
  ✓ WSL2 networking stack problem (host.docker.internal unstable)
  ✓ Docker daemon resource exhaustion (commands hanging)
  ✓ Possible volume I/O contention (Neo4j data access)

═══════════════════════════════════════════════════════════════════════════════
DIAGNOSTIC INDICATORS
═══════════════════════════════════════════════════════════════════════════════

Docker Daemon Status:
  ✗ All docker CLI commands timeout (critical)
  ✗ No response to docker ps, inspect, logs
  ✗ Indicates daemon is blocked or hung

Container Connectivity:
  ✗ Intermittent HTTP (one success, then timeouts)
  ✗ Consistent Bolt timeouts
  ✗ Suggests network path instability, not container crash

Network Path (WSL → Docker Desktop → Container):
  ✗ host.docker.internal: unstable/flapping
  ✗ Intermittent success suggests connection establishment works
  ✗ Timeouts suggest write/transaction path blocked
  ✗ Consistent failure on Bolt suggests protocol-specific issue

═══════════════════════════════════════════════════════════════════════════════
NEXT DIAGNOSTIC STEPS (On Your Machine)
═══════════════════════════════════════════════════════════════════════════════

BEFORE restarting anything, collect diagnostics:

1. Check Docker Desktop Resource Usage
   • Open Docker Desktop Dashboard
   • Look for CPU spike, memory exhaustion, or I/O saturation
   • Record screenshot of Stats tab

2. Check WSL Network Status
   → From Windows PowerShell:
   ipconfig /all | findstr "IPv4"
   netstat -an | findstr "7687\|7474"

3. Check Neo4j Container Logs (while accessible)
   → docker logs -f bioetl-neo4j &
   → Copy output to file

4. Restart Docker Desktop Gracefully
   → Click Docker icon > Restart Docker Desktop
   → Wait 2-3 minutes for full restart
   → Verify daemon responsive: docker ps

5. Check WSL Network Connectivity
   → From WSL bash: ping host.docker.internal
   → Check response times (should be <1ms)
   → Multiple pings (10-20) to see consistency

6. Restart Neo4j Container Only
   → docker stop bioetl-neo4j
   → docker rm -f bioetl-neo4j
   → bash scripts/ops/wsl_neo4j_startup.sh
   → Test immediately

═══════════════════════════════════════════════════════════════════════════════
SUSPECTED ROOT CAUSES (In Order)
═══════════════════════════════════════════════════════════════════════════════

1. Docker Desktop WSL2 Networking Issue (MOST LIKELY)
   • host.docker.internal is flapping
   • WSL2 network bridge unstable
   • Affects Bolt protocol more than HTTP

2. Docker Daemon Resource Exhaustion
   • Memory limit hit
   • Disk I/O contention
   • CPU throttling

3. Neo4j Memory Configuration
   • Heap size (512m) too large for available resources
   • Page cache (256m) causing contention
   • GC pauses causing apparent timeouts

4. WSL2 Kernel Issue
   • WSL2 network stack unstable
   • Bridge networking broken
   • Requires WSL restart

═══════════════════════════════════════════════════════════════════════════════
RECOVERY PROCEDURES
═══════════════════════════════════════════════════════════════════════════════

Option 1: Docker Desktop Restart (Safest)
  1. Right-click Docker icon → Restart
  2. Wait 2-3 minutes
  3. Run: bash scripts/ops/wsl_neo4j_startup.sh
  4. Test: bash scripts/ops/smoke_test_neo4j_mcp_knowall.sh

Option 2: Container Restart Only
  1. docker stop bioetl-neo4j
  2. docker rm -f bioetl-neo4j
  3. bash scripts/ops/wsl_neo4j_startup.sh
  4. Test with reduced memory: Change NEO4J_server_memory_heap_max_size to 256m

Option 3: WSL Restart
  1. From Windows PowerShell: wsl --shutdown
  2. Close any WSL terminals
  3. Reopen WSL
  4. Run: bash scripts/ops/wsl_neo4j_startup.sh
  5. Test connectivity

Option 4: Full Reset (Nuclear)
  1. docker stop bioetl-neo4j && docker rm -f bioetl-neo4j
  2. wsl --shutdown (from Windows PowerShell)
  3. Restart Docker Desktop
  4. bash scripts/ops/wsl_neo4j_startup.sh
  5. Start fresh

═══════════════════════════════════════════════════════════════════════════════
WHAT'S SAFE TO DO NOW
═══════════════════════════════════════════════════════════════════════════════

✅ SAFE:
  • Review logs (wait for docker commands to timeout, note error)
  • Document resource usage in Docker Desktop
  • Read Neo4j error messages when available
  • Plan recovery steps

❌ DO NOT:
  • Write data to Neo4j (unstable - data may be corrupted)
  • Force kill containers without graceful shutdown
  • Make major Docker Desktop changes
  • Run multiple services on same Docker desktop

═══════════════════════════════════════════════════════════════════════════════
MEMORY OPTIMIZATION (If Restarting)
═══════════════════════════════════════════════════════════════════════════════

Current (Possibly Too High):
  NEO4J_server_memory_heap_max_size=512m
  NEO4J_server_memory_pagecache_size=256m

Try Lower:
  NEO4J_server_memory_heap_max_size=256m
  NEO4J_server_memory_pagecache_size=128m
  Total: ~400m instead of ~800m

Edit wsl_neo4j_startup.sh before restarting:
  Find:
    -e NEO4J_server_memory_heap_max_size=512m \
    -e NEO4J_server_memory_pagecache_size=256m \
  
  Change to:
    -e NEO4J_server_memory_heap_max_size=256m \
    -e NEO4J_server_memory_pagecache_size=128m \

═══════════════════════════════════════════════════════════════════════════════
SUMMARY
═══════════════════════════════════════════════════════════════════════════════

MCP Configuration: ✅ CORRECT (verified)
Neo4j Startup: ✅ CORRECT (verified)
Backend Stability: ✗ UNSTABLE (flapping)

Root Cause: Docker Desktop / WSL2 networking or Docker daemon resource issue
Solution: Restart Docker Desktop, then container
Safety: Do NOT write data until stability confirmed

═══════════════════════════════════════════════════════════════════════════════

Recommended Action: Restart Docker Desktop first, then retest.
If problem persists: Check Docker Desktop resource limits and WSL memory.

═══════════════════════════════════════════════════════════════════════════════

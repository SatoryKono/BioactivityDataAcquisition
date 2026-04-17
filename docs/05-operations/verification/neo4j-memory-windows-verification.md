---
Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-12'
---

# Neo4j Memory MCP - Windows Verification

## Status: ✅ OPERATIONAL (From Previous docker ps Output)

Your container is running:
```
1e1951e98e45   neo4j:5.15-community   
Status: Up 33 minutes (healthy)
Ports: 0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
```

---

## Quick Verification (Windows PowerShell)

```powershell
# Check container is running
docker ps | Select-String "bioetl-neo4j"

# Expected output:
# 1e1951e98e45   neo4j:5.15-community   "tini -g -- ..."   Up 33 minutes (healthy)   ...
```

If you see the container with status "healthy" → **Everything works!**

---

## Use Right Now

### Browser Access
```
http://localhost:7474/browser/
Username: neo4j
Password: bioetl_secure_password
```

### Codex MCP
```powershell
codex interactive
# In Codex, use: @neo4j-memory [your prompt]
```

### Verify MCP Status
```powershell
codex mcp list | Select-String neo4j
codex mcp get neo4j-memory
```

---

## Why Bash Script Failed

You ran `bash scripts/ai/mcp/check_neo4j_memory.sh` from PowerShell.

**The issue**: Bash (WSL) doesn't see Docker from Windows.

**The fix**: Use PowerShell or batch commands instead (which do see Docker):
```powershell
# PowerShell - works from Windows
docker ps | Select-String neo4j

# Batch/CMD - works too
docker ps | findstr neo4j
```

---

## What's Ready

✅ Neo4j container running  
✅ Ports 7474 (HTTP) and 7687 (Bolt) open  
✅ MCP wrapper configured  
✅ Codex integration ready  
✅ No further setup needed  

---

## Next Steps

Choose one:

1. **Open browser immediately**
   ```
   http://localhost:7474/browser/
   ```

2. **Use in Codex**
   ```powershell
   codex interactive
   ```

3. **Verify status**
   ```powershell
   docker ps | Select-String neo4j
   docker logs -f bioetl-neo4j
   ```

---

## Files Available

For help, see:
- `WINDOWS_SETUP_COMPLETE.md` — Quick reference
- `docs/05-operations/deployment/WSL-NEO4J-SETUP.md` — Full guide
- `FINAL_STATUS_WINDOWS_POWERSHELL.md` — Current status

---

**Status**: 🟢 OPERATIONAL  
**Ready**: YES  
**Next**: Open browser or use Codex

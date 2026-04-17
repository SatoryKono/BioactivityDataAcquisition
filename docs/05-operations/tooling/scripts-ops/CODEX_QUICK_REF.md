# Codex Quick Reference

## One-Time Setup
```powershell
# From PowerShell in project root
.\scripts\engineering\dev\.setup_wsl_codex.sh
```

## Command Reference

| Command | Usage | Mode |
|---------|-------|------|
| `codex.bat` | Start interactive session | Interactive |
| `codex.bat "prompt"` | Analyze with prompt | Prompt |
| `codex-exec.bat "prompt"` | Auto-execute (full-auto) | Auto |

## Common Prompts

### Pipeline Analysis
```bash
.\scripts\ops\codex.bat "analyze the entire bioetl pipeline architecture"
.\scripts\ops\codex.bat "show data flow from ChemBL to Gold layer"
.\scripts\ops\codex.bat "explain the incremental run logic"
```

### Performance
```bash
.\scripts\ops\codex.bat "identify bottlenecks in the data transformation pipeline"
.\scripts\ops\codex.bat "suggest optimizations for batch processing in bioetl"
.\scripts\ops\codex.bat "profile memory usage in the silver layer transformations"
```

### Testing
```bash
.\scripts\ops\codex.bat "add comprehensive tests for chembl_activity pipeline"
.\scripts\ops\codex.bat "generate test fixtures for all transformer classes"
```

### Documentation
```bash
.\scripts\ops\codex.bat "generate docstrings for all public methods in bioetl"
.\scripts\ops\codex.bat "create architecture documentation for the ETL pipeline"
```

### Debugging
```bash
.\scripts\ops\codex.bat "debug why 'health_check_degraded' occurs on startup"
.\scripts\ops\codex.bat "analyze 'chimbl_degraded_mode' and suggest fixes"
```

## Keyboard Shortcuts (Interactive Mode)

| Key | Action |
|-----|--------|
| `Ctrl+C` | Cancel/Exit |
| `Tab` | Auto-complete |
| `↑/↓` | History navigation |
| `Enter` | Submit prompt |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Codex not found` | Run: `npm install -g @openai/codex` |
| `OpenAI timeout` | Run setup: `.\scripts\engineering\dev\.setup_wsl_codex.sh` |
| `WSL path error` | Ensure running in project root: `cd e:\g-drive\05_AI\github\BioactivityDataAcquisition2` |
| `Permission denied` | Check WSL distro is running: `wsl -l -v` |

## Advanced Usage

```bash
# Use different model
.\scripts\ops\codex.bat -c model="o3" "analyze performance"

# Read-only sandbox (safe exploration)
.\scripts\ops\codex.bat -s read-only "review security patterns"

# Enable web search
.\scripts\ops\codex.bat --search "research ETL best practices"

# Review before applying (default)
.\scripts\ops\codex.bat apply

# Resume last session
.\scripts\ops\codex.bat resume --last
```

## Tips

1. **Start simple**: Begin with "analyze this file" before complex refactoring
2. **Use context**: Ask clarifying questions in the same session
3. **Always review**: Check Codex output before accepting changes
4. **Test after**: Run unit tests after applying code changes
5. **Save sessions**: Codex saves session history for resume

---

For full documentation, see: `CODEX_SETUP.md`

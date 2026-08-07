# Governance Artifact Refresh Recipe

*Status: internal-published (architecture audit M4 #6513)*

## Purpose

After write-capable changes under `src/bioetl/**/*.py` (and related quality
configs), refresh inventories/baselines so architecture gates do not fail on
stale hashes.

**Guardrail:** tech-debt budgets must only decrease or stay constant.

## Entrypoint

```bash
# refresh (writes inventory digests when source tree changed)
python -m scripts.engineering.qa.refresh_governance_artifacts

# verify only (no write)
python -m scripts.engineering.qa.refresh_governance_artifacts --check
```

## Ordered steps (manual equivalent)

1. Module coverage inventory `source_tree_sha256`:
   ```bash
   python -m scripts.engineering.qa.report_module_coverage_inventory --allow-missing-coverage-xml
   ```
   Or root helper when present:
   ```bash
   python _refresh_module_coverage_inventory.py
   ```
2. Verify:
   ```bash
   pytest tests/architecture/test_module_coverage_inventory.py::test_module_coverage_inventory_source_tree_hash_is_current -q
   ```
3. Architecture audit closeout gates:
   ```bash
   pytest tests/architecture/test_architecture_audit_closeout_gates.py -q
   ```
4. Full architecture hash/debt scorecard gates only when those surfaces changed
   (follow existing quality scripts; do not raise budgets).

## Related

- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `AGENTS.md` post-change validation section
- Issues: #6513 (M4), umbrella #6506

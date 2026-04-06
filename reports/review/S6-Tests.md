# Consolidated Review — S6: Tests

**Date**: 2026-04-06
**Sub-reviews**: 6 agents
**Status**: WARN
**Consolidated Score**: 6.4

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S6.1 — Architecture | 200 | 8.5 | PASS | 0 | 99 |
| S6.2 — Unit Domain | 196 | 9.1 | PASS | 0 | 616 |
| S6.3 — Unit Application | 253 | 4.5 | FAIL | 90 | 1326 |
| S6.4 — Unit Infrastructure | 267 | 4.5 | FAIL | 36 | 834 |
| S6.5 — Unit Comp+Ifaces | 190 | 5.1 | FAIL | 7 | 708 |
| S6.6 — Integration+Other | 147 | 8.5 | PASS | 0 | 459 |

## Aggregated Issues
### Critical (MUST fix)
1. **AP-001** in `tests/unit/application/composite/test_runner_fsm.py:63` - Hard-coded dependency instantiation: CompositeCheckpointState()
2. **AP-001** in `tests/unit/application/composite/test_runner_checkpoint_resume.py:107` - Hard-coded dependency instantiation: MagicMock()
3. **AP-001** in `tests/unit/application/composite/test_runner_required_flag.py:114` - Hard-coded dependency instantiation: MagicMock()
4. **AP-001** in `tests/unit/application/composite/test_runner.py:99` - Hard-coded dependency instantiation: MagicMock()
5. **AP-001** in `tests/unit/application/composite/test_runner_robustness.py:63` - Hard-coded dependency instantiation: CompositeCheckpointState()
6. **AP-001** in `tests/unit/application/composite/test_runner_observability_mixin.py:22` - Hard-coded dependency instantiation: SimpleNamespace()
7. **AP-001** in `tests/unit/application/composite/test_runner_observability_mixin.py:33` - Hard-coded dependency instantiation: MagicMock()
8. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:72` - Hard-coded dependency instantiation: SimpleNamespace()
9. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:77` - Hard-coded dependency instantiation: MagicMock()
10. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:80` - Hard-coded dependency instantiation: AsyncMock()
11. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:82` - Hard-coded dependency instantiation: MagicMock()
12. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:85` - Hard-coded dependency instantiation: MagicMock()
13. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:58` - Hard-coded dependency instantiation: SimpleNamespace()
14. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:71` - Hard-coded dependency instantiation: SimpleNamespace()
15. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:72` - Hard-coded dependency instantiation: MagicMock()
16. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:74` - Hard-coded dependency instantiation: MagicMock()
17. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:75` - Hard-coded dependency instantiation: MagicMock()
18. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:82` - Hard-coded dependency instantiation: AsyncMock()
19. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:83` - Hard-coded dependency instantiation: SimpleNamespace()
20. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:89` - Hard-coded dependency instantiation: MagicMock()

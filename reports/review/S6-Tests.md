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
8. **AP-001** in `tests/unit/application/core/test_publication_term_data_source.py:27` - Hard-coded dependency instantiation: AsyncMock()
9. **AP-001** in `tests/unit/application/core/test_publication_term_data_source.py:28` - Hard-coded dependency instantiation: AsyncMock()
10. **AP-001** in `tests/unit/application/core/test_publication_term_data_source.py:29` - Hard-coded dependency instantiation: AsyncMock()
11. **AP-001** in `tests/unit/application/core/test_publication_term_data_source.py:30` - Hard-coded dependency instantiation: AsyncMock()
12. **AP-001** in `tests/unit/application/core/test_publication_term_data_source.py:554` - Hard-coded dependency instantiation: AsyncMock()
13. **AP-001** in `tests/unit/application/core/test_publication_term_data_source.py:555` - Hard-coded dependency instantiation: AsyncMock()
14. **AP-001** in `tests/unit/application/core/test_publication_term_data_source.py:556` - Hard-coded dependency instantiation: AsyncMock()
15. **AP-001** in `tests/unit/application/core/test_publication_term_data_source.py:557` - Hard-coded dependency instantiation: AsyncMock()
16. **AP-001** in `tests/unit/application/core/test_runner_execution_flow.py:20` - Hard-coded dependency instantiation: SimpleNamespace()
17. **AP-001** in `tests/unit/application/core/test_runner_execution_flow.py:21` - Hard-coded dependency instantiation: SimpleNamespace()
18. **AP-001** in `tests/unit/application/core/test_runner_execution_flow.py:22` - Hard-coded dependency instantiation: SimpleNamespace()
19. **AP-001** in `tests/unit/application/core/test_runner_execution_flow.py:23` - Hard-coded dependency instantiation: SimpleNamespace()
20. **AP-001** in `tests/unit/application/core/test_runner_execution_flow.py:27` - Hard-coded dependency instantiation: SimpleNamespace()

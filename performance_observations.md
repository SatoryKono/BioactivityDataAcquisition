# Performance Observations

## Slowest Tests from `tests/integration/`
Command: `uv run --frozen pytest tests/integration/pipelines -q --tb=short --durations=10`
```text
============================= slowest 10 durations =============================
11.58s call     tests/integration/pipelines/test_chembl_activity.py::TestChemblActivityPipeline::test_chembl_activity_happy_path
10.39s call     tests/integration/pipelines/test_chembl_target_component.py::TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path
10.33s call     tests/integration/pipelines/test_chembl_cell_line.py::TestChemblCellLinePipeline::test_chembl_cell_line_happy_path
10.33s call     tests/integration/pipelines/test_chembl_cell_line.py::TestChemblCellLinePipeline::test_chembl_cell_line_source_fields
10.27s call     tests/integration/pipelines/test_chembl_compound_record.py::TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path
```

## cProfile of `tests/integration/pipelines/test_chembl_activity.py`
Command: `uv run --frozen python -m cProfile -o test_chembl_activity.prof -m pytest tests/integration/pipelines/test_chembl_activity.py -q`

Output of `uv run --frozen python -c "import pstats; p = pstats.Stats('test_chembl_activity.prof'); p.strip_dirs().sort_stats('cumtime').print_stats(30)"`:
```text
         9324784 function calls (9096672 primitive calls) in 20.932 seconds

   Ordered by: cumulative time
   List reduced from 15775 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      139    0.002    0.000   25.330    0.182 base_events.py:1980(_run_once)
      139    0.001    0.000   21.411    0.154 selectors.py:435(select)
      139    9.991    0.072   21.112    0.152 {method 'poll' of 'select.epoll' objects}
```

## cProfile of `tests/integration/pipelines/test_chembl_cell_line.py`
Command: `uv run --frozen python -m cProfile -o test_chembl_cell_line.prof -m pytest tests/integration/pipelines/test_chembl_cell_line.py -q`

Output of `uv run --frozen python -c "import pstats; p = pstats.Stats('test_chembl_cell_line.prof'); p.strip_dirs().sort_stats('cumtime').print_stats(30)"`:
```text
         8373308 function calls (8157973 primitive calls) in 29.746 seconds

   Ordered by: cumulative time
   List reduced from 15572 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      222    0.003    0.000   44.589    0.201 base_events.py:1980(_run_once)
      222    0.002    0.000   41.138    0.185 selectors.py:435(select)
      222   19.974    0.090   40.908    0.184 {method 'poll' of 'select.epoll' objects}
```

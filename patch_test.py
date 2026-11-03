import re

file_path = 'tests/e2e/test_full_pipeline_chain_e2e.py'
with open(file_path, 'r') as f:
    content = f.read()

content = content.replace('''    await runner1.run()  # type: ignore[attr-defined]
    await run_molecule_then_target_and_assert(
        e2e_data_dir,
        require_a2_records_fetched=True,
    )''', '''    await runner1.run()  # type: ignore[attr-defined]
    assert runner1.execution_metrics["records_fetched"] > 0  # type: ignore[index]
    assert runner1.execution_metrics["records_silver"] > 0  # type: ignore[index]

    await run_molecule_then_target_and_assert(
        e2e_data_dir,
        require_a2_records_fetched=True,
    )''')

content = content.replace('''    with patched_extract_records(runner1, monkeypatch, gated):
        await cancel_after_first_record(runner1, first_record_ready)
    await run_molecule_then_target_and_assert(e2e_data_dir)''', '''    with patched_extract_records(runner1, monkeypatch, gated):
        await cancel_after_first_record(runner1, first_record_ready)

    assert runner1.execution_metrics["records_fetched"] == 0  # type: ignore[index]

    await run_molecule_then_target_and_assert(e2e_data_dir)''')

with open(file_path, 'w') as f:
    f.write(content)

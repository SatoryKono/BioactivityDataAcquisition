@echo off
cd /d "E:\g-drive\05_AI\github\BioactivityDataAcquisition2"
echo START %DATE% %TIME%> _loop_pytest_out.txt
".venv-win\Scripts\python.exe" -m pytest tests/unit/interfaces/cli/test_workflow_cli.py tests/unit/interfaces/http/test_health_server.py tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py tests/architecture/test_tech_debt_issues_5707_5715_closeout.py::test_issue_5714_dead_code_governance_has_no_untriaged_candidates tests/architecture/test_tech_debt_issues_6159_6169_closeout.py::test_issue_6165_dead_code_zero_import_candidates_are_triaged tests/integration/test_grafana_datasource_provisioning.py -q --tb=line --maxfail=20 >> _loop_pytest_out.txt 2>&1
echo EXIT=%ERRORLEVEL%>> _loop_pytest_out.txt
echo DONE %DATE% %TIME%>> _loop_pytest_out.txt

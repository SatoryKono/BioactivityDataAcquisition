@echo off
cd /d "E:\g-drive\05_AI\github\BioactivityDataAcquisition2"
echo === CMD1 START ===
python -m scripts.engineering.qa.report_architecture_quality_scorecard > "_agent_qa_out1.txt" 2>&1
echo CMD1_EXIT=%ERRORLEVEL%>> "_agent_qa_out1.txt"
echo === CMD1 END ===
echo === CMD2 START ===
python -m scripts.engineering.qa report-debt-governance-gates --update > "_agent_qa_out2.txt" 2>&1
echo CMD2_EXIT=%ERRORLEVEL%>> "_agent_qa_out2.txt"
echo === CMD2 END ===
echo === CMD3 START ===
python -c "import json; from pathlib import Path; p=Path('reports/quality/architecture-quality-scorecard.json'); d=json.loads(p.read_text()); print('scorecard hash', d.get('source_artifacts',{}).get('module_coverage_inventory',{}).get('source_tree_sha256')); p2=Path('reports/quality/module-coverage-inventory.json'); print('inventory hash', json.loads(p2.read_text()).get('source_tree_sha256')); p3=Path('reports/quality/debt-governance-gates.json'); g=json.loads(p3.read_text()); print('gates fail', g['summary']['fail_count'], g['summary']['failing_gates'])" > "_agent_qa_out3.txt" 2>&1
echo CMD3_EXIT=%ERRORLEVEL%>> "_agent_qa_out3.txt"
echo === CMD3 END ===
echo DONE > "_agent_qa_done.txt"

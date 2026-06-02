#!/bin/bash
curl -X POST http://127.0.0.1:8081/submit -H "Content-Type: application/json" -d '{
    "branch_name": "fix-dashboard-errors-13249332482520436398",
    "commit_message": "fix: correct percentage typo and remove empty expr from JSON datasources",
    "title": "Fix Grafana dashboard schema and typo errors",
    "description": "# What\nCorrected a typo `percintage` to `percentage` across multiple dashboard panels and removed erroneous empty `expr` properties from JSON datasource panels.\n\n# Why\nGrafana dashboards contained errors in their definition files, potentially causing rendering issues or misconfigurations.\n\n# Verification\nRan Grafana integration tests and added a UX report.\n\n# Result\nCleaner dashboard JSON files and fixed typos."
}'

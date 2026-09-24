# Grafana S3776 refactor — #10991

Status: implementation verified locally; Sonar closure and merge pending.

Refactored all ten requested entry points into panel/field-specific helpers. Mutation order, UID guards, mapping merge and histogram generation guard are preserved. No NOSONAR or debt-budget changes. Dashboard JSON bytes are unchanged.

Validation: 21 differential cases, each applied twice to all seven dashboard payloads; canonical generator --check 7/7; 838 dashboard/Grafana tests passed, 8 skipped; 48 required focused checks passed; Ruff passed. Skips: 5 retired workflow dashboard checks, 2 POSIX-only bootstrap checks, 1 opt-in live panel-fill check. Local AST complexity estimates for the ten functions are 0–7; these are not Sonar measurements. Sonar keys remained OPEN at the pre-publication live check and require reanalysis after integration.

Live acceptance belongs to a separate context and is not inferred from this semantics-preserving refactor. No monitoring compose started. Merge is held until the owner identifies completion of stream C. AI runtime mirrors unchanged; source coverage inventory not applicable (no src/bioetl edits). Memory pre-task retrieval was degraded because local RAG/timeline artifacts are absent; source and tests were inspected directly.

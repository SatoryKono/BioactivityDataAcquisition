# Live vulnerabilities (SNR-R2 W0′)

revision: `ab0bd320e53b9b9e423150f2dd98153fe686a284` total_vulns=31 total_open=206

| Key | Rule | Path | Line | Message |
|---|---|---|---:|---|
| `AZ-3lPTMpjm5KvNkTzrR` | `githubactions:S7637` | `.github/workflows/memory-freshness.yml` | 22 | Use full commit SHA hash for this dependency. |
| `AZ-4z-__kb2krUTIfyqC` | `githubactions:S8264` | `.github/workflows/branch-hygiene.yml` | 11 | Move this read permission from workflow level to job level. |
| `AZ-4z-__kb2krUTIfyqD` | `githubactions:S8264` | `.github/workflows/branch-hygiene.yml` | 12 | Move this read permission from workflow level to job level. |
| `AZ-3lPTMpjm5KvNkTzrS` | `githubactions:S8541` | `.github/workflows/memory-freshness.yml` | 27 | Omitting "--no-build" can lead to the execution of setup scripts. Make sure it is safe here. |
| `AZ-4RoqPXF-Rs4_NuNzk` | `githubactions:S8541` | `.github/workflows/memory-freshness.yml` | 35 | Omitting "--no-build" can lead to the execution of setup scripts. Make sure it is safe here. |
| `AZ-3lPTMpjm5KvNkTzrU` | `githubactions:S8541` | `.github/workflows/memory-freshness.yml` | 42 | Omitting "--no-build" can lead to the execution of setup scripts. Make sure it is safe here. |
| `AZ-0WVh320ESPB3h1_98` | `githubactions:S8541` | `.github/workflows/memory-retention.yml` | 44 | Omitting "--no-build" can lead to the execution of setup scripts. Make sure it is safe here. |
| `AZ-3lPTMpjm5KvNkTzrT` | `githubactions:S8544` | `.github/workflows/memory-freshness.yml` | 27 | Using dependencies without locking resolved versions is security-sensitive. |
| `AZ-4RoqPXF-Rs4_NuNzl` | `githubactions:S8544` | `.github/workflows/memory-freshness.yml` | 35 | Using dependencies without locking resolved versions is security-sensitive. |
| `AZ-3lPTMpjm5KvNkTzrV` | `githubactions:S8544` | `.github/workflows/memory-freshness.yml` | 42 | Using dependencies without locking resolved versions is security-sensitive. |
| `AZ-3lhnyfP0insu10KpN` | `pythonsecurity:S2083` | `scripts/docs/passports/rename_underscore_to_hyphen.py` | 149 | Change this code to not construct the path from user-controlled data. |
| `AZ_WpggDY9BZ5BAOyClL` | `pythonsecurity:S2083` | `scripts/engineering/apply_s1_c2_fixes.py` | 14 | Change this code to not construct the path from user-controlled data. |
| `AZ_WpgR8Y9BZ5BAOyClK` | `pythonsecurity:S2083` | `scripts/engineering/apply_s1_c3c6_fixes.py` | 14 | Change this code to not construct the path from user-controlled data. |
| `AZ-tRYo1vvakrfsdqURn` | `pythonsecurity:S2083` | `scripts/ops/observability/grafana/apply_dux5_residual.py` | 169 | Change this code to not construct the path from user-controlled data. |
| `AZ_YbeR7NNQnFHwd25PW` | `pythonsecurity:S8703` | `scripts/ops/runtime/docker/verify_report_bind.py` | 93 | LLMs running this code with faulty CLI arguments can cause SSRFs. Refactor this code to validate strings before using them in network reques |
| `AZ-tRYtNvvakrfsdqURo` | `pythonsecurity:S8705` | `scripts/engineering/ci/_compatibility_registry.py` | 490 | LLMs running this code with faulty CLI arguments can escape from shell sandboxes. Refactor this code to validate untrusted data before passi |
| `AZ_YbeR7NNQnFHwd25PX` | `pythonsecurity:S8705` | `scripts/ops/runtime/docker/verify_report_bind.py` | 103 | LLMs running this code with faulty CLI arguments can escape from shell sandboxes. Refactor this code to validate untrusted data before passi |
| `AZ-4nwE2OQN6Udtp1QH0` | `pythonsecurity:S8707` | `scripts/ai/sync/runtime_skills.py` | 113 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ-4nwE2OQN6Udtp1QHz` | `pythonsecurity:S8707` | `scripts/ai/sync/runtime_skills.py` | 114 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ-4z-09kb2krUTIfyqB` | `pythonsecurity:S8707` | `scripts/diagrams/fix/strip_svg_foreign_object.py` | 121 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ-tRYtNvvakrfsdqURp` | `pythonsecurity:S8707` | `scripts/engineering/ci/_compatibility_registry.py` | 144 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ_Sx7f87s3WKsGdEFu0` | `pythonsecurity:S8707` | `scripts/engineering/qa/report_domain_ports_inventory.py` | 217 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ-u_S2h0C2pXrklOfoG` | `pythonsecurity:S8707` | `scripts/ops/observability/grafana/run_grafana_render_matrix.py` | 175 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ-u_O3F0C2pXrklOfnv` | `pythonsecurity:S8707` | `src/bioetl/infrastructure/storage/support/_atomic_replace.py` | 70 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ-3lWCKfP0insu10Ko9` | `pythonsecurity:S8707` | `src/memory/mcp_scope.py` | 64 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ-u_QQL0C2pXrklOfoC` | `pythonsecurity:S8707` | `src/memory/migrations.py` | 102 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ-u_QN20C2pXrklOfn4` | `pythonsecurity:S8707` | `src/memory/storage.py` | 156 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ-u_QN20C2pXrklOfn5` | `pythonsecurity:S8707` | `src/memory/storage.py` | 171 | LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path be |
| `AZ_VxLOQen4ZkXPEVpyt` | `shell:S5332` | `grafana/scripts/bootstrap-datasources.sh` | 33 | Make sure that using clear-text protocols is safe here. |
| `AZ_VxLOQen4ZkXPEVpyu` | `shell:S5332` | `grafana/scripts/bootstrap-datasources.sh` | 34 | Make sure that using clear-text protocols is safe here. |
| `AZ_VxLOQen4ZkXPEVpyv` | `shell:S5332` | `grafana/scripts/bootstrap-datasources.sh` | 43 | Make sure that using clear-text protocols is safe here. |
